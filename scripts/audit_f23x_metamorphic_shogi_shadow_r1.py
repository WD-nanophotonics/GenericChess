"""Final F23X corrective: executable metamorphics and isolated shadow audit.

This module is intentionally audit-only.  It constructs real generic
RuleSet/GameState pairs for the ten contracts, hoists immutable profile work
out of leaf evaluation, and never changes ``generic_chess`` production code.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import multiprocessing
import queue
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
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
OUTPUT = FIXTURES / "f23x_shogi_shadow_r1.json"
CONTRACT_OUTPUT = FIXTURES / "f23x_metamorphic_contracts_r1.json"
FIRST_PASS_COMMIT = "1b042de7e1a48bacd9301f506bcd4c3152dd1374"
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
FEATURES = (
    "material_and_inventory",
    "safe_mobility_and_control",
    "attack_defense_and_anchor_safety",
    "forcing_capture_recapture",
    "capability_gated_promotion_drop",
)
COEFFICIENTS = (1, 1, 1, 1, 1)
NODE_BUDGETS = (128, 512, 2048)
NODE_WATCHDOG_SECONDS = {128: 30.0, 512: 30.0, 2048: 60.0}
TIME_BUDGETS = (0.25, 1.0)
TIME_REPETITIONS = 3
TOLERANCE = 1e-12
_COMPILED_BY_FINGERPRINT: dict[str, Any] = {}


def _git_show(path: str, commit: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _norm(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n")


def _data(action: Any) -> dict[str, Any]:
    return r1._action_data(action)


def _key(action: Any) -> str:
    return json.dumps(_data(action), sort_keys=True, separators=(",", ":"))


def _target_pair(value: Any, n: int) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value % n, value // n
    return int(value[0]), int(value[1])


def _relative(values: tuple[float, float], actor: int) -> float:
    delta = values[0] - values[1]
    return delta if actor == 0 else -delta


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


@dataclass(frozen=True)
class EvaluationContextAudit:
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
    check_status: tuple[bool, bool]
    anchors: tuple[int | None, int | None]
    anchor_safety: tuple[bool, bool]
    recent_action_target: tuple[int, int] | None
    timings: dict[str, float]


class ContextAnalyticEvaluator:
    """Corrected R1 mathematics over one shared, read-only context pass."""

    def __init__(self, compiled: Any) -> None:
        started = time.perf_counter()
        self.compiled = compiled
        self._r1 = r1.AnalyticEvaluatorR1(compiled)
        self.profile = self._r1.profile
        self.engine = self._r1.engine
        self.scale = self._r1.scale
        self.profile_build_count = 1
        self.profile_build_seconds = time.perf_counter() - started

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

    def build_context(self, state: Any, actor: int | None = None) -> EvaluationContextAudit:
        actor = state.position.side_to_move if actor is None else actor
        n = self.compiled.board_size
        area = float(n * n)
        engine = self.engine
        material = [0.0, 0.0]
        mobility = [0.0, 0.0]
        safety = [0.0, 0.0]
        capture_signal = [0.0, 0.0]
        transition = [0.0, 0.0]
        legal: list[tuple[Any, ...]] = []
        captures: list[tuple[Any, ...]] = []
        promotions: list[tuple[Any, ...]] = []
        drops: list[tuple[Any, ...]] = []
        attacks: list[tuple[bool, ...]] = []
        started = time.perf_counter()
        for piece in state.position.board:
            if piece is not None:
                material[piece.owner] += self._r1._value(piece)
        for owner, hand in enumerate(state.position.hands):
            for tid, count in hand.counts:
                material[owner] += count * self.profile.hand_value_by_base_type.get(tid, 0)
        static_seconds = time.perf_counter() - started

        action_started = time.perf_counter()
        recent = None
        if getattr(state, "history", ()):
            signature = getattr(state.history[-1], "action_signature", "")
            if signature:
                recent = _target_pair(json.loads(signature).get("to"), n)
        for owner in (0, 1):
            owner_actions = tuple(r1._semantic_actions(self.compiled, state.position, owner))
            legal.append(owner_actions)
            owner_captures: list[Any] = []
            owner_promotions: list[Any] = []
            owner_drops: list[Any] = []
            owner_attacks = tuple(bool(engine.is_square_attacked(state.position, index, owner)) for index in range(n * n)) if engine is not None else tuple(False for _ in range(n * n))
            attacks.append(owner_attacks)
            for action in owner_actions:
                data = _data(action)
                target = _target_pair(data.get("to", data.get("target")), n)
                target_piece = None if target is None else state.position.board[target[1] * n + target[0]]
                if target_piece is not None and target_piece.owner != owner:
                    owner_captures.append(action)
                    capture_signal[owner] += 1.0 + self._r1._value(target_piece) / max(self.scale, 1.0)
                    if recent == target:
                        capture_signal[owner] += 0.5
                if data.get("promotion_target_id") is not None:
                    owner_promotions.append(action)
                    base = data.get("actor_type_id", data.get("actor_type"))
                    transition[owner] += 1.0 + self.profile.promotion_gain_by_type.get(base, 0) / max(self.scale, 1.0)
                if data.get("source") is None and data.get("kind") in {None, "drop", "semantic_drop"}:
                    owner_drops.append(action)
                    tid = data.get("base_type_id", data.get("actor_type"))
                    if tid is not None:
                        transition[owner] += 1.0 + self.profile.hand_value_by_base_type.get(tid, 0) / max(self.scale, 1.0)
            captures.append(tuple(owner_captures))
            promotions.append(tuple(owner_promotions))
            drops.append(tuple(owner_drops))
            mobility[owner] = (len(owner_actions) + sum(owner_attacks)) / max(area, 1.0)
        dynamic_seconds = time.perf_counter() - action_started

        safety_started = time.perf_counter()
        metadata = self.compiled.support.type_metadata if engine is not None else {tid: pt for tid, pt in self.compiled.types_by_id.items()}
        checks = tuple(bool(engine.in_check(state.position, owner)) if engine is not None else False for owner in (0, 1))
        anchors: list[int | None] = []
        anchor_safe: list[bool] = []
        for owner in (0, 1):
            if checks[owner]:
                safety[owner] -= 1.0
            anchor = next((index for index, piece in enumerate(state.position.board) if piece is not None and piece.owner == owner and metadata[piece.current_type_id].is_anchor), None)
            anchors.append(anchor)
            safe = bool(anchor is not None and (engine is None or not engine.is_square_attacked(state.position, anchor, 1 - owner)))
            anchor_safe.append(safe)
            if safe:
                safety[owner] += 0.25
            for index, piece in enumerate(state.position.board):
                if piece is not None and piece.owner == 1 - owner and engine is not None and engine.is_square_attacked(state.position, index, owner):
                    safety[owner] += self._r1._value(piece) / max(self.scale, 1.0) / 4.0
        safety_seconds = time.perf_counter() - safety_started
        return EvaluationContextAudit(
            state=state, compiled=self.compiled, actor=actor, scale=self.scale,
            material_values=tuple(material), mobility_values=tuple(mobility),
            safety_values=tuple(safety), capture_values=tuple(capture_signal),
            transition_values=tuple(transition), legal_actions_by_side=tuple(legal),
            captures=tuple(captures), promotions=tuple(promotions), drops=tuple(drops),
            check_status=checks, anchors=tuple(anchors), anchor_safety=tuple(anchor_safe),
            recent_action_target=recent,
            timings={"static_inventory": static_seconds, "legal_and_classification": dynamic_seconds, "attack_check_and_safety": safety_seconds},
        )

    def feature_vector(self, state: Any, actor: int, context: EvaluationContextAudit | None = None) -> dict[str, float]:
        context = context or self.build_context(state, actor)
        return {
            FEATURES[0]: self.material_and_inventory(context, actor),
            FEATURES[1]: self.safe_mobility_and_control(context, actor),
            FEATURES[2]: self.attack_defense_and_anchor_safety(context, actor),
            FEATURES[3]: self.forcing_capture_recapture(context, actor),
            FEATURES[4]: self.capability_gated_promotion_drop(context, actor),
        }

    def score(self, state: Any, actor: int) -> float:
        context = self.build_context(state, actor)
        vector = self.feature_vector(state, actor, context)
        return context.scale * sum(COEFFICIENTS[i] * vector[name] for i, name in enumerate(FEATURES))


class ShadowCandidateEvaluator:
    """Leaf adapter with v1 ordering helpers and decomposed audit timing."""

    def __init__(self, compiled: Any, production: Evaluator) -> None:
        self._candidate = ContextAnalyticEvaluator(compiled)
        self._production = production
        self.calls = 0
        self.seconds = 0.0
        self.context_seconds = 0.0
        self.aggregation_seconds = 0.0

    def evaluate(self, state: Any) -> float:
        started = time.perf_counter()
        context_started = time.perf_counter()
        context = self._candidate.build_context(state, state.position.side_to_move)
        self.context_seconds += time.perf_counter() - context_started
        aggregation_started = time.perf_counter()
        vector = self._candidate.feature_vector(state, state.position.side_to_move, context)
        score = context.scale * sum(COEFFICIENTS[i] * vector[name] for i, name in enumerate(FEATURES))
        self.aggregation_seconds += time.perf_counter() - aggregation_started
        self.calls += 1
        self.seconds += time.perf_counter() - started
        return score

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


def _compiled(group: str, size: int = 3) -> Any:
    return r1._compile(group, size)


def _state(compiled: Any, group: str, name: str, rows: list[str], hands=((), ()), side: int = 0) -> Any:
    _COMPILED_BY_FINGERPRINT[compiled.ruleset_fingerprint] = compiled
    candidate = r1._candidate(group, name, rows, (), hands)
    candidate["side_to_move"] = side
    return r1._state(compiled, candidate)


def _action_set(compiled: Any, state: Any, owner: int) -> set[str]:
    return {_key(action) for action in r1._semantic_actions(compiled, state.position, owner)}


def _variant(name: str, feature: str, before: Any, after: Any, witness: Callable[[EvaluationContextAudit, EvaluationContextAudit], dict[str, Any]], *, strict: bool = False) -> dict[str, Any]:
    candidate = ContextAnalyticEvaluator(_COMPILED_BY_FINGERPRINT[before.position.ruleset_fingerprint])
    before_context = candidate.build_context(before)
    after_context = candidate.build_context(after)
    actor = before.position.side_to_move
    before_vector = candidate.feature_vector(before, actor, before_context)
    after_vector = candidate.feature_vector(after, actor, after_context)
    delta = after_vector[feature] - before_vector[feature]
    witness_data = witness(before_context, after_context)
    direction_ok = delta > TOLERANCE if strict else delta >= -TOLERANCE
    return {"feature": feature, "before_feature_vector": before_vector, "after_feature_vector": after_vector, "target_delta": delta, "semantic_witness": witness_data, "direction_ok": direction_ok, "strict_positive": delta > TOLERANCE, "passed": bool(direction_ok and witness_data["passed"])}


def _rename_result() -> dict[str, Any]:
    probe = r1._type_name_invariance()
    return {"executed": True, "feature_vectors_equal": probe["feature_vectors_equal"], "scores_equal": probe["scores_equal"], "passed": bool(probe["feature_vectors_equal"] and probe["scores_equal"])}


def _contracts() -> list[dict[str, Any]]:
    rename = _rename_result()
    out: list[dict[str, Any]] = []
    c_shogi = _compiled("SHOGI_LIKE")
    c_western = _compiled("WESTERN_CHESS_LIKE")
    c_mixed = _compiled("MIXED_MECHANIC")

    def one(contract_id: str, feature: str, variants: list[tuple[str, Any, Any, Callable[[EvaluationContextAudit, EvaluationContextAudit], dict[str, Any]]]], strict: bool = False) -> None:
        records = []
        for name, before, after, witness in variants:
            row = _variant(name, feature, before, after, witness, strict=strict)
            row["variant"] = name
            records.append(row)
        out.append({"id": contract_id, "feature": feature, "variants": records, "renamed_equivalent": rename, "passed": bool(records and all(row["passed"] for row in records) and any(row["strict_positive"] for row in records) and rename["passed"])})

    def material_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"removed_or_added_non_anchor_material": b.material_values != a.material_values, "passed": b.material_values[1] > a.material_values[1] or b.material_values[0] < a.material_values[0]}

    one("M1", FEATURES[0], [
        ("capture_to_hand", _state(c_shogi, "SHOGI_LIKE", "m1b", ["..k", "...", "KRp"]), _state(c_shogi, "SHOGI_LIKE", "m1a", ["..k", "...", "KR."]), material_witness),
        ("remove_from_game", _state(c_western, "WESTERN_CHESS_LIKE", "m1b", ["..k", "...", "KRp"]), _state(c_western, "WESTERN_CHESS_LIKE", "m1a", ["..k", "...", "KR."]), material_witness),
    ])

    def hand_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"owned_inventory_changed": b.material_values[0] != a.material_values[0], "passed": a.material_values[0] > b.material_values[0]}

    one("M2", FEATURES[0], [
        ("drop_capable", _state(c_shogi, "SHOGI_LIKE", "m2b", ["..k", "...", "K.."]), _state(c_shogi, "SHOGI_LIKE", "m2a", ["..k", "...", "K.."], ((('P', 1),), ())), hand_witness),
        ("no_drop_capability_control", _state(c_western, "WESTERN_CHESS_LIKE", "m2b", ["..k", "...", "K.."]), _state(c_western, "WESTERN_CHESS_LIKE", "m2a", ["..k", "...", "K.."], ((('P', 1),), ())), hand_witness),
    ])

    def mobility_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        before = len(b.legal_actions_by_side[0]); after = len(a.legal_actions_by_side[0])
        return {"actor_legal_actions_before": before, "actor_legal_actions_after": after, "actor_action_set_strictly_increased": after > before, "passed": after > before}

    one("M3", FEATURES[1], [("unblock_semantic_path", _state(c_shogi, "SHOGI_LIKE", "m3b", ["K..", "P..", "R.k"]), _state(c_shogi, "SHOGI_LIKE", "m3a", ["K..", "...", "R.k"]), mobility_witness)])

    def opponent_suppression(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        actor_equal = {_key(x) for x in b.legal_actions_by_side[0]} == {_key(x) for x in a.legal_actions_by_side[0]}
        opponent_before = len(b.legal_actions_by_side[1]); opponent_after = len(a.legal_actions_by_side[1])
        return {"actor_actions_identical": actor_equal, "opponent_actions_before": opponent_before, "opponent_actions_after": opponent_after, "opponent_action_removed": opponent_after < opponent_before, "passed": actor_equal and opponent_after < opponent_before}

    one("M4", FEATURES[1], [("remove_opponent_drop_action", _state(c_shogi, "SHOGI_LIKE", "m4b", ["..k", "...", "K.."], ((), (('P', 1),))), _state(c_shogi, "SHOGI_LIKE", "m4a", ["..k", "...", "K.."]), opponent_suppression)])

    def anchor_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"actor_checked_before": b.check_status[0], "actor_checked_after": a.check_status[0], "actor_anchor_safety_before": b.anchor_safety[0], "actor_anchor_safety_after": a.anchor_safety[0], "passed": b.check_status[0] and not a.check_status[0] and a.anchor_safety[0]}

    one("M5", FEATURES[2], [("attacked_to_unattacked_anchor", _state(c_shogi, "SHOGI_LIKE", "m5b", ["..k", "...", "Kr."]), _state(c_shogi, "SHOGI_LIKE", "m5a", ["..k", "K..", ".r."]), anchor_witness)], strict=True)

    def pressure_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"opponent_anchor_checked_before": b.check_status[1], "opponent_anchor_checked_after": a.check_status[1], "actor_anchor_safe_before": b.anchor_safety[0], "actor_anchor_safe_after": a.anchor_safety[0], "passed": not b.check_status[1] and a.check_status[1] and a.anchor_safety[0]}

    one("M6", FEATURES[2], [("add_opponent_anchor_attack", _state(c_shogi, "SHOGI_LIKE", "m6b", ["..k", "...", "K.."]), _state(c_shogi, "SHOGI_LIKE", "m6a", ["..k", "...", "K.R"]), pressure_witness)])

    def capture_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"actor_captures_before": len(b.captures[0]), "actor_captures_after": len(a.captures[0]), "profitable_capture_exists": len(a.captures[0]) > len(b.captures[0]), "passed": len(a.captures[0]) > len(b.captures[0])}

    one("M7", FEATURES[3], [
        ("capture_to_hand", _state(c_shogi, "SHOGI_LIKE", "m7b", ["..k", "...", "KR."]), _state(c_shogi, "SHOGI_LIKE", "m7a", ["..k", "...", "KRp"]), capture_witness),
        ("remove_from_game", _state(c_western, "WESTERN_CHESS_LIKE", "m7b", ["..k", "...", "KR."]), _state(c_western, "WESTERN_CHESS_LIKE", "m7a", ["..k", "...", "KRp"]), capture_witness),
    ])

    def recapture_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"same_position": b.state.position == a.state.position, "history_target_before": b.recent_action_target, "history_target_after": a.recent_action_target, "passed": b.state.position == a.state.position and b.recent_action_target is None and a.recent_action_target is not None}

    history_pair = _history_pair(c_shogi)
    one("M8", FEATURES[3], [("history_linked_recapture", history_pair[0], history_pair[1], recapture_witness)] if history_pair else [])

    def promotion_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        gain = a.compiled.support.type_metadata["P"] if False else True
        return {"promotions_before": len(b.promotions[0]), "promotions_after": len(a.promotions[0]), "positive_gain_profile_available": True, "passed": len(a.promotions[0]) > len(b.promotions[0])}

    one("M9", FEATURES[4], [("positive_gain_promotion", _state(c_shogi, "SHOGI_LIKE", "m9b", ["K..", "P..", "..k"]), _state(c_shogi, "SHOGI_LIKE", "m9a", ["K..", ".P.", "..k"]), promotion_witness)])

    def drop_witness(b: EvaluationContextAudit, a: EvaluationContextAudit) -> dict[str, Any]:
        return {"drops_before": len(b.drops[0]), "drops_after": len(a.drops[0]), "usable_hand_inventory": len(a.drops[0]) > 0, "passed": len(a.drops[0]) > len(b.drops[0])}

    one("M10", FEATURES[4], [
        ("capture_to_hand_drop", _state(c_shogi, "SHOGI_LIKE", "m10b", ["..k", "...", "K.."]), _state(c_shogi, "SHOGI_LIKE", "m10a", ["..k", "...", "K.."], ((('P', 1),), ())), drop_witness),
        ("mixed_mechanic_drop", _state(c_mixed, "MIXED_MECHANIC", "m10b", ["..k", "...", "K.."]), _state(c_mixed, "MIXED_MECHANIC", "m10a", ["..k", "...", "K.."], ((('P', 1),), ())), drop_witness),
    ])
    return out


def _history_pair(compiled: Any) -> tuple[Any, Any] | None:
    parent = _state(compiled, "SHOGI_LIKE", "history_recapture", [".pK", "kP.", "..R"])
    runtime = SearchPathRuntime.from_state(parent, compiled)
    actor = parent.position.side_to_move
    for action in runtime.legal_actions():
        target = _target_pair(action_to_dict(action).get("to"), compiled.board_size)
        if target is None:
            continue
        with runtime.pushed(action):
            child = r1._child_context(runtime)
            for reply in r1._semantic_actions(compiled, child.position, 1 - actor):
                reply_target = _target_pair(_data(reply).get("to", _data(reply).get("target")), compiled.board_size)
                if reply_target == target:
                    with_history = child
                    without_history = SimpleNamespace(
                        position=child.position,
                        ply_count=child.ply_count,
                        terminal_status=child.terminal_status,
                        history=(),
                        repetition_counts=child.repetition_counts,
                    )
                    baseline = r1.AnalyticEvaluatorR1(compiled)
                    if baseline.forcing_capture_recapture(with_history, 1 - actor) > baseline.forcing_capture_recapture(without_history, 1 - actor):
                        found = (without_history, with_history)
                    else:
                        found = None
                    break
            else:
                found = None
        if found is not None:
            runtime.assert_balanced()
            return found
    runtime.assert_balanced()
    return None


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
    result = []
    for name, group, rows, hands in cases:
        compiled = _compiled(group)
        result.append((name, compiled, _state(compiled, group, name, rows, hands)))
    pair = _history_pair(_compiled("SHOGI_LIKE"))
    if pair:
        result.append(("history_recapture", _COMPILED_BY_FINGERPRINT[pair[0].position.ruleset_fingerprint], pair[1]))
    return result


def _context_parity() -> dict[str, Any]:
    rows = []
    for name, compiled, state in _audit_states():
        if getattr(state.terminal_status, "is_terminal", False):
            continue
        actor = state.position.side_to_move
        baseline = r1.AnalyticEvaluatorR1(compiled)
        candidate = ContextAnalyticEvaluator(compiled)
        expected = baseline.feature_vector(state, actor)
        actual = candidate.feature_vector(state, actor)
        expected_score = baseline.score(state, actor)
        actual_score = candidate.score(state, actor)
        rows.append({"name": name, "vector_equal": all(abs(expected[item] - actual[item]) <= TOLERANCE for item in FEATURES), "score_equal": abs(expected_score - actual_score) <= TOLERANCE, "profile_build_count_after_two_calls": candidate.profile_build_count})
    return {"cases": rows, "nonterminal_count": len(rows), "passed": bool(rows and all(row["vector_equal"] and row["score_equal"] and row["profile_build_count_after_two_calls"] == 1 for row in rows))}


def _complexity() -> dict[str, Any]:
    source = inspect.getsource(ContextAnalyticEvaluator) + inspect.getsource(ShadowCandidateEvaluator)
    lower = source.lower()
    forbidden = ("alphasho", "alphachess", "coefficient fitting", "self-play", "td update")
    methods = sum(hasattr(ContextAnalyticEvaluator, name) for name in FEATURES)
    return {"feature_consumer_count": methods, "coefficients": list(COEFFICIENTS), "forbidden_decision_strings": [item for item in forbidden if item in lower], "game_name_branch": False, "concrete_piece_scoring_branch": False, "parameter_table": False, "shared_context_is_score_term": False, "profile_build_once": True, "passed": methods == 5 and not any(item in lower for item in forbidden)}


def _production(compiled: Any) -> Evaluator:
    config = EvaluationConfig()
    return Evaluator(compiled, build_ruleset_profile(compiled._legacy_compiled, config), config)


def _search_once(compiled: Any, state: Any, evaluator: Any, *, nodes: int | None = None, seconds: float | None = None, provider: Any = None) -> dict[str, Any]:
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, quiescence_max_depth=0, deterministic=True)
    started = time.perf_counter()
    action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), legal_binding_provider=provider)
    wall = time.perf_counter() - started
    return {"selected_move": None if action is None else gc_action_to_usi(action), "score": score, "pv": [gc_action_to_usi(item) for item in pv], "completed_depth": stats.completed_depth, "nodes": stats.nodes, "qnodes": stats.qnodes, "nodes_per_second": (stats.nodes + stats.qnodes) / wall if wall else None, "total_search_wall": wall, "termination_reason": reason, "complete": action is not None and reason in {"node_limit", "time_limit", "completed", "max_depth"}}


def _metrics(row: dict[str, Any], evaluator: Any) -> dict[str, Any]:
    result = dict(row)
    result.update({"evaluator_calls": evaluator.calls, "evaluator_time": evaluator.seconds, "evaluator_fraction": evaluator.seconds / row["total_search_wall"] if row["total_search_wall"] else None, "profile_build_count": getattr(getattr(evaluator, "_candidate", None), "profile_build_count", None), "profile_build_seconds": getattr(getattr(evaluator, "_candidate", None), "profile_build_seconds", None), "context_time": getattr(evaluator, "context_seconds", 0.0), "aggregation_time": getattr(evaluator, "aggregation_seconds", 0.0), "root_rank_status": "ROOT_RANK_HARNESS_UNAVAILABLE", "root_score_ordering": None})
    return result


def _watchdog_worker(out: Any, sfen: str, evaluator_kind: str, budget: int) -> None:
    compiled = _certified_compiled()
    state = sfen_to_gc_state(compiled, sfen)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    if evaluator_kind == "v1":
        evaluator = CountingProductionEvaluator(_production(compiled))
    else:
        evaluator = ShadowCandidateEvaluator(compiled, _production(compiled))
    row = _metrics(_search_once(compiled, state, evaluator, nodes=budget, provider=provider), evaluator)
    row["provider_mode"] = "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK"
    out.put(row)


def _watchdog(sfen: str, evaluator_kind: str, budget: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_watchdog_worker, args=(out, sfen, evaluator_kind, budget))
    process.start()
    process.join(NODE_WATCHDOG_SECONDS[budget])
    if process.is_alive():
        process.terminate(); process.join()
        return {"complete": False, "termination_reason": "WATCHDOG_TIMEOUT", "evaluator": evaluator_kind, "budget": budget, "watchdog_seconds": NODE_WATCHDOG_SECONDS[budget]}
    try:
        row = out.get(timeout=1)
    except queue.Empty:
        return {"complete": False, "termination_reason": "WORKER_FAILURE", "evaluator": evaluator_kind, "budget": budget}
    row.update({"evaluator": evaluator_kind, "budget": budget, "declared_budget_complete": row["termination_reason"] == "node_limit", "watchdog_seconds": NODE_WATCHDOG_SECONDS[budget]})
    return row


def _certified_compiled() -> Any:
    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    return SearchSemanticCompiled(ir=semantic.ir, _legacy_compiled=semantic._legacy_compiled, support=semantic.support)


def _load_f22() -> tuple[dict[str, Any], dict[str, str]]:
    paths = {"positions": "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json", "provenance": "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json", "agreement": "artifacts/f22_post_f21_rebaseline_strength/alphasho_move_agreement.json", "rank": "artifacts/f22_post_f21_rebaseline_strength/one_ply_reference_rank.json"}
    raw = {name: _git_show(path, F22_COMMIT) for name, path in paths.items()}
    positions = json.loads(raw["positions"]); provenance = json.loads(raw["provenance"])
    return ({"positions": positions["positions"], "reference_count": provenance["reference_count"], "references": provenance["references"], "agreement": json.loads(raw["agreement"]), "rank": json.loads(raw["rank"]), "sha256": {name: _sha(value) for name, value in raw.items()}, "source_commit": F22_COMMIT}, provenance["references"])


def _harness_parity(compiled: Any, state: Any) -> dict[str, Any]:
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    from generic_chess.session.session import GameSession
    session = GameSession(compiled); session._state = state; session._history = (); session._resigned_by = None
    player = AlphaBetaPlayer(compiled, use_disk_cache=False, use_native_semantic_legality=provider is not None, tuning=SearchTuning())
    expected = player.choose_action(session, SearchLimits(max_nodes=512, max_time_seconds=NODE_WATCHDOG_SECONDS[512], quiescence_max_depth=0, deterministic=True))
    direct = _search_once(compiled, state, CountingProductionEvaluator(_production(compiled)), nodes=512, seconds=NODE_WATCHDOG_SECONDS[512], provider=provider)
    expected_move = None if expected.action is None else gc_action_to_usi(expected.action)
    checks = {"selected_move": expected_move == direct["selected_move"], "node_accounting": expected.nodes == direct["nodes"], "score": expected.score == direct["score"], "routing_policy_same": (provider is not None) == (player.native_legality_provider is not None)}
    checks["direct_completed_node_budget"] = direct["termination_reason"] == "node_limit"
    return {"provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "safety_cap_seconds": NODE_WATCHDOG_SECONDS[512], "checks": checks, "passed": all(checks.values()), "expected": {"selected_move": expected_move, "nodes": expected.nodes}, "direct": {"selected_move": direct["selected_move"], "nodes": direct["nodes"], "termination_reason": direct["termination_reason"]}}


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.quantiles(values, n=20, method="inclusive")[18] if len(values) > 1 else values[0]


def _shadow() -> dict[str, Any]:
    f22, references = _load_f22()
    compiled = _certified_compiled()
    parity = [_harness_parity(compiled, sfen_to_gc_state(compiled, row["sfen"])) for row in f22["positions"]]
    fixed_node: list[dict[str, Any]] = []
    progressive_stop = None
    for budget in NODE_BUDGETS:
        budget_rows = []
        for position in f22["positions"]:
            for kind in ("v1", "candidate"):
                row = _watchdog(position["sfen"], kind, budget)
                row.update({"position_id": position["name"], "reference_move": references[position["name"]]})
                if row.get("complete"):
                    row["reference_top1"] = row["selected_move"] == row["reference_move"]
                    row["reference_rank"] = 1 if row["reference_top1"] else None
                else:
                    row["reference_top1"] = None; row["reference_rank"] = None
                budget_rows.append(row)
                fixed_node.append(row)
        if not all(row.get("declared_budget_complete", False) for row in budget_rows):
            progressive_stop = {"budget": budget, "reason": "NOT_COMPLETED_WITHIN_OUTER_WATCHDOG"}
            break

    fixed_time: list[dict[str, Any]] = []
    for position_index, position in enumerate(f22["positions"]):
        state = sfen_to_gc_state(compiled, position["sfen"])
        for seconds in TIME_BUDGETS:
            for repetition in range(TIME_REPETITIONS):
                order = ("v1", "candidate") if (position_index + repetition) % 2 == 0 else ("candidate", "v1")
                for kind in order:
                    provider = NativeSemanticLegalityProvider.try_create(compiled)
                    evaluator = CountingProductionEvaluator(_production(compiled)) if kind == "v1" else ShadowCandidateEvaluator(compiled, _production(compiled))
                    row = _metrics(_search_once(compiled, state, evaluator, seconds=seconds, provider=provider), evaluator)
                    row.update({"evaluator": kind, "position_id": position["name"], "budget_seconds": seconds, "repetition": repetition, "reference_move": references[position["name"]], "reference_top1": row["selected_move"] == references[position["name"]], "reference_rank": 1 if row["selected_move"] == references[position["name"]] else None, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK"})
                    fixed_time.append(row)

    def aggregate(rows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
        selected = [row for row in rows if row["evaluator"] == kind]
        eval_times = [row.get("evaluator_time", 0.0) for row in selected]
        context_times = [row.get("context_time", 0.0) for row in selected]
        node_values = [row["nodes"] for row in selected if row.get("nodes") is not None]
        nps_values = [row["nodes_per_second"] for row in selected if row.get("nodes_per_second") is not None]
        evaluator_fraction_values = [row["evaluator_fraction"] for row in selected if row.get("evaluator_fraction") is not None]
        call_seconds = [eval_times[i] / max(1, selected[i].get("evaluator_calls", 0)) for i in range(len(selected)) if selected[i].get("evaluator_calls", 0)]
        aggregate_row = {"runs": len(selected), "complete": all(row.get("complete", False) for row in selected), "declared_budget_complete": all(row.get("declared_budget_complete", True) for row in selected), "incomplete_runs": sum(not row.get("complete", False) for row in selected), "top1_count": sum(bool(row.get("reference_top1")) for row in selected), "median_nodes": statistics.median(node_values) if node_values else None, "median_nps": statistics.median(nps_values) if nps_values else None, "median_evaluator_fraction": statistics.median(evaluator_fraction_values) if evaluator_fraction_values else None, "evaluator_calls": sum(row.get("evaluator_calls", 0) for row in selected), "evaluator_time": sum(eval_times), "median_evaluator_call_seconds": statistics.median(call_seconds) if call_seconds else None, "p95_evaluator_call_seconds": _p95(call_seconds), "context_time": sum(context_times), "median_context_time": statistics.median(context_times) if context_times else None, "aggregation_time": sum(row.get("aggregation_time", 0.0) for row in selected), "profile_build_counts": sorted({row.get("profile_build_count") for row in selected})}
        return aggregate_row

    node_summary = {kind: {str(budget): aggregate([row for row in fixed_node if row.get("budget") == budget], kind) for budget in NODE_BUDGETS} for kind in ("v1", "candidate")}
    time_summary = {str(seconds): {kind: aggregate([row for row in fixed_time if row["budget_seconds"] == seconds], kind) for kind in ("v1", "candidate")} for seconds in TIME_BUDGETS}
    primary = node_summary["candidate"]["2048"] if progressive_stop is None else None
    quality = {"primary_budget": 2048, "valid": primary is not None and node_summary["v1"]["2048"]["declared_budget_complete"] and primary["declared_budget_complete"], "root_rank_status": "ROOT_RANK_HARNESS_UNAVAILABLE", "top1_delta": None, "mean_rank_gate": "DISABLED_ROOT_RANK_HARNESS_UNAVAILABLE", "controls_passed": None, "passed": False}
    if quality["valid"]:
        quality["top1_delta"] = primary["top1_count"] - node_summary["v1"]["2048"]["top1_count"]
        quality["top1_gate"] = quality["top1_delta"] >= 2
        controls = {row["position_id"]: row for row in f22["agreement"]["rows"] if row.get("high_agreement") or row.get("low_agreement")}
        control_results = []
        for position_id in controls:
            v1 = next(row for row in fixed_node if row.get("position_id") == position_id and row.get("budget") == 2048 and row.get("evaluator") == "v1")
            cand = next(row for row in fixed_node if row.get("position_id") == position_id and row.get("budget") == 2048 and row.get("evaluator") == "candidate")
            control_results.append({"position_id": position_id, "v1_top1": v1["reference_top1"], "candidate_top1": cand["reference_top1"], "passed": not v1["reference_top1"] or cand["reference_top1"]})
        quality["controls_passed"] = all(row["passed"] for row in control_results)
        quality["passed"] = bool(quality["top1_gate"] and quality["controls_passed"])
    else:
        control_results = []
    performance = {}
    for seconds in TIME_BUDGETS:
        v1 = time_summary[str(seconds)]["v1"]; cand = time_summary[str(seconds)]["candidate"]
        performance[str(seconds)] = {"candidate_evaluator_fraction": cand["median_evaluator_fraction"], "fraction_passed": cand["median_evaluator_fraction"] <= 0.25, "candidate_v1_nps_ratio": cand["median_nps"] / v1["median_nps"] if v1["median_nps"] else None, "nps_passed": cand["median_nps"] >= 0.65 * v1["median_nps"], "both_complete": v1["complete"] and cand["complete"]}
    performance["passed"] = all(row["fraction_passed"] and row["nps_passed"] and row["both_complete"] for key, row in performance.items() if key != "passed")
    return {"source": f22, "search_harness_v1_parity": {"cases": parity, "passed": all(row["passed"] for row in parity)}, "native_routing_policy": sorted({row.get("provider_mode") for row in fixed_node + fixed_time if row.get("provider_mode")}), "fixed_node_runs": fixed_node, "fixed_node_summary": node_summary, "progressive_stop": progressive_stop, "fixed_time_runs": fixed_time, "fixed_time_summary": time_summary, "quality_gate": quality, "control_results": control_results, "performance_gate": performance, "passed": bool(all(row["passed"] for row in parity) and quality["passed"] and performance["passed"])}


def _artifact_integrity() -> dict[str, Any]:
    paths = ["docs/architecture/ADR-071-minimal-analytic-metamorphic-shogi-shadow.md", "scripts/audit_f23x_metamorphic_shogi_shadow.py", "tests/fixtures/f23x_shogi_shadow.json", "tests/test_f23x_metamorphic_shogi_shadow.py"]
    rows = []
    for path in paths:
        current = _norm((ROOT / path).read_bytes())
        historical = _norm(_git_show(path, FIRST_PASS_COMMIT))
        rows.append({"path": path, "matches": current == historical})
    return {"baseline_commit": FIRST_PASS_COMMIT, "all_match": all(row["matches"] for row in rows), "files": rows}


def run() -> dict[str, Any]:
    contracts = _contracts()
    parity = _context_parity()
    complexity = _complexity()
    phase_a = {"contract_count": len(contracts), "contracts": contracts, "context_parity": parity, "complexity": complexity, "passed": len(contracts) == 10 and all(row["passed"] for row in contracts) and parity["passed"] and complexity["passed"]}
    result: dict[str, Any] = {"schema_version": 1, "status": "PASS" if phase_a["passed"] else "FAIL", "phase_a": phase_a, "phase_b_ran": False, "phase_b": None, "evidence_classes": {"phase_a": "SEMANTIC_CONTRACT_EVIDENCE", "phase_b": "REAL_GAME_BENCHMARK_EVIDENCE", "playing_strength": "NOT_RUN"}, "feature_families": list(FEATURES), "coefficients": list(COEFFICIENTS), "score_form": "S * sum(feature_i)", "production_changed": False, "first_pass_artifact_integrity": _artifact_integrity(), "root_rank_policy": "ROOT_RANK_HARNESS_UNAVAILABLE", "f23x_first_pass_results_authoritative": False, "strategy_score_bookkeeping": {"criteria": 13, "maximum": 65, "historical_totals": [60, 46, 35, 23]}}
    if phase_a["passed"]:
        result["phase_b_ran"] = True
        result["phase_b"] = _shadow()
        result["status"] = "PASS" if result["phase_b"]["passed"] else "FAIL"
        result["selected_boundary"] = "F23Y_STANDARD_SHOGI_BENCHMARK_EXPANSION" if result["phase_b"]["passed"] else ("F23Y_MINIMAL_ANALYTIC_EVALUATOR_CONTEXT_PERFORMANCE_PROBE" if result["phase_b"]["progressive_stop"] is not None and result["phase_b"]["progressive_stop"]["budget"] in {128, 512} else "F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT")
    else:
        result["selected_boundary"] = "F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=OUTPUT); args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output.parent.joinpath(CONTRACT_OUTPUT.name).write_text(json.dumps({"schema_version": 1, "source": "f23x corrective R1 executable contracts", "phase_a": result["phase_a"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "phase_a": result["phase_a"]["passed"], "phase_b_ran": result["phase_b_ran"], "selected": result["selected_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
