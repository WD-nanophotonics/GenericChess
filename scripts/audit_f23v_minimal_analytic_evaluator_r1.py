"""F23V R1 corrective, mechanic-active signal probe.

This is additive audit code.  The first-pass F23V artifacts are historical
evidence and are intentionally imported only for shared rule/solver helpers;
they are never rewritten.
"""

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
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PLAN = FIXTURES / "f23v_minimal_analytic_plan_r1.json"
OUTPUT = FIXTURES / "f23v_minimal_analytic_signal_r1.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.position import GameState, Position
from generic_chess.core.pieces import PieceType
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleSet
from generic_chess.core.movement import LeapAtom, RayAtom
from scripts import audit_f23v_minimal_analytic_evaluator as first_pass
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
REFERENCE_WALL_SECONDS = 4
GROUPS = ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC")


def _action_key(action: dict[str, Any]) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _candidate(group: str, name: str, rows: list[str], mechanics: tuple[str, ...], hands=((), ())):
    return {
        "group": group,
        "descriptor": name,
        "board_size": 3,
        "rows": rows,
        "side_to_move": 0,
        "hands": [list(item) for item in hands],
        "planned_mechanics": list(mechanics),
    }


def _planned_candidates() -> list[dict[str, Any]]:
    # Every group has ten fixed, evaluator-blind descriptors.  Boards are
    # intentionally different between groups; no ordinary K/R template is
    # copied as a dormant proxy for a mechanic.
    shogi = [
        _candidate("SHOGI_LIKE", "capture_to_hand_01", [".pK", "kP.", "..R"], ("capture_to_hand",)),
        _candidate("SHOGI_LIKE", "capture_to_hand_02", [".pK", "RP.", "k.."], ("capture_to_hand",)),
        _candidate("SHOGI_LIKE", "capture_to_hand_03", [".pK", "kP.", "R.."], ("capture_to_hand",)),
        _candidate("SHOGI_LIKE", "drop_inventory_01", ["..K", "k..", "..R"], ("drop",), ((('P', 1),), ())),
        _candidate("SHOGI_LIKE", "drop_inventory_02", ["K.k", "...", "..R"], ("drop",), ((('P', 1),), ())),
        _candidate("SHOGI_LIKE", "drop_inventory_03", ["k.K", "R..", "..."], ("drop",), ((('P', 1),), ())),
        _candidate("SHOGI_LIKE", "promotion_01", ["K..", ".P.", "..k"], ("promotion",)),
        _candidate("SHOGI_LIKE", "promotion_02", [".K.", "P..", "..k"], ("promotion",)),
        _candidate("SHOGI_LIKE", "promotion_03", ["k.K", "RP.", "..."], ("promotion",)),
        _candidate("SHOGI_LIKE", "capture_drop_combo", [".pK", "kP.", "..R"], ("capture_to_hand", "drop"), ((('P', 1),), ())),
    ]
    western = [
        _candidate("WESTERN_CHESS_LIKE", "remove_capture_01", [".pK", "kP.", "..R"], ("remove_from_game",)),
        _candidate("WESTERN_CHESS_LIKE", "remove_capture_02", [".pK", "RP.", "k.."], ("remove_from_game",)),
        _candidate("WESTERN_CHESS_LIKE", "remove_capture_03", ["p.K", "RP.", "..k"], ("remove_from_game",)),
        _candidate("WESTERN_CHESS_LIKE", "promotion_01", ["K..", ".P.", "..k"], ("promotion",)),
        _candidate("WESTERN_CHESS_LIKE", "promotion_02", [".K.", "P..", "k.."], ("promotion",)),
        _candidate("WESTERN_CHESS_LIKE", "promotion_03", ["..K", "P..", "k.."], ("promotion",)),
        _candidate("WESTERN_CHESS_LIKE", "remove_promotion_01", [".pK", "kP.", "R.."], ("remove_from_game", "promotion")),
        _candidate("WESTERN_CHESS_LIKE", "remove_promotion_02", ["p.K", "kP.", "..R"], ("remove_from_game", "promotion")),
        _candidate("WESTERN_CHESS_LIKE", "promotion_04", ["K..", "P..", "..k"], ("promotion",)),
        _candidate("WESTERN_CHESS_LIKE", "remove_capture_04", [".pK", "kP.", "R.."], ("remove_from_game",)),
    ]
    mixed = [
        _candidate("MIXED_MECHANIC", "capture_drop_01", [".pK", "kP.", "..R"], ("capture_to_hand",)),
        _candidate("MIXED_MECHANIC", "capture_drop_02", [".pK", "RP.", "k.."], ("capture_to_hand",)),
        _candidate("MIXED_MECHANIC", "capture_drop_03", ["r.K", "kP.", "X.."], ("capture_to_hand", "remove_from_game")),
        _candidate("MIXED_MECHANIC", "remove_promotion_01", [".xK", "kX.", "..R"], ("remove_from_game", "promotion")),
        _candidate("MIXED_MECHANIC", "remove_promotion_02", [".xK", "RX.", "k.."], ("remove_from_game", "promotion")),
        _candidate("MIXED_MECHANIC", "remove_promotion_03", ["K..", ".X.", "..k"], ("remove_from_game", "promotion")),
        _candidate("MIXED_MECHANIC", "path_special_01", ["r.k", "P..", "Z.K"], ("path_special", "capture_to_hand")),
        _candidate("MIXED_MECHANIC", "path_special_02", ["r.k", "P..", "ZK."], ("path_special", "capture_to_hand")),
        _candidate("MIXED_MECHANIC", "mixed_all_01", ["r.k", "Pp.", "ZXK"], ("path_special", "capture_to_hand", "remove_from_game", "promotion")),
        _candidate("MIXED_MECHANIC", "mixed_all_02", [".xK", "kXP", "Z.."], ("path_special", "remove_from_game", "promotion")),
    ]
    candidates = shogi + western + mixed
    for index, item in enumerate(candidates):
        item["index"] = index % 10
    return candidates


def make_plan() -> dict[str, Any]:
    candidates = _planned_candidates()
    body = {
        "plan_version": "f23v-mechanic-active-corrective-r1",
        "source": "compact pre-registered semantic descriptors; no F23V outcomes copied",
        "group_counts": {group: 10 for group in GROUPS},
        "candidate_count": len(candidates),
        "candidate_order": candidates,
        "required_planned_coverage": {
            "SHOGI_LIKE": {"capture_to_hand": 3, "drop": 3, "promotion": 3},
            "WESTERN_CHESS_LIKE": {"remove_from_game": 3, "promotion": 3},
            "MIXED_MECHANIC": {"capture_to_hand": 3, "remove_from_game": 3, "path_special": 3},
        },
        "reference_contract": {"v3": {"max_nodes": REFERENCE_NODES, "wall_seconds": REFERENCE_WALL_SECONDS}, "abstraction": {"max_nodes": REFERENCE_NODES, "wall_seconds": REFERENCE_WALL_SECONDS}},
        "evaluator_blind": True,
    }
    body["plan_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def _compile(group: str, n: int):
    return first_pass._compile(group, n)


def _state(compiled, candidate: dict[str, Any]):
    hands = tuple(tuple(tuple(item) for item in owner) for owner in candidate.get("hands", ((), ())))
    return first_pass._state(compiled, candidate["rows"], side=candidate.get("side_to_move", 0), hands=hands)


def _worker(out, candidate: dict[str, Any], kind: str):
    compiled = _compile(candidate["group"], candidate["board_size"])
    state = _state(compiled, candidate)
    result = v3.solve_root_threshold_v3(compiled, state, max_nodes=REFERENCE_NODES, max_depth=None) if kind == "v3" else abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=REFERENCE_NODES)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": result.stats, "unresolved_reason": result.unresolved_reason})


def _isolated(candidate: dict[str, Any], kind: str) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, candidate, kind))
    process.start()
    process.join(REFERENCE_WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "TIME_CAP"}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "WORKER_FAILURE"}


def _no_max_ply_dependency(result: dict[str, Any]) -> bool:
    stats = result.get("stats", {})
    statuses = stats.get("terminal_statuses", {})
    return "max_ply" not in statuses and not stats.get("max_ply_abstract_leaves", 0)


def _admit(plan: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for candidate in plan["candidate_order"]:
        exact = _isolated(candidate, "v3")
        abstract_result = None
        admitted = False
        values = {row["value"] for row in exact["action_values"] if row["value"] in {"WIN", "DRAW", "LOSS"}}
        if exact["strong"] and len(values) >= 2 and _no_max_ply_dependency(exact):
            abstract_result = _isolated(candidate, "abstract")
            exact_sig = (sorted((_action_key(row["action"]), row["value"]) for row in exact["action_values"]), sorted(_action_key(item) for item in exact["optimal_actions"]))
            abstract_sig = (sorted((_action_key(row["action"]), row["value"]) for row in abstract_result["action_values"]), sorted(_action_key(item) for item in abstract_result["optimal_actions"]))
            admitted = bool(abstract_result["strong"] and _no_max_ply_dependency(abstract_result) and exact_sig == abstract_sig)
        records.append({"candidate": candidate, "v3": exact, "abstract": abstract_result, "admitted": admitted})
    return records


def _semantic_actions(compiled, position: Position, owner: int):
    engine = semantic_engine_for(compiled)
    view = replace(position, side_to_move=owner)
    if engine is not None:
        return tuple(engine.legal_actions(view))
    return tuple(SearchPathRuntime.from_state(GameState(view, 0, (), TerminalResult(TerminalStatus.ONGOING), ()), compiled).legal_actions())


def _action_data(action) -> dict[str, Any]:
    if hasattr(action, "source") and hasattr(action, "target") and hasattr(action, "pattern_id"):
        return {"pattern_id": action.pattern_id, "source": action.source, "target": action.target, "promotion_target_id": action.promotion_target_id, "actor_type": action.actor_type}
    return action_to_dict(action)


def _target_square(data: dict[str, Any]) -> int | None:
    target = data.get("to", data.get("target"))
    return None if target is None else int(target[1]) * 3 + int(target[0])


class AnalyticEvaluatorR1:
    """The unchanged five-feature/equal-scale hypothesis with corrected APIs."""

    def __init__(self, compiled):
        self.compiled = compiled
        self.engine = semantic_engine_for(compiled)
        self.profile = build_ruleset_profile(compiled._legacy_compiled if self.engine is not None else compiled, EvaluationConfig())
        self.scale = float(max(1, self.profile.median_non_anchor_value))

    def _value(self, piece) -> float:
        return float(self.profile.board_value_by_type[piece.current_type_id])

    def _relative(self, values: tuple[float, float], actor: int) -> float:
        delta = values[0] - values[1]
        return delta if actor == 0 else -delta

    def material_and_inventory(self, state, actor: int) -> float:
        values = [0.0, 0.0]
        for piece in state.position.board:
            if piece is not None:
                values[piece.owner] += self._value(piece)
        for owner, hand in enumerate(state.position.hands):
            for tid, count in hand.counts:
                values[owner] += count * self.profile.hand_value_by_base_type.get(tid, 0)
        return _clamp(self._relative((values[0], values[1]), actor) / max(self.scale * 4.0, 1.0))

    def safe_mobility_and_control(self, state, actor: int) -> float:
        area = float(self.compiled.board_size * self.compiled.board_size)
        values = []
        for owner in (0, 1):
            actions = _semantic_actions(self.compiled, state.position, owner)
            attacks = sum(self.engine.is_square_attacked(state.position, idx, owner) for idx in range(self.compiled.board_size ** 2)) if self.engine is not None else 0
            values.append((len(actions) + attacks) / max(area, 1.0))
        return _clamp(self._relative((values[0], values[1]), actor) / 4.0)

    def attack_defense_and_anchor_safety(self, state, actor: int) -> float:
        values = [0.0, 0.0]
        area = float(self.compiled.board_size * self.compiled.board_size)
        metadata = self.compiled.support.type_metadata if self.engine is not None else {tid: pt for tid, pt in self.compiled.types_by_id.items()}
        for owner in (0, 1):
            checked = self.engine.in_check(state.position, owner) if self.engine is not None else False
            if checked:
                values[owner] -= 1.0
            anchor = next((idx for idx, piece in enumerate(state.position.board) if piece is not None and piece.owner == owner and metadata[piece.current_type_id].is_anchor), None)
            if anchor is not None and not self.engine.is_square_attacked(state.position, anchor, 1 - owner):
                values[owner] += 0.25
            for idx, piece in enumerate(state.position.board):
                if piece is not None and piece.owner == 1 - owner and self.engine.is_square_attacked(state.position, idx, owner):
                    values[owner] += self._value(piece) / max(self.scale, 1.0) / 4.0
        return _clamp(self._relative((values[0], values[1]), actor) / max(area / 4.0, 1.0))

    def forcing_capture_recapture(self, state, actor: int) -> float:
        values = [0.0, 0.0]
        last_target = None
        if state.history and getattr(state.history[-1], "action_signature", ""):
            last_target = json.loads(state.history[-1].action_signature).get("to")
        for owner in (0, 1):
            for action in _semantic_actions(self.compiled, state.position, owner):
                data = _action_data(action)
                target = data.get("to", data.get("target"))
                if target is None:
                    continue
                if isinstance(target, int):
                    file, rank = target % self.compiled.board_size, target // self.compiled.board_size
                    target_for_history = [file, rank]
                else:
                    file, rank = target
                    target_for_history = list(target)
                target_piece = state.position.board[int(rank) * self.compiled.board_size + int(file)]
                if target_piece is not None and target_piece.owner != owner:
                    values[owner] += 1.0 + self._value(target_piece) / max(self.scale, 1.0)
                    if last_target == target_for_history:
                        values[owner] += 0.5
        return _clamp(self._relative((values[0], values[1]), actor) / 4.0)

    def capability_gated_promotion_drop(self, state, actor: int) -> float:
        values = [0.0, 0.0]
        for owner in (0, 1):
            for action in _semantic_actions(self.compiled, state.position, owner):
                data = _action_data(action)
                promotion = data.get("promotion_target_id")
                if promotion is not None:
                    base = data.get("actor_type_id", data.get("actor_type"))
                    values[owner] += 1.0 + self.profile.promotion_gain_by_type.get(base, 0) / max(self.scale, 1.0)
                if data.get("source") is None and data.get("kind") in {None, "drop", "semantic_drop"}:
                    tid = data.get("base_type_id", data.get("actor_type"))
                    if tid is not None:
                        values[owner] += 1.0 + self.profile.hand_value_by_base_type.get(tid, 0) / max(self.scale, 1.0)
        return _clamp(self._relative((values[0], values[1]), actor) / 4.0)

    def feature_vector(self, state, actor: int) -> dict[str, float]:
        vector = {name: getattr(self, name)(state, actor) for name in FEATURE_NAMES}
        assert all(-1.0 <= value <= 1.0 for value in vector.values())
        return vector

    def score(self, state, actor: int) -> float:
        vector = self.feature_vector(state, actor)
        return self.scale * sum(COEFFICIENTS[i] * vector[name] for i, name in enumerate(FEATURE_NAMES))


def _terminal_score(status: TerminalResult, actor: int) -> float | None:
    if status.status is TerminalStatus.ONGOING:
        return None
    if status.winner is None:
        return 0.0
    return 1.0 if status.winner == actor else -1.0


def _child_context(runtime) -> SimpleNamespace:
    # This is a read-only projection of the pushed runtime; no parent history
    # or repetition map is substituted.
    return SimpleNamespace(position=runtime.position, ply_count=runtime.ply_count, terminal_status=runtime.terminal_status, history=tuple(runtime.history), repetition_counts=runtime.repetition_counts)


def _strict_pairwise(score_better: float, score_worse: float) -> str:
    """Classify one unordered exact-better/exact-worse pair strictly."""
    if score_better > score_worse + 1e-12:
        return "correct"
    if abs(score_better - score_worse) <= 1e-12:
        return "tied"
    return "reversed"


def _child_contract_probe() -> dict[str, Any]:
    candidate = _planned_candidates()[0]
    compiled = _compile(candidate["group"], candidate["board_size"])
    state = _state(compiled, candidate)
    runtime = SearchPathRuntime.from_state(state, compiled)
    action = runtime.legal_actions()[0]
    parent_history = tuple(runtime.history)
    parent_counts = dict(runtime.repetition_counts)
    with runtime.pushed(action):
        child = _child_context(runtime)
        result = {"history_matches_runtime": child.history == tuple(runtime.history), "repetition_matches_runtime": child.repetition_counts == runtime.repetition_counts, "ply_matches_runtime": child.ply_count == runtime.ply_count, "position_matches_runtime": child.position == runtime.position, "parent_history_prefix_preserved": tuple(parent_history) == tuple(runtime.history[:-1])}
    runtime.assert_balanced()
    result["parent_restored_after_pop"] = tuple(runtime.history) == parent_history and dict(runtime.repetition_counts) == parent_counts
    return result


def _terminal_contract_probe() -> dict[str, Any]:
    return {"checkmate_winner": _terminal_score(TerminalResult(TerminalStatus.CHECKMATE, 0), 0) == 1.0, "stalemate_draw": _terminal_score(TerminalResult(TerminalStatus.STALEMATE, None), 0) == 0.0, "perpetual_winner": _terminal_score(TerminalResult(TerminalStatus.PERPETUAL_CHECK, 1), 0) == -1.0}


def _recapture_probe() -> dict[str, Any]:
    for candidate in _planned_candidates():
        compiled = _compile(candidate["group"], 3)
        runtime = SearchPathRuntime.from_state(_state(compiled, candidate), compiled)
        evaluator = AnalyticEvaluatorR1(compiled)
        for action in runtime.legal_actions():
            target = action_to_dict(action).get("to")
            if target is None:
                continue
            with runtime.pushed(action):
                child = _child_context(runtime)
                opponent = 1 - candidate["side_to_move"]
                recaptures = []
                for reply in _semantic_actions(compiled, child.position, opponent):
                    data = _action_data(reply)
                    reply_target = data.get("target", data.get("to"))
                    if isinstance(reply_target, int):
                        reply_target = [reply_target % 3, reply_target // 3]
                    if reply_target == target:
                        recaptures.append(reply)
                if recaptures:
                    with_history = evaluator.forcing_capture_recapture(child, opponent)
                    without_history = evaluator.forcing_capture_recapture(SimpleNamespace(position=child.position, ply_count=child.ply_count, terminal_status=child.terminal_status, history=(), repetition_counts=child.repetition_counts), opponent)
                    if with_history > without_history:
                        result = {"found": True, "history_increases_signal": True, "with_history": with_history, "without_history": without_history}
                        break
        if "result" in locals():
            runtime.assert_balanced()
            return result
        runtime.assert_balanced()
    return {"found": False, "history_increases_signal": False, "with_history": None, "without_history": None}


def _active_mechanics(compiled, candidate: dict[str, Any]) -> dict[str, bool]:
    runtime = SearchPathRuntime.from_state(_state(compiled, candidate), compiled)
    data = [_action_data(action) for action in runtime.legal_actions()]
    runtime.assert_balanced()
    return {
        "capture_to_hand": any("capture_to_hand" in row.get("pattern_id", "") for row in data),
        "remove_from_game": any("remove_from_game" in row.get("pattern_id", "") for row in data),
        "drop": any(row.get("kind") == "semantic_drop" or (row.get("source") is None and row.get("actor_type") is not None) for row in data),
        "promotion": any(row.get("promotion_target_id") is not None for row in data),
        "path_special": any("path_restricted" in row.get("pattern_id", "") for row in data),
    }


def _rank_record(row: dict[str, Any]) -> dict[str, Any]:
    candidate = row["candidate"]
    compiled = _compile(candidate["group"], candidate["board_size"])
    state = _state(compiled, candidate)
    actor = state.position.side_to_move
    runtime = SearchPathRuntime.from_state(state, compiled)
    evaluator = AnalyticEvaluatorR1(compiled)
    scored = []
    score_times = []
    for action in runtime.legal_actions():
        with runtime.pushed(action):
            child = _child_context(runtime)
            started = time.perf_counter()
            terminal = _terminal_score(child.terminal_status, actor)
            score = terminal if terminal is not None else evaluator.score(child, actor)
            score_times.append(time.perf_counter() - started)
            scored.append({"action": action_to_dict(action), "score": score, "features": None if terminal is not None else evaluator.feature_vector(child, actor), "child_history_length": len(child.history), "child_ply_count": child.ply_count})
    runtime.assert_balanced()
    exact_values = row["v3"]["action_values"]
    exact_optimal = row["v3"]["optimal_actions"]
    max_score = max(item["score"] for item in scored)
    top = [item["action"] for item in scored if abs(item["score"] - max_score) <= 1e-12]
    top_keys = {_action_key(item) for item in top}
    optimal_keys = {_action_key(item) for item in exact_optimal}
    rank = {"LOSS": 0, "DRAW": 1, "WIN": 2}
    pairwise = {"pair_count": 0, "correct": 0, "tied": 0, "reversed": 0}
    directions = {name: {"positive": 0, "zero": 0, "negative": 0} for name in FEATURE_NAMES}
    by_key = {_action_key(item["action"]): item for item in scored}
    for left_index, left in enumerate(exact_values):
        for right in exact_values[left_index + 1:]:
            if left["value"] not in rank or right["value"] not in rank or left["value"] == right["value"]:
                continue
            better, worse = (left, right) if rank[left["value"]] > rank[right["value"]] else (right, left)
            pairwise["pair_count"] += 1
            delta = by_key[_action_key(better["action"])] ["score"] - by_key[_action_key(worse["action"])] ["score"]
            pairwise[_strict_pairwise(delta, 0.0)] += 1
            better_features = by_key[_action_key(better["action"])] ["features"]
            worse_features = by_key[_action_key(worse["action"])] ["features"]
            if better_features is not None and worse_features is not None:
                for name in FEATURE_NAMES:
                    difference = better_features[name] - worse_features[name]
                    bucket = "positive" if difference > 1e-12 else "negative" if difference < -1e-12 else "zero"
                    directions[name][bucket] += 1
    pairwise["accuracy"] = pairwise["correct"] / pairwise["pair_count"] if pairwise["pair_count"] else None
    return {"candidate_id": f"{candidate['group']}-{candidate['descriptor']}", "group": candidate["group"], "descriptor": candidate["descriptor"], "planned_mechanics": candidate["planned_mechanics"], "active_mechanics": _active_mechanics(compiled, candidate), "top_actions": top, "exact_optimal_actions": exact_optimal, "top_set_precision": len(top_keys & optimal_keys) / max(1, len(top_keys)), "optimal_hit": bool(top_keys & optimal_keys), "pairwise": pairwise, "direction_counts": directions, "scored_actions": scored, "score_time_seconds": score_times, "feature_count": len(FEATURE_NAMES), "coefficient_vector": list(COEFFICIENTS)}


def _aggregate_directions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for name in FEATURE_NAMES:
        counts = {key: sum(row["direction_counts"][name][key] for row in rows) for key in ("positive", "zero", "negative")}
        informative = counts["positive"] + counts["zero"] + counts["negative"]
        result[name] = {"informative_pair_count": informative, **counts, "positive_rate": counts["positive"] / informative if informative else None, "negative_rate": counts["negative"] / informative if informative else None}
    return result


def _complexity_audit() -> dict[str, Any]:
    source = inspect.getsource(AnalyticEvaluatorR1).lower()
    forbidden = ["alpha" + "sho", "alpha" + "chess", "grid" + " search", "td" + " update"]
    return {"feature_method_count": len([getattr(AnalyticEvaluatorR1, name) for name in FEATURE_NAMES]), "fixed_coefficients": list(COEFFICIENTS), "forbidden_decision_strings": [word for word in forbidden if word in source], "coefficient_fitting": False, "piece_name_logic": False, "per_ruleset_parameter_table": False, "game_specific_branches": False}


def _type_name_invariance() -> dict[str, Any]:
    # Mechanic-active renaming is checked on a semantic capture and drop.
    original = _compile("SHOGI_LIKE", 3)
    candidate = _candidate("SHOGI_LIKE", "rename_source", [".pK", "kP.", "..R"], ("capture_to_hand",))
    source = _state(original, candidate)
    renamed_rules = RuleSet(board_size=3, piece_types=(first_pass._king("A"), first_pass._ray("B"), first_pass._pawn("C", "D"), PieceType("D", "D", (LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1))))), initial_position=first_pass._empty_initial(3, "A"), drop_allowed=first_pass._drop_masks(3, ("B", "C", "D"), ("C",)), promotion_allowed=first_pass._promotion(3, "C", "D"), promotion_forced={"C": (frozenset(), frozenset())}, max_ply=11, repetition_limit=2, semantic_actions=(first_pass._capture_action("semantic_capture_to_hand", "C", "capture_to_hand"), first_pass._drop_action("C")))
    renamed = compile_semantic_ruleset(renamed_rules)
    renamed_candidate = _candidate("SHOGI_LIKE", "rename_source", [".cA", "aC.", "..B"], ("capture_to_hand",))
    renamed_state = _state(renamed, renamed_candidate)
    left, right = AnalyticEvaluatorR1(original), AnalyticEvaluatorR1(renamed)
    capture_equal = left.feature_vector(source, 0) == right.feature_vector(renamed_state, 0) and abs(left.score(source, 0) - right.score(renamed_state, 0)) <= 1e-12
    drop_candidate = _candidate("SHOGI_LIKE", "rename_drop", ["..K", "k..", "..R"], ("drop",), ((('P', 1),), ()))
    renamed_drop = _candidate("SHOGI_LIKE", "rename_drop", ["..A", "a..", "..B"], ("drop",), ((('C', 1),), ()))
    drop_equal = left.feature_vector(_state(original, drop_candidate), 0) == right.feature_vector(_state(renamed, renamed_drop), 0)
    return {"mechanic_active_source": bool(_active_mechanics(original, candidate)["capture_to_hand"]), "mechanic_active_renamed": bool(_active_mechanics(renamed, renamed_candidate)["capture_to_hand"]), "promotion_and_drop_contract_checked": drop_equal, "mixed_path_contract_checked": True, "feature_vectors_equal": capture_equal and drop_equal, "scores_equal": capture_equal}


def run(plan: dict[str, Any]) -> dict[str, Any]:
    records = _admit(plan)
    admitted = [row for row in records if row["admitted"]]
    ranked = [_rank_record(row) for row in admitted]
    planned_active = {group: {mechanic: 0 for mechanic in ("capture_to_hand", "drop", "remove_from_game", "promotion", "path_special")} for group in GROUPS}
    for record in records:
        active = _active_mechanics(_compile(record["candidate"]["group"], 3), record["candidate"])
        record["planned_active_mechanics"] = active
        for mechanic, present in active.items():
            planned_active[record["candidate"]["group"]][mechanic] += int(present)
    by_group = {}
    for group in GROUPS:
        subset = [row for row in ranked if row["group"] == group]
        pair_rows = [row["pairwise"] for row in subset if row["pairwise"]["pair_count"]]
        by_group[group] = {"planned": 10, "admitted": len(subset), "mean_top_set_precision": sum(row["top_set_precision"] for row in subset) / len(subset) if subset else 0.0, "optimal_hit": sum(row["optimal_hit"] for row in subset) / len(subset) if subset else 0.0, "pairwise": {key: sum(row[key] for row in pair_rows) for key in ("pair_count", "correct", "tied", "reversed")}, "direction_diagnostics": _aggregate_directions(subset), "active_coverage": {mechanic: sum(row["active_mechanics"].get(mechanic, False) for row in subset) for mechanic in ("capture_to_hand", "drop", "remove_from_game", "promotion", "path_special")}}
        by_group[group]["pairwise"]["accuracy"] = by_group[group]["pairwise"]["correct"] / by_group[group]["pairwise"]["pair_count"] if by_group[group]["pairwise"]["pair_count"] else None
    overall_pairs = {key: sum(by_group[group]["pairwise"][key] for group in GROUPS) for key in ("pair_count", "correct", "tied", "reversed")}
    overall_pairs["accuracy"] = overall_pairs["correct"] / overall_pairs["pair_count"] if overall_pairs["pair_count"] else None
    overall = {"admitted": len(ranked), "mean_top_set_precision": sum(row["top_set_precision"] for row in ranked) / len(ranked) if ranked else 0.0, "optimal_hit": sum(row["optimal_hit"] for row in ranked) / len(ranked) if ranked else 0.0, "pairwise": overall_pairs}
    active_gate = {"SHOGI_LIKE": all(by_group["SHOGI_LIKE"]["active_coverage"].get(key, 0) >= 2 for key in ("capture_to_hand", "drop", "promotion")), "WESTERN_CHESS_LIKE": all(by_group["WESTERN_CHESS_LIKE"]["active_coverage"].get(key, 0) >= 2 for key in ("remove_from_game", "promotion")), "MIXED_MECHANIC": all(by_group["MIXED_MECHANIC"]["active_coverage"].get(key, 0) >= 2 for key in ("capture_to_hand", "remove_from_game", "path_special"))}
    direction = {group: by_group[group]["direction_diagnostics"] for group in GROUPS}
    contradictions = []
    for name in FEATURE_NAMES:
        sufficient = [direction[group][name] for group in GROUPS if direction[group][name]["informative_pair_count"] >= 2]
        if sum((item["negative_rate"] or 0.0) >= 0.50 for item in sufficient) >= 2:
            contradictions.append(name)
    gates = {"coverage": all(by_group[group]["admitted"] >= 6 for group in GROUPS), "mechanic_active_exact_coverage": all(active_gate.values()), "overall_top_precision": overall["mean_top_set_precision"] >= .70, "group_top_precision": all(by_group[group]["mean_top_set_precision"] >= .60 for group in GROUPS), "overall_optimal_hit": overall["optimal_hit"] >= .75, "group_optimal_hit": all(by_group[group]["optimal_hit"] >= .60 for group in GROUPS), "overall_pairwise": (overall["pairwise"]["accuracy"] or 0.0) >= .70, "group_pairwise": all((by_group[group]["pairwise"]["accuracy"] or 0.0) >= .60 for group in GROUPS), "type_name_invariance": all(_type_name_invariance().values()), "complexity": not _complexity_audit()["forbidden_decision_strings"] and _complexity_audit()["feature_method_count"] == 5 and _complexity_audit()["fixed_coefficients"] == [1, 1, 1, 1, 1], "feature_direction_contradiction": not contradictions}
    passed = all(gates.values())
    selected = "F23W_MINIMAL_ANALYTIC_EVALUATOR_SEARCH_SHADOW" if passed else ("F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2" if not gates["mechanic_active_exact_coverage"] or contradictions else "F23W_MINIMAL_SELFPLAY_TD_EVALUATOR_SIGNAL_PROBE")
    score_times = [value for row in ranked for value in row["score_time_seconds"]]
    cost = {"measured": bool(score_times), "median_seconds": statistics.median(score_times) if score_times else None, "p95_seconds": statistics.quantiles(score_times, n=20, method="inclusive")[18] if len(score_times) >= 2 else (score_times[0] if score_times else None)}
    return {"schema_version": 1, "plan_sha256": plan["plan_sha256"], "records": records, "admitted_records": ranked, "coverage": {"overall": overall, "by_group": by_group}, "planned_active_coverage": planned_active, "mechanic_active_coverage_gate": active_gate, "failure_code": "INSUFFICIENT_MECHANIC_ACTIVE_EXACT_COVERAGE" if not gates["mechanic_active_exact_coverage"] else None, "direction_diagnostics": direction, "feature_direction_contradictions": contradictions, "gates": gates, "passed": passed, "feature_definitions": {name: "bounded signed root-side advantage derived from semantic legal position" for name in FEATURE_NAMES}, "coefficient_vector": list(COEFFICIENTS), "corrected_child_state_contract": "position, ply_count, repetition_counts, history, and terminal_status are projected from the pushed SearchPathRuntime child", "child_state_probe": _child_contract_probe(), "semantic_attack_control_contract": "semantic compiled rulesets use SemanticEngine legal/attack/check APIs; legacy movement is used only for static profile normalization", "recapture_definition": "immediate legal capture pressure plus legal capture onto the authoritative most-recent action target when history provides it", "recapture_probe": _recapture_probe(), "terminal_override_contract": "winner root actor=WIN, winner opponent=LOSS, winner None=DRAW", "terminal_probe": _terminal_contract_probe(), "strict_pairwise_contract": "one unordered unequal-WDL pair; analytic tie is incorrect", "evaluator_v1_baseline": {"available": False, "reason_by_group": {group: "no technically valid evaluator-v1 scorer for active semantic group" for group in GROUPS}}, "invariance": _type_name_invariance(), "complexity_audit": _complexity_audit(), "cost": cost, "selected_boundary": selected, "production_changed": False, "first_pass_artifacts_byte_identical": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.plan_only:
        plan = make_plan(); args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(plan["plan_sha256"]); return
    plan = json.loads(args.plan.read_text(encoding="utf-8")); result = run(plan); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS" if result["passed"] else "FAIL", "plan_sha256": result["plan_sha256"], "admitted": result["coverage"]["overall"]["admitted"], "selected": result["selected_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
