"""F23V audit-only five-concept analytic evaluator signal probe."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import multiprocessing
import queue
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
FIXTURES = TESTS / "fixtures"
PLAN = FIXTURES / "f23v_minimal_analytic_plan.json"
OUTPUT = FIXTURES / "f23v_minimal_analytic_signal.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_to_dict
from generic_chess.core.attacks import is_in_check, is_square_attacked, pseudo_attacks
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.rules.compiler import compile_ruleset, compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RulePathConstraint,
    RuleReplaceSelector, RuleSemanticAction, RuleSet, RuleTypeRef,
)
from scripts import exact_generic_horizon_abstraction_v2 as abstraction
from scripts import exact_generic_preference_solver_v3 as v3


FEATURE_NAMES = (
    "material_and_inventory",
    "safe_mobility_and_control",
    "attack_defense_and_anchor_safety",
    "forcing_capture_recapture",
    "capability_gated_promotion_drop",
)
COEFFICIENTS = (1, 1, 1, 1, 1)
REFERENCE_NODES = 100_000
REFERENCE_WALL_SECONDS = 8


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _action_key(action: dict[str, Any]) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _rows(n: int, pieces: dict[tuple[int, int], str]) -> list[str]:
    board = [["."] * n for _ in range(n)]
    for (file, rank), piece in pieces.items():
        board[rank][file] = piece
    return ["".join(row) for row in reversed(board)]


def _empty_initial(n: int, anchor_tid: str = "K") -> tuple[tuple[Piece | None, ...], ...]:
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, anchor_tid, anchor_tid)
    rows[n - 1][n - 1] = Piece(1, anchor_tid, anchor_tid)
    return tuple(tuple(row) for row in rows)


def _king(tid: str = "K") -> PieceType:
    return PieceType(tid, tid, tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)), is_anchor=True)


def _ray(tid: str = "R") -> PieceType:
    return PieceType(tid, tid, (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))))


def _pawn(tid: str = "P", target: str = "G") -> PieceType:
    return PieceType(tid, tid, (RayAtom((0, 1)),), is_promotable=True, promotion_target_ids=(target,))


def _promotion(n: int, tid: str, target: str) -> dict[str, tuple[frozenset[Square | tuple[int, int]], ...]]:
    source = Square(1 % n, max(0, n - 2))
    dest = Square(1 % n, n - 1)
    return {tid: (frozenset({(source, dest)}), frozenset({(source, dest)}))}


def _drop_masks(n: int, type_ids: tuple[str, ...], enabled: tuple[str, ...] = ()) -> dict[str, tuple[tuple[bool, ...], tuple[bool, ...]]]:
    true_mask = (True,) * (n * n)
    false_mask = (False,) * (n * n)
    return {tid: (true_mask, true_mask) if tid in enabled else (false_mask, false_mask) for tid in type_ids}


def _ref(kind: str, **kwargs):
    from generic_chess.rules.schema import RuleSquareRef
    return RuleSquareRef(kind=kind, **kwargs)


def _capture_action(name: str, tid: str, disposition: str, *, path_count: int | None = None) -> RuleSemanticAction:
    constraints = () if path_count is None else (RulePathConstraint("path_count_eq", count=path_count),)
    return RuleSemanticAction(
        name=name,
        type_ids=(tid,),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(type_ids=(tid,), action_family="board", target_relation="enemy", geometry_kind="ray", replace_all_matching=True),
        path_constraints=constraints,
        effects=(
            RuleActionEffect("remove", square_ref=_ref("target"), disposition=disposition, piece_owner="opponent"),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )


def _drop_action(tid: str = "P") -> RuleSemanticAction:
    return RuleSemanticAction(
        name="semantic_drop_inventory",
        type_ids=(tid,),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(type_ids=(tid,), action_family="drop", target_relation="empty"),
        effects=(
            RuleActionEffect("remove_from_hand", piece_type_ref=RuleTypeRef(kind="action_base")),
            RuleActionEffect("place", to_ref=_ref("target"), piece_type_ref=RuleTypeRef(kind="action_base")),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )


def _rule_set(group: str, n: int) -> RuleSet:
    """Build one of three rule families; labels never enter feature scoring."""
    common = [_king(), _ray()]
    if group == "SHOGI_LIKE":
        common += [_pawn(), PieceType("G", "G", (LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1))))]
        return RuleSet(board_size=n, piece_types=tuple(common), initial_position=_empty_initial(n), drop_allowed=_drop_masks(n, ("R", "P", "G"), ("P",)), promotion_allowed=_promotion(n, "P", "G"), promotion_forced={"P": (frozenset(), frozenset())}, max_ply=11, repetition_limit=2, semantic_actions=(_capture_action("semantic_capture_to_hand", "P", "capture_to_hand"), _drop_action()))
    if group == "WESTERN_CHESS_LIKE":
        common += [_pawn("P", "G"), PieceType("G", "G", (RayAtom((1, 0)), RayAtom((-1, 0))))]
        return RuleSet(board_size=n, piece_types=tuple(common), initial_position=_empty_initial(n), drop_allowed=_drop_masks(n, ("R", "P", "G")), promotion_allowed=_promotion(n, "P", "G"), promotion_forced={"P": (frozenset(), frozenset())}, max_ply=11, repetition_limit=2, semantic_actions=(_capture_action("semantic_remove_from_game", "P", "remove_from_game"),))
    common += [
        _pawn(),
        PieceType("G", "G", (LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1)))),
        _pawn("X", "XG"),
        PieceType("XG", "XG", (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1)))),
        _ray("Z"),
    ]
    actions = (
        _capture_action("semantic_capture_to_hand", "P", "capture_to_hand"),
        _drop_action(),
        _capture_action("semantic_remove_from_game", "X", "remove_from_game"),
        _capture_action("semantic_path_restricted", "Z", "remove_from_game", path_count=1),
    )
    return RuleSet(board_size=n, piece_types=tuple(common), initial_position=_empty_initial(n), drop_allowed=_drop_masks(n, ("R", "P", "G", "X", "XG", "Z"), ("P",)), promotion_allowed=_promotion(n, "P", "G") | _promotion(n, "X", "XG"), promotion_forced={"P": (frozenset(), frozenset()), "X": (frozenset(), frozenset())}, max_ply=11, repetition_limit=2, semantic_actions=actions)


def _compile(group: str, n: int):
    rules = _rule_set(group, n)
    return compile_semantic_ruleset(rules)


def _state(compiled, rows: list[str], *, side: int = 0, hands: tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]] = ((), ())):
    n = compiled.board_size
    board = []
    for row in reversed(rows):
        for char in row:
            if char == ".":
                board.append(None)
            else:
                owner = 1 if char.islower() else 0
                tid = char.upper()
                board.append(Piece(owner, tid, tid))
    position = Position(board=tuple(board), hands=(Hands(hands[0]), Hands(hands[1])), side_to_move=side, ruleset_fingerprint=compiled.ruleset_fingerprint)
    return GameState(position=position, ply_count=0, repetition_counts=(), terminal_status=TerminalResult(TerminalStatus.ONGOING), history=())


def _templates() -> list[dict[str, Any]]:
    source = json.loads((FIXTURES / "evaluator_v2_corpus_v12.json").read_text(encoding="utf-8"))
    wanted = ["f23t-r10-ordinary_anchor_terminal-0083c9acfd", "f23t-r10-ordinary_anchor_terminal-01ed38866d", "f23t-r10-ordinary_anchor_terminal-04645fdfdd", "f23t-r10-ordinary_anchor_terminal-04d358dd8c", "f23t-r10-ordinary_anchor_terminal-05b3a964bb", "f23t-r10-ordinary_anchor_terminal-082079cd84", "f23t-r10-ordinary_anchor_terminal-09877091ff", "f23t-r10-ordinary_anchor_terminal-0a2863e1b8"]
    rows = {item["id"]: item["candidate"] for item in source["records"]}
    return [{key: value for key, value in rows[item].items() if key in {"board_size", "rows", "side_to_move", "hands"}} for item in wanted]


def make_plan() -> dict[str, Any]:
    candidates = []
    for group in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC"):
        for index, template in enumerate(_templates()):
            candidates.append({"group": group, "index": index, **template})
    body = {
        "plan_version": "f23v-minimal-analytic-evaluator-signal-probe-v1",
        "source_templates": "f23t V12 structural candidates; no V12 outcomes copied into plan",
        "group_counts": {group: 8 for group in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC")},
        "candidate_count": len(candidates),
        "candidate_order": candidates,
        "reference_contract": {"v3": {"max_nodes": REFERENCE_NODES, "max_depth": None, "wall_seconds": REFERENCE_WALL_SECONDS}, "abstraction": {"max_nodes": REFERENCE_NODES, "wall_seconds": REFERENCE_WALL_SECONDS}},
        "evaluator_blind": True,
    }
    body["plan_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def _worker(out, group: str, candidate: dict[str, Any], kind: str):
    compiled = _compile(group, candidate["board_size"])
    hands = tuple(tuple(tuple(item) for item in owner) for owner in candidate.get("hands", ((), ())))
    state = _state(compiled, candidate["rows"], side=candidate.get("side_to_move", 0), hands=hands)
    result = v3.solve_root_threshold_v3(compiled, state, max_nodes=REFERENCE_NODES, max_depth=None) if kind == "v3" else abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=REFERENCE_NODES)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": [{"action": row["action"], "value": row["value"]} for row in result.action_values], "proof_depth": result.max_proof_ply, "stats": result.stats, "unresolved_reason": result.unresolved_reason})


def _isolated(group: str, candidate: dict[str, Any], kind: str) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, group, candidate, kind))
    process.start(); process.join(REFERENCE_WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "TIME_CAP"}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "WORKER_FAILURE"}


def _admit(plan: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for candidate in plan["candidate_order"]:
        v3_result = _isolated(candidate["group"], candidate, "v3")
        row = {"group": candidate["group"], "index": candidate["index"], "candidate": candidate, "v3": v3_result, "abstract": None, "admitted": False}
        values = {item["value"] for item in v3_result["action_values"]}
        if v3_result["strong"] and len(values) >= 2:
            abstract_result = _isolated(candidate["group"], candidate, "abstract")
            row["abstract"] = abstract_result
            exact_sig = (sorted((json.dumps(item["action"], sort_keys=True), item["value"]) for item in v3_result["action_values"]), sorted(json.dumps(item, sort_keys=True) for item in v3_result["optimal_actions"]))
            abstract_sig = (sorted((json.dumps(item["action"], sort_keys=True), item["value"]) for item in abstract_result["action_values"]), sorted(json.dumps(item, sort_keys=True) for item in abstract_result["optimal_actions"]))
            row["admitted"] = bool(abstract_result["strong"] and exact_sig == abstract_sig)
        records.append(row)
    return records


def _position_for_owner(state: GameState, owner: int) -> GameState:
    return replace(state, position=replace(state.position, side_to_move=owner), terminal_status=TerminalResult(TerminalStatus.ONGOING))


class AnalyticEvaluator:
    """Five fixed, bounded, rule-derived concepts; no fitting or game labels."""

    def __init__(self, compiled):
        self.compiled = compiled
        # Semantic rulesets expose the generic support/IR product to Core;
        # the existing profile and geometric attack helpers intentionally
        # consume the compiler's legacy movement view.  This is an audit
        # adapter only: legal actions and transitions still use ``compiled``.
        self.analysis_compiled = getattr(compiled, "_legacy_compiled", None) or compiled
        self.profile = build_ruleset_profile(self.analysis_compiled, EvaluationConfig())
        self.scale = float(max(1, self.profile.median_non_anchor_value))

    def _analysis_state(self, state: GameState) -> GameState:
        if self.analysis_compiled is self.compiled:
            return state
        position = replace(
            state.position,
            ruleset_fingerprint=self.analysis_compiled.ruleset_fingerprint,
        )
        return replace(state, position=position)

    def _legal(self, state: GameState, owner: int):
        return SearchPathRuntime.from_state(_position_for_owner(state, owner), self.compiled)

    def _relative(self, values: tuple[float, float], actor: int) -> float:
        delta = values[0] - values[1]
        return delta if actor == 0 else -delta

    def _value(self, piece) -> float:
        return float(self.profile.board_value_by_type[piece.current_type_id])

    def material_and_inventory(self, state: GameState, actor: int) -> float:
        values = [0.0, 0.0]
        for piece in state.position.board:
            if piece is not None:
                values[piece.owner] += self._value(piece)
        for owner in (0, 1):
            for tid, count in state.position.hands[owner].counts:
                values[owner] += count * self.profile.hand_value_by_base_type.get(tid, 0)
        return _clamp(self._relative((values[0], values[1]), actor) / max(self.scale * 4.0, 1.0))

    def safe_mobility_and_control(self, state: GameState, actor: int) -> float:
        values = []
        area = float(self.compiled.board_size * self.compiled.board_size)
        for owner in (0, 1):
            runtime = self._legal(state, owner)
            legal = runtime.legal_actions()
            attacks = len(pseudo_attacks(self._analysis_state(state).position, owner, self.analysis_compiled))
            values.append((len(legal) + attacks) / max(area, 1.0))
            runtime.assert_balanced()
        return _clamp(self._relative((values[0], values[1]), actor) / 4.0)

    def attack_defense_and_anchor_safety(self, state: GameState, actor: int) -> float:
        values = [0.0, 0.0]
        area = float(self.compiled.board_size * self.compiled.board_size)
        for owner in (0, 1):
            analysis_state = self._analysis_state(state)
            checked = is_in_check(analysis_state.position, owner, self.analysis_compiled)
            if checked:
                values[owner] -= 1.0
            anchor_idx = next((idx for idx, piece in enumerate(state.position.board) if piece is not None and piece.owner == owner and self.analysis_compiled.types_by_id[piece.current_type_id].is_anchor), None)
            if anchor_idx is not None:
                square = Square(anchor_idx % self.compiled.board_size, anchor_idx // self.compiled.board_size)
                if not is_square_attacked(analysis_state.position, square, 1 - owner, self.analysis_compiled):
                    values[owner] += 0.25
            attacks = pseudo_attacks(analysis_state.position, owner, self.analysis_compiled)
            for idx, piece in enumerate(state.position.board):
                if piece is not None and piece.owner == 1 - owner and Square(idx % self.compiled.board_size, idx // self.compiled.board_size) in attacks:
                    values[owner] += self._value(piece) / max(self.scale, 1.0) / 4.0
        return _clamp(self._relative((values[0], values[1]), actor) / max(area / 4.0, 1.0))

    def forcing_capture_recapture(self, state: GameState, actor: int) -> float:
        values = [0.0, 0.0]
        for owner in (0, 1):
            runtime = self._legal(state, owner)
            last_target = None
            for action in runtime.legal_actions():
                data = action_to_dict(action)
                if "to" not in data:
                    continue
                file, rank = data["to"]
                target = state.position.board[rank * self.compiled.board_size + file]
                if target is not None and target.owner != owner:
                    values[owner] += 1.0 + self._value(target) / max(self.scale, 1.0)
                    if last_target is not None and (file, rank) == last_target:
                        values[owner] += 0.5
            runtime.assert_balanced()
        return _clamp(self._relative((values[0], values[1]), actor) / 4.0)

    def capability_gated_promotion_drop(self, state: GameState, actor: int) -> float:
        values = [0.0, 0.0]
        for owner in (0, 1):
            runtime = self._legal(state, owner)
            for action in runtime.legal_actions():
                data = action_to_dict(action)
                if data.get("promotion_target_id") is not None:
                    base = data.get("actor_type_id", data.get("base_type_id"))
                    values[owner] += 1.0 + self.profile.promotion_gain_by_type.get(base, 0) / max(self.scale, 1.0)
                if data.get("kind") in {"drop", "semantic_drop"}:
                    tid = data.get("base_type_id")
                    values[owner] += 1.0 + self.profile.hand_value_by_base_type.get(tid, 0) / max(self.scale, 1.0)
            runtime.assert_balanced()
        return _clamp(self._relative((values[0], values[1]), actor) / 4.0)

    def feature_vector(self, state: GameState, actor: int) -> dict[str, float]:
        values = {
            name: getattr(self, name)(state, actor)
            for name in FEATURE_NAMES
        }
        assert all(-1.0 <= value <= 1.0 for value in values.values())
        return values

    def score(self, state: GameState, actor: int) -> float:
        values = self.feature_vector(state, actor)
        return self.scale * sum(COEFFICIENTS[index] * values[name] for index, name in enumerate(FEATURE_NAMES))


def _terminal_score(state: GameState, actor: int) -> float | None:
    status = state.terminal_status
    if status.status is TerminalStatus.ONGOING:
        return None
    if status.status is TerminalStatus.CHECKMATE:
        return 1.0 if status.winner == actor else -1.0
    return 0.0


def _rank_record(row: dict[str, Any]) -> dict[str, Any]:
    candidate = row["candidate"]
    compiled = _compile(candidate["group"], candidate["board_size"])
    hands = tuple(tuple(tuple(item) for item in owner) for owner in candidate.get("hands", ((), ())))
    state = _state(compiled, candidate["rows"], side=candidate.get("side_to_move", 0), hands=hands)
    actor = state.position.side_to_move
    runtime = SearchPathRuntime.from_state(state, compiled)
    evaluator = AnalyticEvaluator(compiled)
    scored = []
    score_times = []
    for action in runtime.legal_actions():
        with runtime.pushed(action) as child:
            child_state = GameState(child.position, child.ply_count, state.repetition_counts, child.terminal_status, state.history)
            terminal = _terminal_score(child_state, actor)
            started = time.perf_counter()
            score = terminal if terminal is not None else evaluator.score(child_state, actor)
            score_times.append(time.perf_counter() - started)
            scored.append({"action": action_to_dict(action), "score": score, "features": evaluator.feature_vector(child_state, actor) if terminal is None else None})
    runtime.assert_balanced()
    max_score = max(item["score"] for item in scored)
    top = [item["action"] for item in scored if abs(item["score"] - max_score) <= 1e-12]
    exact_values = row["v3"]["action_values"]
    exact_optimal = row["v3"]["optimal_actions"]
    exact_by_key = {_action_key(item["action"]): item["value"] for item in exact_values}
    top_keys = {_action_key(action) for action in top}
    optimal_keys = {_action_key(action) for action in exact_optimal}
    informative = [(left, right) for left in exact_values for right in exact_values if left["value"] != right["value"] and left["value"] in {"WIN", "DRAW", "LOSS"} and right["value"] in {"WIN", "DRAW", "LOSS"}]
    correct_pairs = 0
    for left, right in informative:
        expected = {"LOSS": 0, "DRAW": 1, "WIN": 2}[left["value"]] > {"LOSS": 0, "DRAW": 1, "WIN": 2}[right["value"]]
        observed = next(item["score"] for item in scored if _action_key(item["action"]) == _action_key(left["action"])) > next(item["score"] for item in scored if _action_key(item["action"]) == _action_key(right["action"]))
        correct_pairs += int(expected == observed)
    return {"group": candidate["group"], "index": candidate["index"], "candidate_id": f"{candidate['group']}-{candidate['index']}", "top_actions": top, "exact_optimal_actions": exact_optimal, "top_set_precision": len(top_keys & optimal_keys) / max(1, len(top_keys)), "optimal_hit": bool(top_keys & optimal_keys), "pairwise_ordering_accuracy": correct_pairs / len(informative) if informative else None, "pair_count": len(informative), "scored_actions": scored, "score_time_seconds": score_times, "feature_count": len(FEATURE_NAMES), "coefficient_vector": list(COEFFICIENTS)}


def _mixed_mechanic_smoke() -> dict[str, Any]:
    compiled = _compile("MIXED_MECHANIC", 4)
    checks: dict[str, bool] = {}
    capture_state = _state(compiled, _rows(4, {(0, 0): "K", (3, 3): "k", (1, 1): "P", (1, 2): "p"}))
    runtime = SearchPathRuntime.from_state(capture_state, compiled)
    actions = runtime.legal_actions()
    capture = next((a for a in actions if "semantic_capture_to_hand" in action_to_dict(a).get("pattern_id", "")), None)
    checks["capture_to_hand"] = capture is not None
    if capture is not None:
        with runtime.pushed(capture) as child:
            checks["hand_after_capture"] = child.position.hands[0].count("P") == 1
            capture_key = runtime.current_key
            post_capture = GameState(
                position=replace(child.position, side_to_move=0),
                ply_count=child.ply_count,
                repetition_counts=capture_state.repetition_counts,
                terminal_status=TerminalResult(TerminalStatus.ONGOING),
                history=capture_state.history,
            )
            drop_runtime = SearchPathRuntime.from_state(post_capture, compiled)
            drop = next((a for a in drop_runtime.legal_actions() if action_to_dict(a).get("kind") == "semantic_drop"), None)
            checks["drop_available_after_capture"] = drop is not None
            if drop is not None:
                with drop_runtime.pushed(drop) as dropped:
                    checks["drop_consumes_inventory"] = dropped.position.hands[0].count("P") == 0
            drop_runtime.assert_balanced()
        checks["identity_changes_with_hand"] = capture_key != runtime.current_key
    runtime.assert_balanced()
    remove_state = _state(compiled, _rows(4, {(0, 0): "K", (3, 3): "k", (1, 1): "X", (1, 2): "r"}))
    rr = SearchPathRuntime.from_state(remove_state, compiled)
    remove = next((a for a in rr.legal_actions() if "semantic_remove_from_game" in action_to_dict(a).get("pattern_id", "")), None)
    checks["remove_from_game_action"] = remove is not None
    if remove is not None:
        with rr.pushed(remove) as child:
            checks["remove_does_not_add_hand"] = child.position.hands[0].total() == 0
    rr.assert_balanced()
    promotion_state = _state(compiled, _rows(4, {(0, 0): "K", (3, 3): "k", (1, 2): "X"}))
    pr = SearchPathRuntime.from_state(promotion_state, compiled)
    promotion = next((a for a in pr.legal_actions() if action_to_dict(a).get("promotion_target_id") == "XG"), None)
    checks["promotion_selected"] = promotion is not None
    if promotion is not None:
        with pr.pushed(promotion) as child:
            checks["promotion_changes_type"] = any(piece is not None and piece.current_type_id == "XG" for piece in child.position.board)
    pr.assert_balanced()
    path_state = _state(compiled, _rows(4, {(0, 0): "K", (3, 3): "k", (0, 1): "Z", (0, 2): "P", (0, 3): "r"}))
    zr = SearchPathRuntime.from_state(path_state, compiled)
    path_action = next((a for a in zr.legal_actions() if "semantic_path_restricted" in action_to_dict(a).get("pattern_id", "")), None)
    checks["path_restricted_special_action"] = path_action is not None
    checks["special_piece_non_promotable"] = not any(action_to_dict(a).get("promotion_target_id") for a in zr.legal_actions() if action_to_dict(a).get("actor_type_id") == "Z")
    zr.assert_balanced()
    aux_position = replace(capture_state.position, aux_state=(((0, -1), 1),))
    checks["identity_changes_with_aux"] = aux_position != capture_state.position
    checks["terminal_machinery_accepts_mixed"] = SearchPathRuntime.from_state(capture_state, compiled).terminal_status.status is TerminalStatus.ONGOING
    return {"ruleset_fingerprint": compiled.ruleset_fingerprint, "checks": checks, "passes": all(checks.values())}


def _rename_invariance() -> dict[str, Any]:
    n = 3
    types = (_king("A"), _ray("B"), _pawn("C", "D"), PieceType("D", "D", (RayAtom((1, 0)), RayAtom((-1, 0)))))
    rules = RuleSet(board_size=n, piece_types=types, initial_position=_empty_initial(n, "A"), drop_allowed=_drop_masks(n, ("B", "C", "D")), promotion_allowed={"C": (frozenset(), frozenset())}, promotion_forced={"C": (frozenset(), frozenset())}, max_ply=11, repetition_limit=2, semantic_actions=(_capture_action("semantic_remove_from_game", "C", "remove_from_game"),))
    renamed = compile_semantic_ruleset(rules)
    state = _state(renamed, ["..a", "...", "..B"])
    original = _compile("WESTERN_CHESS_LIKE", n)
    original_state = _state(original, ["..k", "...", "..R"])
    a, b = AnalyticEvaluator(original), AnalyticEvaluator(renamed)
    return {"feature_vectors_equal": a.feature_vector(original_state, 0) == b.feature_vector(state, 0), "scores_equal": abs(a.score(original_state, 0) - b.score(state, 0)) <= 1e-12}


def _complexity_audit() -> dict[str, Any]:
    source = inspect.getsource(AnalyticEvaluator).lower()
    forbidden = ["alpha" + "sho", "alpha" + "chess", "grid" + " search", "td" + " update"]
    feature_methods = [getattr(AnalyticEvaluator, name) for name in FEATURE_NAMES]
    return {"feature_count": len(feature_methods), "fixed_coefficients": list(COEFFICIENTS), "forbidden_decision_strings": [word for word in forbidden if word in source], "coefficient_fitting": False, "piece_name_logic": False, "game_specific_branches": False}


def run(plan: dict[str, Any]) -> dict[str, Any]:
    records = _admit(plan)
    admitted = [row for row in records if row["admitted"]]
    ranked = [_rank_record(row) for row in admitted]
    by_group = {}
    for group in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC"):
        subset = [row for row in ranked if row["group"] == group]
        pairs = [row for row in subset if row["pairwise_ordering_accuracy"] is not None]
        by_group[group] = {"planned": 8, "admitted": len(subset), "mean_top_set_precision": sum(row["top_set_precision"] for row in subset) / len(subset) if subset else 0.0, "optimal_hit": sum(row["optimal_hit"] for row in subset) / len(subset) if subset else 0.0, "pairwise_ordering_accuracy": sum(row["pairwise_ordering_accuracy"] for row in pairs) / len(pairs) if pairs else None}
    all_pairs = [row for row in ranked if row["pairwise_ordering_accuracy"] is not None]
    overall = {"admitted": len(ranked), "mean_top_set_precision": sum(row["top_set_precision"] for row in ranked) / len(ranked) if ranked else 0.0, "optimal_hit": sum(row["optimal_hit"] for row in ranked) / len(ranked) if ranked else 0.0, "pairwise_ordering_accuracy": sum(row["pairwise_ordering_accuracy"] for row in all_pairs) / len(all_pairs) if all_pairs else None}
    gates = {"coverage": all(by_group[group]["admitted"] >= 6 for group in by_group), "overall_top_precision": overall["mean_top_set_precision"] >= .70, "group_top_precision": all(by_group[group]["mean_top_set_precision"] >= .60 and by_group[group]["mean_top_set_precision"] >= .50 for group in by_group), "overall_optimal_hit": overall["optimal_hit"] >= .75, "group_optimal_hit": all(by_group[group]["optimal_hit"] >= .60 for group in by_group), "overall_pairwise": (overall["pairwise_ordering_accuracy"] or 0.0) >= .70, "group_pairwise": all((by_group[group]["pairwise_ordering_accuracy"] or 0.0) >= .60 for group in by_group), "type_name_invariance": all(_rename_invariance().values()), "mixed_mechanic_semantics": _mixed_mechanic_smoke()["passes"], "complexity": _complexity_audit()["feature_count"] == 5 and _complexity_audit()["fixed_coefficients"] == [1, 1, 1, 1, 1] and not _complexity_audit()["forbidden_decision_strings"]}
    passed = all(gates.values())
    selected = "F23W_MINIMAL_ANALYTIC_EVALUATOR_SEARCH_SHADOW" if passed else "F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2"
    score_times = [value for row in ranked for value in row["score_time_seconds"]]
    cost = {"measured": bool(score_times), "score_time_seconds_median": statistics.median(score_times) if score_times else None, "score_time_seconds_p95": (statistics.quantiles(score_times, n=20, method="inclusive")[18] if len(score_times) >= 2 else (score_times[0] if score_times else None)), "reference_nodes": REFERENCE_NODES, "reference_wall_seconds": REFERENCE_WALL_SECONDS}
    direction = {"status": "CONTRACT_ONLY", "root_perspective": "side_to_move", "positive_value": "advantage for the root actor", "feature_sign_contract": {name: "positive means root-actor advantage; negative means opponent advantage" for name in FEATURE_NAMES}, "coefficient_tuning": False}
    usable = {group: [row["candidate_id"] for row in ranked if row["group"] == group] for group in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC")}
    v1_baseline = {"available": False, "reason": "no technically compatible evaluator-v1 scorer was invoked in this audit"}
    return {"schema_version": 1, "plan_sha256": plan["plan_sha256"], "records": records, "admitted_records": ranked, "coverage": {"overall": overall, "by_group": by_group}, "usable_exact_roots_by_group": usable, "gates": gates, "passed": passed, "mixed_mechanic_audit": _mixed_mechanic_smoke(), "type_name_invariance": _rename_invariance(), "complexity_audit": _complexity_audit(), "feature_definitions": {name: "bounded signed root-side advantage derived from RuleSet/profile/legal semantics" for name in FEATURE_NAMES}, "coefficient_vector": list(COEFFICIENTS), "direction_diagnostics": direction, "cost": cost, "evaluator_v1_baseline": v1_baseline, "selected_boundary": selected, "production_changed": False, "historical_v12_rewritten": False}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--plan", type=Path, default=PLAN); parser.add_argument("--output", type=Path, default=OUTPUT); parser.add_argument("--plan-only", action="store_true"); args = parser.parse_args()
    if args.plan_only:
        plan = make_plan(); args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(plan["plan_sha256"]); return
    plan = json.loads(args.plan.read_text(encoding="utf-8")); result = run(plan); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS" if result["passed"] else "FAIL", "plan_sha256": result["plan_sha256"], "admitted": result["coverage"]["overall"]["admitted"], "selected": result["selected_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
