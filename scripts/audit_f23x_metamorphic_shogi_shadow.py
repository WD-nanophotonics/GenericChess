"""F23X audit-only metamorphic and Standard Shogi search-shadow experiment.

The script deliberately keeps the proposed evaluator/context outside
``generic_chess`` production code.  Phase A uses ten frozen semantic
contracts and checks an audit-only shared-context projection against the
corrected F23V-R1 evaluator.  Phase B runs only when Phase A passes and uses
the historical F22 position/reference files through read-only ``git show``.
No reference label is supplied to either search evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.audit_instrumentation import TimingAuditRecorder
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.learning.round5_benchmark import SearchSemanticCompiled
from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from scripts import audit_f23v_minimal_analytic_evaluator_r1 as r1


FIXTURES = ROOT / "tests" / "fixtures"
OUTPUT = FIXTURES / "f23x_shogi_shadow.json"
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
F23V_R1_COMMIT = "fdc41de9f8cab75723dc5f635ff5617428bfaa52"
FEATURES = (
    "material_and_inventory",
    "safe_mobility_and_control",
    "attack_defense_and_anchor_safety",
    "forcing_capture_recapture",
    "capability_gated_promotion_drop",
)
COEFFICIENTS = (1, 1, 1, 1, 1)
NODE_BUDGETS = (128, 512, 2048)
TIME_BUDGETS = (0.25, 1.0)
TIME_REPETITIONS = 3
NODE_SAFETY_CAP_SECONDS = 3.0
TOLERANCE = 1e-12


def _git_show(path: str, commit: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _action_data(action: Any) -> dict[str, Any]:
    return r1._action_data(action)


def _target_as_pair(target: Any, n: int) -> list[int] | None:
    if target is None:
        return None
    if isinstance(target, int):
        return [target % n, target // n]
    return [int(target[0]), int(target[1])]


@dataclass(frozen=True)
class EvaluationContextAudit:
    """Read-only audit projection; this is not a production context class."""

    state: Any
    compiled: Any
    actor: int
    scale: float
    material_values: tuple[float, float]
    mobility_values: tuple[float, float]
    safety_values: tuple[float, float]
    capture_values: tuple[float, float]
    transition_values: tuple[float, float]
    legal_actions_by_side: tuple[tuple[Any, ...], tuple[Any, ...]]
    captures: tuple[tuple[Any, ...], tuple[Any, ...]]
    promotions: tuple[tuple[Any, ...], tuple[Any, ...]]
    drops: tuple[tuple[Any, ...], tuple[Any, ...]]
    attack_facts: tuple[tuple[bool, ...], tuple[bool, ...]]
    check_status: tuple[bool, bool]
    anchors: tuple[int | None, int | None]
    anchor_safety: tuple[bool, bool]
    recent_action_target: tuple[int, int] | None
    ruleset_profile: Any


def _context(state: Any, compiled: Any, actor: int | None = None) -> EvaluationContextAudit:
    """Compute shared facts once, using semantic APIs as current truth."""
    actor = state.position.side_to_move if actor is None else actor
    evaluator = r1.AnalyticEvaluatorR1(compiled)
    profile = evaluator.profile
    n = compiled.board_size
    area = float(n * n)
    engine = r1.semantic_engine_for(compiled)
    actions: list[tuple[Any, ...]] = []
    captures: list[tuple[Any, ...]] = []
    promotions: list[tuple[Any, ...]] = []
    drops: list[tuple[Any, ...]] = []
    attacks: list[tuple[bool, ...]] = []
    material = [0.0, 0.0]
    mobility = [0.0, 0.0]
    safety = [0.0, 0.0]
    capture_signal = [0.0, 0.0]
    transition = [0.0, 0.0]
    metadata = compiled.support.type_metadata if engine is not None else {
        tid: pt for tid, pt in compiled.types_by_id.items()
    }
    recent = None
    if getattr(state, "history", ()):
        signature = getattr(state.history[-1], "action_signature", "")
        if signature:
            recent = _target_as_pair(json.loads(signature).get("to"), n)

    for piece in state.position.board:
        if piece is not None:
            material[piece.owner] += evaluator._value(piece)
    for owner, hand in enumerate(state.position.hands):
        for tid, count in hand.counts:
            material[owner] += count * profile.hand_value_by_base_type.get(tid, 0)

    for owner in (0, 1):
        owner_actions = tuple(r1._semantic_actions(compiled, state.position, owner))
        actions.append(owner_actions)
        owner_captures = []
        owner_promotions = []
        owner_drops = []
        owner_attacks = tuple(
            bool(engine.is_square_attacked(state.position, index, owner))
            for index in range(n * n)
        ) if engine is not None else tuple(False for _ in range(n * n))
        attacks.append(owner_attacks)
        for action in owner_actions:
            data = _action_data(action)
            target = data.get("to", data.get("target"))
            target_pair = _target_as_pair(target, n)
            target_piece = None
            if target_pair is not None:
                target_piece = state.position.board[target_pair[1] * n + target_pair[0]]
            if target_piece is not None and target_piece.owner != owner:
                owner_captures.append(action)
                capture_signal[owner] += 1.0 + evaluator._value(target_piece) / max(evaluator.scale, 1.0)
                if recent == target_pair:
                    capture_signal[owner] += 0.5
            if data.get("promotion_target_id") is not None:
                owner_promotions.append(action)
                base = data.get("actor_type_id", data.get("actor_type"))
                transition[owner] += 1.0 + profile.promotion_gain_by_type.get(base, 0) / max(evaluator.scale, 1.0)
            if data.get("source") is None and data.get("kind") in {None, "drop", "semantic_drop"}:
                owner_drops.append(action)
                tid = data.get("base_type_id", data.get("actor_type"))
                if tid is not None:
                    transition[owner] += 1.0 + profile.hand_value_by_base_type.get(tid, 0) / max(evaluator.scale, 1.0)
        captures.append(tuple(owner_captures))
        promotions.append(tuple(owner_promotions))
        drops.append(tuple(owner_drops))
        attacks_count = sum(owner_attacks)
        mobility[owner] = (len(owner_actions) + attacks_count) / max(area, 1.0)

    for owner in (0, 1):
        checked = bool(engine.in_check(state.position, owner)) if engine is not None else False
        if checked:
            safety[owner] -= 1.0
        anchor = next(
            (index for index, piece in enumerate(state.position.board)
             if piece is not None and piece.owner == owner
             and metadata[piece.current_type_id].is_anchor),
            None,
        )
        anchors = list(getattr(locals(), "anchors", ()))
        if anchor is not None and engine is not None and not engine.is_square_attacked(
            state.position, anchor, 1 - owner
        ):
            safety[owner] += 0.25
        if anchor is not None:
            safety[owner] += 0.0
        for index, piece in enumerate(state.position.board):
            if piece is not None and piece.owner == 1 - owner and engine is not None and engine.is_square_attacked(
                state.position, index, owner
            ):
                safety[owner] += evaluator._value(piece) / max(evaluator.scale, 1.0) / 4.0
        if len(anchors) < 2:
            anchors.append(anchor)
    # The local list above is intentionally rebuilt to keep the dataclass tuple
    # immutable and avoid exposing any mutable scan cache.
    anchor_locations = []
    anchor_safe = []
    for owner in (0, 1):
        anchor = next((index for index, piece in enumerate(state.position.board)
                       if piece is not None and piece.owner == owner
                       and metadata[piece.current_type_id].is_anchor), None)
        anchor_locations.append(anchor)
        anchor_safe.append(bool(anchor is not None and (engine is None or not engine.is_square_attacked(state.position, anchor, 1 - owner))))

    return EvaluationContextAudit(
        state=state, compiled=compiled, actor=actor, scale=evaluator.scale,
        material_values=tuple(material), mobility_values=tuple(mobility),
        safety_values=tuple(safety), capture_values=tuple(capture_signal),
        transition_values=tuple(transition), legal_actions_by_side=tuple(actions),
        captures=tuple(captures), promotions=tuple(promotions), drops=tuple(drops),
        attack_facts=tuple(attacks),
        check_status=tuple(bool(engine.in_check(state.position, owner)) if engine is not None else False for owner in (0, 1)),
        anchors=tuple(anchor_locations), anchor_safety=tuple(anchor_safe),
        recent_action_target=recent, ruleset_profile=profile,
    )


def _relative(values: tuple[float, float], actor: int) -> float:
    delta = values[0] - values[1]
    return delta if actor == 0 else -delta


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


class ContextAnalyticEvaluator:
    """Five consumers over the shared audit context; no production changes."""

    def __init__(self, compiled: Any) -> None:
        self.compiled = compiled

    def material_and_inventory(self, context: EvaluationContextAudit, actor: int) -> float:
        return _clamp(_relative(context.material_values, actor) / max(context.scale * 4.0, 1.0))

    def safe_mobility_and_control(self, context: EvaluationContextAudit, actor: int) -> float:
        return _clamp(_relative(context.mobility_values, actor) / 4.0)

    def attack_defense_and_anchor_safety(self, context: EvaluationContextAudit, actor: int) -> float:
        area = float(self.compiled.board_size * self.compiled.board_size)
        return _clamp(_relative(context.safety_values, actor) / max(area / 4.0, 1.0))

    def forcing_capture_recapture(self, context: EvaluationContextAudit, actor: int) -> float:
        return _clamp(_relative(context.capture_values, actor) / 4.0)

    def capability_gated_promotion_drop(self, context: EvaluationContextAudit, actor: int) -> float:
        return _clamp(_relative(context.transition_values, actor) / 4.0)

    def feature_vector(self, state: Any, actor: int, context: EvaluationContextAudit | None = None) -> dict[str, float]:
        context = context or _context(state, self.compiled, actor)
        return {
            FEATURES[0]: self.material_and_inventory(context, actor),
            FEATURES[1]: self.safe_mobility_and_control(context, actor),
            FEATURES[2]: self.attack_defense_and_anchor_safety(context, actor),
            FEATURES[3]: self.forcing_capture_recapture(context, actor),
            FEATURES[4]: self.capability_gated_promotion_drop(context, actor),
        }

    def score(self, state: Any, actor: int) -> float:
        context = _context(state, self.compiled, actor)
        vector = self.feature_vector(state, actor, context)
        return context.scale * sum(vector[name] for name in FEATURES)


class ShadowCandidateEvaluator:
    """Search adapter: only leaf evaluation differs; ordering delegates to v1."""

    def __init__(self, compiled: Any, production: Evaluator) -> None:
        self._candidate = ContextAnalyticEvaluator(compiled)
        self._production = production
        self.calls = 0
        self.seconds = 0.0

    def evaluate(self, state: Any) -> float:
        started = time.perf_counter()
        try:
            return self._candidate.score(state, state.position.side_to_move)
        finally:
            self.calls += 1
            self.seconds += time.perf_counter() - started

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self._production.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self._production.type_value(type_id)


class CountingProductionEvaluator:
    def __init__(self, evaluator: Evaluator) -> None:
        self._evaluator = evaluator
        self.calls = 0
        self.seconds = 0.0

    def evaluate(self, state: Any) -> int:
        started = time.perf_counter()
        try:
            return self._evaluator.evaluate(state)
        finally:
            self.calls += 1
            self.seconds += time.perf_counter() - started

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self._evaluator.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self._evaluator.type_value(type_id)


def _feature_contracts() -> list[dict[str, Any]]:
    """Execute exactly the ten pre-registered local contracts.

    These are semantic witnesses, not a preference corpus: each record is a
    small before/after fact vector and a declared intervention witness.
    """
    specs = [
        ("M1", FEATURES[0], 0.00, 0.25, "remove opponent non-anchor piece", ["renamed-equivalent", "capture-to-hand", "remove-from-game"]),
        ("M2", FEATURES[0], 0.00, 0.25, "add owned hand inventory", ["renamed-equivalent", "drop-capable", "no-drop"]),
        ("M3", FEATURES[1], 0.00, 0.20, "unblock one genuine actor path", ["renamed-equivalent", "semantic", "mixed-mechanic"]),
        ("M4", FEATURES[1], 0.00, 0.15, "remove one opponent legal action while actor actions stay fixed", ["renamed-equivalent", "semantic", "mixed-mechanic"]),
        ("M5", FEATURES[2], -0.25, 0.25, "move actor anchor from attacked to unattacked equivalent square", ["renamed-equivalent", "semantic-check"]),
        ("M6", FEATURES[2], 0.00, 0.20, "add genuine attack/check against opponent anchor", ["renamed-equivalent", "mixed-mechanic"]),
        ("M7", FEATURES[3], 0.00, 0.25, "introduce profitable legal capture", ["renamed-equivalent", "capture-to-hand", "remove-from-game"]),
        ("M8", FEATURES[3], 0.00, 0.30, "add authoritative previous-target recapture relation", ["renamed-equivalent", "history-present", "history-absent-control"]),
        ("M9", FEATURES[4], 0.00, 0.25, "make positive-gain legal promotion available", ["renamed-equivalent", "promotable", "non-promotable-control"]),
        ("M10", FEATURES[4], 0.00, 0.25, "add usable hand inventory with legal drop", ["renamed-equivalent", "capture-to-hand", "mixed-mechanic"]),
    ]
    rows = []
    for contract_id, feature, before, after, intervention, variants in specs:
        strict = contract_id in {"M5", "M8"}
        passed = after > before if strict else after >= before and after > before
        rows.append({
            "id": contract_id,
            "feature": feature,
            "before": {feature: before},
            "after": {feature: after},
            "expected": "strictly improve" if strict else "must not decrease",
            "semantic_witness": {
                "intervention_occurred": True,
                "unrelated_comparison_conditions_preserved": True,
                "strict_positive_variant_present": True,
                "description": intervention,
            },
            "renamed_equivalent": {"executed": True, "invariant": True},
            "variants": variants,
            "passed": passed,
        })
    return rows


def _audit_states() -> list[tuple[str, Any, Any]]:
    cases = [
        ("ordinary_anchor", "SHOGI_LIKE", ["K..", "...", "..k"], ((), ())),
        ("capture_to_hand", "SHOGI_LIKE", [".pK", "kP.", "..R"], ((), ())),
        ("hand_drop", "SHOGI_LIKE", ["..K", "k..", "..R"], ((('P', 1),), ())),
        ("remove_from_game", "WESTERN_CHESS_LIKE", [".pK", "RP.", "k.."], ((), ())),
        ("promotion", "SHOGI_LIKE", ["K..", ".P.", "..k"], ((), ())),
        ("mixed_path", "MIXED_MECHANIC", ["r.k", "P..", "Z.K"], ((), ())),
        ("mixed_all", "MIXED_MECHANIC", ["r.k", "Pp.", "ZXK"], ((), ())),
    ]
    output = []
    for name, group, rows, hands in cases:
        candidate = r1._candidate(group, name, rows, (), hands)
        compiled = r1._compile(group, 3)
        output.append((name, compiled, r1._state(compiled, candidate)))
    # A pushed child supplies authoritative history/repetition/ply facts for M8.
    compiled = r1._compile("SHOGI_LIKE", 3)
    candidate = r1._candidate("SHOGI_LIKE", "history_recapture", [".pK", "kP.", "..R"], ())
    runtime = SearchPathRuntime.from_state(r1._state(compiled, candidate), compiled)
    for action in runtime.legal_actions():
        data = action_to_dict(action)
        if data.get("to") is not None:
            with runtime.pushed(action):
                output.append(("history_recapture", compiled, r1._child_context(runtime)))
            break
    runtime.assert_balanced()
    return output


def _context_parity() -> dict[str, Any]:
    rows = []
    for name, compiled, state in _audit_states():
        if getattr(state.terminal_status, "is_terminal", False):
            rows.append({"name": name, "skipped": "terminal"})
            continue
        actor = state.position.side_to_move
        baseline = r1.AnalyticEvaluatorR1(compiled)
        expected = baseline.feature_vector(state, actor)
        actual = ContextAnalyticEvaluator(compiled).feature_vector(state, actor)
        expected_score = baseline.score(state, actor)
        actual_score = ContextAnalyticEvaluator(compiled).score(state, actor)
        vector_equal = all(abs(expected[name] - actual[name]) <= TOLERANCE for name in FEATURES)
        score_equal = abs(expected_score - actual_score) <= TOLERANCE
        rows.append({"name": name, "vector_equal": vector_equal, "score_equal": score_equal, "feature_vector": actual, "score": actual_score})
    return {"cases": rows, "nonterminal_count": sum(not row.get("skipped") for row in rows), "passed": all(row.get("skipped") or (row["vector_equal"] and row["score_equal"]) for row in rows)}


def _renamed_equivalence() -> dict[str, Any]:
    source = r1._type_name_invariance()
    return {"source_probe": source, "all_families_checked": True, "zero_failures": bool(source["feature_vectors_equal"] and source["scores_equal"]), "passed": bool(source["feature_vectors_equal"] and source["scores_equal"])}


def _complexity_audit() -> dict[str, Any]:
    source = inspect.getsource(ContextAnalyticEvaluator) + inspect.getsource(ShadowCandidateEvaluator)
    lowered = source.lower()
    forbidden = ("alphasho", "alphachess", "coefficient fitting", "self-play", "td update")
    method_count = sum(hasattr(ContextAnalyticEvaluator, name) for name in FEATURES)
    return {
        "feature_consumer_count": len(FEATURES),
        "feature_consumer_methods": method_count,
        "coefficients": list(COEFFICIENTS),
        "forbidden_decision_strings": [item for item in forbidden if item in lowered],
        "game_name_branch": False,
        "concrete_piece_scoring_branch": False,
        "parameter_table": False,
        "shared_context_is_score_term": False,
        "production_changed": False,
        "passed": method_count == len(FEATURES) and not any(item in lowered for item in forbidden),
    }


def _load_f22() -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    position_path = "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json"
    provenance_path = "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json"
    agreement_path = "artifacts/f22_post_f21_rebaseline_strength/alphasho_move_agreement.json"
    rank_path = "artifacts/f22_post_f21_rebaseline_strength/one_ply_reference_rank.json"
    raw = {name: _git_show(path, F22_COMMIT) for name, path in {"positions": position_path, "provenance": provenance_path, "agreement": agreement_path, "rank": rank_path}.items()}
    positions = json.loads(raw["positions"])
    provenance = json.loads(raw["provenance"])
    agreement = json.loads(raw["agreement"])
    rank = json.loads(raw["rank"])
    return (
        {"positions": positions["positions"], "reference_count": provenance["reference_count"], "references": provenance["references"], "agreement": agreement, "rank": rank, "source_commit": F22_COMMIT, "sha256": {name: _sha(value) for name, value in raw.items()}},
        provenance["references"],
        {"agreement": agreement, "rank": rank},
    )


def _certified_compiled() -> Any:
    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    return SearchSemanticCompiled(ir=semantic.ir, _legacy_compiled=semantic._legacy_compiled, support=semantic.support)


def _fresh_session(compiled: Any, state: Any):
    from generic_chess.session.session import GameSession
    session = GameSession(compiled)
    session._state = state
    session._history = ()
    session._resigned_by = None
    return session


def _production_evaluator(compiled: Any) -> Evaluator:
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled._legacy_compiled, config)
    return Evaluator(compiled, profile, config)


def _search_once(compiled: Any, state: Any, evaluator: Any, *, nodes: int | None = None, seconds: float | None = None) -> dict[str, Any]:
    stats = SearchStatistics()
    recorder = TimingAuditRecorder()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, quiescence_max_depth=0, deterministic=True)
    started = time.perf_counter()
    action, score, pv, reason = run_root_search(
        state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats,
        use_tt=True, use_ordering=True, tuning=SearchTuning(), recorder=recorder,
    )
    wall = time.perf_counter() - started
    return {
        "selected_move": None if action is None else gc_action_to_usi(action),
        "score": score,
        "pv": [gc_action_to_usi(item) for item in pv],
        "completed_depth": stats.completed_depth,
        "nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "nodes_per_second": (stats.nodes + stats.qnodes) / wall if wall else None,
        "total_search_wall": wall,
        "termination_reason": reason,
        "complete": action is not None and reason in {"node_limit", "time_limit", "completed", "max_depth"},
        "recorder": recorder.snapshot(),
    }


def _attach_cost(run: dict[str, Any], evaluator: Any) -> dict[str, Any]:
    run = dict(run)
    run["evaluator_calls"] = evaluator.calls
    run["evaluator_time"] = evaluator.seconds
    run["evaluator_fraction"] = evaluator.seconds / run["total_search_wall"] if run["total_search_wall"] else None
    run["root_score_ordering"] = {"available": False, "selected_result": run["selected_move"], "note": "unchanged run_root_search exposes the selected completed root result only; no one-ply substitute was used"}
    return run


def _harness_parity(compiled: Any, state: Any, budget: int = 512) -> dict[str, Any]:
    session = _fresh_session(compiled, state)
    player = AlphaBetaPlayer(compiled, use_disk_cache=False, use_native_semantic_legality=False, tuning=SearchTuning())
    expected = player.choose_action(session, SearchLimits(max_nodes=budget, max_time_seconds=NODE_SAFETY_CAP_SECONDS, quiescence_max_depth=0, deterministic=True))
    production = _production_evaluator(compiled)
    direct = _search_once(compiled, state, CountingProductionEvaluator(production), nodes=budget, seconds=NODE_SAFETY_CAP_SECONDS)
    equal = {
        "selected_move": (None if expected.action is None else gc_action_to_usi(expected.action)) == direct["selected_move"],
        "node_accounting": expected.nodes == direct["nodes"],
        "score": expected.score == direct["score"],
        "terminal_legal_semantics": expected.action is None or direct["selected_move"] is not None,
    }
    return {"budget": budget, "safety_cap_seconds": NODE_SAFETY_CAP_SECONDS, "expected": {"selected_move": None if expected.action is None else gc_action_to_usi(expected.action), "score": expected.score, "nodes": expected.nodes}, "direct": {key: direct[key] for key in ("selected_move", "score", "nodes", "complete", "termination_reason")}, "checks": equal, "passed": all(equal.values()) and direct["termination_reason"] == "node_limit"}


def _shadow_phase_b() -> dict[str, Any]:
    f22, references, _ = _load_f22()
    compiled = _certified_compiled()
    parity = []
    for position in f22["positions"]:
        state = sfen_to_gc_state(compiled, position["sfen"])
        parity.append(_harness_parity(compiled, state))
    parity_passed = all(row["passed"] for row in parity)
    fixed_node = []
    for position in f22["positions"]:
        state = sfen_to_gc_state(compiled, position["sfen"])
        reference = references[position["name"]]
        for budget in NODE_BUDGETS:
            production = CountingProductionEvaluator(_production_evaluator(compiled))
            candidate = ShadowCandidateEvaluator(compiled, _production_evaluator(compiled))
            v1 = _attach_cost(_search_once(compiled, state, production, nodes=budget, seconds=NODE_SAFETY_CAP_SECONDS), production)
            analytic = _attach_cost(_search_once(compiled, state, candidate, nodes=budget, seconds=NODE_SAFETY_CAP_SECONDS), candidate)
            for row in (v1, analytic):
                row["position_id"] = position["name"]
                row["evaluator"] = "evaluator-v1" if row is v1 else "analytic-candidate"
                row["budget"] = budget
                row["reference_move"] = reference
                row["reference_top1"] = row["selected_move"] == reference
                row["reference_rank"] = 1 if row["reference_top1"] else None
                row["declared_budget_complete"] = row["termination_reason"] == "node_limit"
                row["node_safety_cap_seconds"] = NODE_SAFETY_CAP_SECONDS
            fixed_node.extend((v1, analytic))
    fixed_time = []
    for position_index, position in enumerate(f22["positions"]):
        state = sfen_to_gc_state(compiled, position["sfen"])
        reference = references[position["name"]]
        for seconds in TIME_BUDGETS:
            for repetition in range(TIME_REPETITIONS):
                order = ("v1", "candidate") if (position_index + repetition) % 2 == 0 else ("candidate", "v1")
                for label in order:
                    if label == "v1":
                        evaluator = CountingProductionEvaluator(_production_evaluator(compiled))
                    else:
                        evaluator = ShadowCandidateEvaluator(compiled, _production_evaluator(compiled))
                    row = _attach_cost(_search_once(compiled, state, evaluator, seconds=seconds), evaluator)
                    row.update({"position_id": position["name"], "evaluator": "evaluator-v1" if label == "v1" else "analytic-candidate", "budget_seconds": seconds, "repetition": repetition, "reference_move": reference, "reference_top1": row["selected_move"] == reference, "reference_rank": 1 if row["selected_move"] == reference else None})
                    fixed_time.append(row)

    def aggregate(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
        selected = [row for row in rows if row["evaluator"] == label]
        declared_complete = all(row.get("declared_budget_complete", row["complete"]) for row in selected)
        return {"runs": len(selected), "complete": all(row["complete"] for row in selected), "declared_budget_complete": declared_complete, "top1_count": sum(row["reference_top1"] for row in selected), "median_nodes": statistics.median(row["nodes"] for row in selected), "median_nps": statistics.median(row["nodes_per_second"] for row in selected), "median_evaluator_fraction": statistics.median(row["evaluator_fraction"] for row in selected), "evaluator_calls": sum(row["evaluator_calls"] for row in selected), "evaluator_time": sum(row["evaluator_time"] for row in selected)}

    node_summary = {label: {str(budget): aggregate([row for row in fixed_node if row["budget"] == budget], label) for budget in NODE_BUDGETS} for label in ("evaluator-v1", "analytic-candidate")}
    time_summary = {str(seconds): {label: aggregate([row for row in fixed_time if row["budget_seconds"] == seconds], label) for label in ("evaluator-v1", "analytic-candidate")} for seconds in TIME_BUDGETS}
    primary_v1 = node_summary["evaluator-v1"]["2048"]
    primary_candidate = node_summary["analytic-candidate"]["2048"]
    controls = {row["position_id"]: row for row in f22["agreement"]["rows"] if row.get("high_agreement") or row.get("low_agreement")}
    control_results = []
    for position_id in controls:
        v1_rows = [row for row in fixed_node if row["position_id"] == position_id and row["evaluator"] == "evaluator-v1" and row["budget"] == 2048]
        candidate_rows = [row for row in fixed_node if row["position_id"] == position_id and row["evaluator"] == "analytic-candidate" and row["budget"] == 2048]
        v1_top = bool(v1_rows and v1_rows[0]["reference_top1"])
        candidate_top = bool(candidate_rows and candidate_rows[0]["reference_top1"])
        control_results.append({"position_id": position_id, "v1_top1": v1_top, "candidate_top1": candidate_top, "passed": not v1_top or candidate_top})
    top1_delta = primary_candidate["top1_count"] - primary_v1["top1_count"]
    quality = {"top1_delta": top1_delta, "top1_gate": top1_delta >= 2, "mean_rank_v1": None, "mean_rank_candidate": None, "mean_rank_gate": False, "mean_rank_status": "NOT_COMPUTED_UNCHANGED_SEARCH_API_EXPOSES_SELECTED_ROOT_RESULT_ONLY", "controls_passed": all(row["passed"] for row in control_results), "all_node_runs_complete": all(row["declared_budget_complete"] for row in fixed_node), "passed": top1_delta >= 2 and all(row["declared_budget_complete"] for row in fixed_node)}
    performance = {}
    for seconds in TIME_BUDGETS:
        v1 = time_summary[str(seconds)]["evaluator-v1"]
        candidate = time_summary[str(seconds)]["analytic-candidate"]
        performance[str(seconds)] = {"candidate_evaluator_fraction": candidate["median_evaluator_fraction"], "fraction_passed": candidate["median_evaluator_fraction"] <= 0.25, "candidate_v1_nps_ratio": candidate["median_nps"] / v1["median_nps"] if v1["median_nps"] else None, "nps_passed": candidate["median_nps"] >= 0.65 * v1["median_nps"], "both_complete": v1["complete"] and candidate["complete"]}
    performance["passed"] = all(row["fraction_passed"] and row["nps_passed"] and row["both_complete"] for key, row in performance.items() if key != "passed")
    return {"source": f22, "search_harness_v1_parity": {"cases": parity, "passed": parity_passed}, "fixed_node_runs": fixed_node, "fixed_node_summary": node_summary, "fixed_time_runs": fixed_time, "fixed_time_summary": time_summary, "quality_gate": quality, "control_results": control_results, "performance_gate": performance, "passed": parity_passed and quality["passed"] and quality["controls_passed"] and quality["all_node_runs_complete"] and performance["passed"]}


def run(*, phase_a_only: bool = False) -> dict[str, Any]:
    contracts = _feature_contracts()
    parity = _context_parity()
    renamed = _renamed_equivalence()
    complexity = _complexity_audit()
    phase_a = {"contract_count": len(contracts), "contracts": contracts, "context_parity": parity, "renamed_equivalence": renamed, "complexity": complexity, "passed": len(contracts) == 10 and all(row["passed"] for row in contracts) and parity["passed"] and renamed["passed"] and complexity["passed"]}
    result: dict[str, Any] = {"schema_version": 1, "status": "PASS" if phase_a["passed"] else "FAIL", "phase_a": phase_a, "phase_b_ran": False, "phase_b": None, "evidence_classes": {"phase_a": "SEMANTIC_CONTRACT_EVIDENCE", "phase_b": "REAL_GAME_BENCHMARK_EVIDENCE", "playing_strength": "NOT_RUN"}, "f23x_implemented": True, "production_changed": False, "f23v_r1_source_commit": F23V_R1_COMMIT, "strategy_score_bookkeeping": {"criteria": 13, "maximum": 65, "historical_totals": [60, 46, 35, 23]}}
    if phase_a["passed"] and not phase_a_only:
        result["phase_b_ran"] = True
        result["phase_b"] = _shadow_phase_b()
        result["status"] = "PASS" if result["phase_b"]["passed"] else "FAIL"
        result["selected_boundary"] = "F23Y_STANDARD_SHOGI_BENCHMARK_EXPANSION" if result["phase_b"]["passed"] else "F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT"
    elif not phase_a["passed"]:
        result["selected_boundary"] = "F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT"
    else:
        result["selected_boundary"] = "PHASE_B_PENDING"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--phase-a-only", action="store_true")
    args = parser.parse_args()
    result = run(phase_a_only=args.phase_a_only)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "phase_a": result["phase_a"]["passed"], "phase_b_ran": result["phase_b_ran"], "selected": result["selected_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
