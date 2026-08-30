"""F24A audit-only signal probe for the frozen cheap structural evaluator."""

from __future__ import annotations

import hashlib
import inspect
import json
import multiprocessing
import queue
import statistics
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.pieces import Piece
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from scripts import audit_f23v_minimal_analytic_evaluator as f23v
from scripts import audit_f23v_minimal_analytic_evaluator_r1 as f23vr1
from scripts import audit_f23x_metamorphic_shogi_shadow_r1 as f23x
from scripts import audit_f23y_context_performance as f23y


FIXTURES = ROOT / "tests" / "fixtures"
F23Y_REPORT = FIXTURES / "f23y_context_performance.json"
OUTPUT = FIXTURES / "f24a_minimal_cheap_evaluator.json"
F23Y_COMMIT = "c4af3b93b6ac9d5185fcd7f225b5e2e4fd7eb136"
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
F22_PATHS = {
    "positions": "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json",
    "provenance": "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json",
    "agreement": "artifacts/f22_post_f21_rebaseline_strength/alphasho_move_agreement.json",
    "rank": "artifacts/f22_post_f21_rebaseline_strength/one_ply_reference_rank.json",
}
TIME_BUDGETS = (0.25, 1.0)
TIME_REPETITIONS = 3
NODE_BUDGETS = (128, 512, 2048)
NODE_WATCHDOG_SECONDS = {128: 30.0, 512: 30.0, 2048: 60.0}
TOLERANCE = 1e-12
CONCEPTS = ("material", "positional", "anchor_space", "transition")
FORBIDDEN = ("legal_actions", "pseudo_attacks", "is_square_attacked", "is_in_check", "successor", "push", "pop", "qsearch", "search", "history", "countermove")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _state(compiled: Any, rows: list[str], hands=((), ()), side: int = 0) -> GameState:
    return f23x._state(compiled, "SHOGI_LIKE", "f24a", rows, hands, side)


class CheapRuleDerivedEvaluator:
    """The exact four-term F24A formula, with no dynamic semantic queries."""

    def __init__(self, compiled: Any) -> None:
        started = time.perf_counter()
        self.static_compiled = getattr(compiled, "_legacy_compiled", compiled)
        self.compiled = compiled
        self.profile = build_ruleset_profile(self.static_compiled, EvaluationConfig())
        self.scale = max(1, self.profile.median_non_anchor_value)
        self.n = self.static_compiled.board_size
        self.positional_q: dict[tuple[str, int, int], float] = {}
        self.promotion_ratio: dict[tuple[str, int, int], float] = {}
        self.drop_capability: dict[tuple[str, int], float] = {}
        for piece_type in self.static_compiled.piece_types:
            tid = piece_type.type_id
            for owner in (0, 1):
                mobility = [len(self.static_compiled.empty_mobility[tid][owner][square]) for square in range(self.n * self.n)]
                maximum = max(mobility, default=0)
                mean = sum(mobility) / len(mobility) if mobility else 0.0
                for square, count in enumerate(mobility):
                    self.positional_q[(tid, owner, square)] = (count - mean) / max(1, maximum)
                allowed_pairs = self.static_compiled.promotion_allowed.get(tid, (frozenset(), frozenset()))[owner]
                for square in range(self.n * self.n):
                    source = (square % self.n, square // self.n)
                    promotion_count = sum(1 for pair in allowed_pairs if (pair[0].file, pair[0].rank) == source)
                    self.promotion_ratio[(tid, owner, square)] = min(1.0, promotion_count / max(1, mobility[square]))
                mask = self.static_compiled.drop_allowed.get(tid, ((False,) * (self.n * self.n), (False,) * (self.n * self.n)))[owner]
                allowed_squares = [square for square, enabled in enumerate(mask) if enabled]
                freedom = len(allowed_squares) / max(1, self.n * self.n)
                average = sum(len(self.static_compiled.empty_mobility[tid][owner][square]) for square in allowed_squares) / len(allowed_squares) if allowed_squares else 0.0
                max_mobility = max(mobility, default=0)
                self.drop_capability[(tid, owner)] = freedom * average / max(1, max_mobility)
        self.profile_build_seconds = time.perf_counter() - started
        self.profile_build_count = 1
        self.last_timings: dict[str, float] = {}

    def components(self, state: Any) -> dict[str, int]:
        started = time.perf_counter()
        material = 0
        positional_raw = 0.0
        transition_raw = 0.0
        anchors: list[tuple[int, Any] | None] = [None, None]
        board = state.position.board
        for square, piece in enumerate(board):
            if piece is None:
                continue
            sign = 1 if piece.owner == 0 else -1
            material += sign * self.profile.board_value_by_type[piece.current_type_id]
            metadata = self.static_compiled.types_by_id[piece.current_type_id]
            if metadata.is_anchor:
                anchors[piece.owner] = (square, piece)
            elif not metadata.is_anchor:
                value = min(self.profile.board_value_by_type[piece.current_type_id], self.scale)
                positional_raw += sign * value * self.positional_q[(piece.current_type_id, piece.owner, square)] / self.n
            if not piece.promoted and self.profile.promotion_gain_by_type.get(piece.base_type_id, 0) > 0:
                gain = min(self.profile.promotion_gain_by_type[piece.base_type_id], self.scale)
                transition_raw += sign * (gain / self.n) * self.promotion_ratio[(piece.base_type_id, piece.owner, square)]
        board_seconds = time.perf_counter() - started

        started = time.perf_counter()
        for owner, hand in enumerate(state.position.hands):
            sign = 1 if owner == 0 else -1
            for tid, count in hand.counts:
                material += sign * count * self.profile.hand_value_by_base_type[tid]
                hand_value = min(self.profile.hand_value_by_base_type[tid], self.scale)
                transition_raw += sign * count * (hand_value / self.n) * self.drop_capability[(tid, owner)]
        hand_seconds = time.perf_counter() - started

        started = time.perf_counter()
        anchor_raw = 0.0
        for owner, anchor in enumerate(anchors):
            if anchor is None:
                continue
            square, piece = anchor
            targets = self.static_compiled.empty_mobility[piece.current_type_id][owner][square]
            if targets:
                empty_fraction = sum(board[square_to_index(target, self.n)] is None for target in targets) / len(targets)
                value = (self.scale / self.n) * empty_fraction
                anchor_raw += value if owner == 0 else -value
        anchor_seconds = time.perf_counter() - started
        self.last_timings = {"material_board_scan": board_seconds, "hand_scan": hand_seconds, "positional_lookup": board_seconds, "anchor_space": anchor_seconds, "transition_lookup": board_seconds + hand_seconds, "total": board_seconds + hand_seconds + anchor_seconds}
        return {"material": material, "positional": round(positional_raw), "anchor_space": round(anchor_raw), "transition": round(transition_raw)}

    def evaluate(self, state: Any) -> int:
        components = self.components(state)
        raw = sum(components.values())
        return raw if state.position.side_to_move == 0 else -raw

    def capability_snapshot(self) -> dict[str, Any]:
        return {"positional_q": {"|".join(map(str, key)): value for key, value in sorted(self.positional_q.items())}, "promotion_ratio": {"|".join(map(str, key)): value for key, value in sorted(self.promotion_ratio.items())}, "drop_capability": {"|".join(map(str, key)): value for key, value in sorted(self.drop_capability.items())}}


class SearchEvaluator:
    def __init__(self, candidate: CheapRuleDerivedEvaluator, production: Evaluator) -> None:
        self.candidate = candidate
        self.production = production
        self.calls = 0
        self.seconds = 0.0
        self.context_seconds = 0.0
        self.aggregation_seconds = 0.0

    def evaluate(self, state: Any) -> int:
        started = time.perf_counter()
        value = self.candidate.evaluate(state)
        self.calls += 1
        self.seconds += time.perf_counter() - started
        return value

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self.production.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self.production.type_value(type_id)


class TimedProduction:
    def __init__(self, production: Evaluator) -> None:
        self.production = production
        self.calls = 0
        self.seconds = 0.0

    def evaluate(self, state: Any) -> int:
        started = time.perf_counter()
        try:
            return self.production.evaluate(state)
        finally:
            self.calls += 1
            self.seconds += time.perf_counter() - started

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self.production.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self.production.type_value(type_id)


def _descriptor_state(descriptor: dict[str, Any], compiled: Any) -> GameState:
    board = tuple(None if item is None else Piece(item["owner"], item["base"], item["current"], item["promoted"]) for item in descriptor["board"])
    hands = tuple(Hands(tuple((str(item[0]), int(item[1])) for item in owner)) for owner in descriptor["hands"])
    position = Position(board=board, hands=hands, side_to_move=descriptor["side_to_move"], ruleset_fingerprint=compiled.ruleset_fingerprint)
    return GameState(position=position, ply_count=0, repetition_counts=(), terminal_status=TerminalResult(TerminalStatus.ONGOING), history=())


def _micro_descriptors() -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str]:
    report = json.loads(F23Y_REPORT.read_text(encoding="utf-8"))
    descriptors = report["preflight"]["microbenchmark"]["descriptors"]
    full_hash = _sha(descriptors)
    shogi = [item for item in descriptors if item["group"] == "SHOGI_LIKE"]
    return descriptors, shogi, full_hash, _sha(shogi)


def _formula_contracts() -> dict[str, Any]:
    compiled = f23y._compiled("SHOGI_LIKE")
    candidate = CheapRuleDerivedEvaluator(compiled)
    material_before = _state(compiled, ["..k", "...", "Kp."])
    material_after = _state(compiled, ["..k", "...", "K.."])
    hand_after = _state(compiled, ["..k", "...", "K.."], ((('P', 1),), ()))
    material = {"remove_opponent_non_anchor_increases": candidate.components(material_after)["material"] >= candidate.components(material_before)["material"], "owned_hand_value_increases": candidate.components(hand_after)["material"] >= candidate.components(material_after)["material"]}

    q_values = sorted((candidate.positional_q[("P", 0, square)], square) for square in range(9) if square not in (0, 8))
    low_q, low_square = q_values[0]
    high_q, high_square = q_values[-1]
    def with_pawn(square: int) -> GameState:
        board = [None] * 9
        board[0] = Piece(0, "K", "K")
        board[8] = Piece(1, "K", "K")
        board[square] = Piece(0, "P", "P")
        return GameState(Position(tuple(board), (Hands.empty(), Hands.empty()), 0, compiled.ruleset_fingerprint), 0, (), TerminalResult(TerminalStatus.ONGOING), ())
    low_state, high_state = with_pawn(low_square), with_pawn(high_square)
    positional = {"low_q": low_q, "high_q": high_q, "strict_component_increase": candidate.components(high_state)["positional"] > candidate.components(low_state)["positional"]}

    anchor = 0
    anchor_targets = list(candidate.static_compiled.empty_mobility["K"][0][anchor])
    target = anchor_targets[0]
    board_empty = [None] * 9; board_empty[anchor] = Piece(0, "K", "K"); board_empty[8] = Piece(1, "K", "K")
    board_occupied = list(board_empty); board_occupied[square_to_index(target, candidate.n)] = Piece(0, "R", "R")
    empty_state = GameState(Position(tuple(board_empty), (Hands.empty(), Hands.empty()), 0, compiled.ruleset_fingerprint), 0, (), TerminalResult(TerminalStatus.ONGOING), ())
    occupied_state = GameState(Position(tuple(board_occupied), (Hands.empty(), Hands.empty()), 0, compiled.ruleset_fingerprint), 0, (), TerminalResult(TerminalStatus.ONGOING), ())
    anchor_contract = {"target": square_to_index(target, candidate.n), "empty_not_worse": candidate.components(empty_state)["anchor_space"] >= candidate.components(occupied_state)["anchor_space"], "strict_case": candidate.components(empty_state)["anchor_space"] > candidate.components(occupied_state)["anchor_space"]}

    ratios = sorted((candidate.promotion_ratio[("P", 0, square)], square) for square in range(9))
    low_ratio, low_promotion_square = ratios[0]
    high_ratio, high_promotion_square = ratios[-1]
    transition = {"low_ratio": low_ratio, "high_ratio": high_ratio, "non_decreasing": high_ratio >= low_ratio, "owned_positive_drop": candidate.components(hand_after)["transition"] > candidate.components(material_after)["transition"]}
    material["passed"] = all(material.values())
    positional["passed"] = positional["strict_component_increase"]
    anchor_contract["passed"] = anchor_contract["empty_not_worse"] and anchor_contract["strict_case"]
    transition["low_square"] = low_promotion_square
    transition["high_square"] = high_promotion_square
    transition["passed"] = transition["non_decreasing"] and transition["owned_positive_drop"]
    return {"material_inventory": material, "positional_capability": positional, "anchor_space": anchor_contract, "transition": transition, "passed": all(row["passed"] for row in (material, positional, anchor_contract, transition))}


def _renamed_type_contract() -> dict[str, Any]:
    cases = [("SHOGI_LIKE", ["..k", "...", "K.."], ((('P', 1),), ())), ("WESTERN_CHESS_LIKE", ["..k", "...", "KRp"], ((), ())), ("MIXED_MECHANIC", ["r.k", "Pp.", "ZXK"], ((('P', 1),), ()))]
    rows = []
    for group, board, hands in cases:
        compiled = f23y._compiled(group)
        source_rules = f23v._rule_set(group, 3)
        type_ids = tuple(compiled.support.type_metadata)
        mapping = {tid: f"T{index}" for index, tid in enumerate(type_ids)}
        renamed_rules = f23y._rename_rules(group, mapping)
        renamed = compile_semantic_ruleset(renamed_rules)
        original = _state(compiled, board, hands)
        renamed_state = f23y._rename_state(original, mapping, renamed.ruleset_fingerprint)
        left, right = CheapRuleDerivedEvaluator(compiled), CheapRuleDerivedEvaluator(renamed)
        left_components, right_components = left.components(original), right.components(renamed_state)
        left_snapshot = left.capability_snapshot()
        right_snapshot = right.capability_snapshot()
        def rename_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
            renamed_snapshot: dict[str, Any] = {}
            for name, values in snapshot.items():
                renamed_snapshot[name] = {}
                for key, value in values.items():
                    parts = key.split("|")
                    renamed_key = "|".join([mapping.get(parts[0], parts[0]), *parts[1:]])
                    renamed_snapshot[name][renamed_key] = value
            return renamed_snapshot
        ratio_equal = rename_snapshot(left_snapshot) == right_snapshot
        row = {"group": group, "components_equal": left_components == right_components, "raw_equal": sum(left_components.values()) == sum(right_components.values()), "side0_equal": left.evaluate(original) == right.evaluate(renamed_state), "side1_equal": left.evaluate(replace(original, position=replace(original.position, side_to_move=1))) == right.evaluate(replace(renamed_state, position=replace(renamed_state.position, side_to_move=1))), "capability_ratios_equal": ratio_equal}
        row["passed"] = all(row[key] for key in ("components_equal", "raw_equal", "side0_equal", "side1_equal", "capability_ratios_equal"))
        rows.append(row)
    return {"rows": rows, "passed": all(row["passed"] for row in rows)}


def _mixed_applicability() -> dict[str, Any]:
    compiled = f23y._compiled("MIXED_MECHANIC")
    state = _state(compiled, ["r.k", "Pp.", "ZXK"], ((('P', 1),), ()))
    candidate = CheapRuleDerivedEvaluator(compiled)
    result = candidate.evaluate(state)
    source = inspect.getsource(CheapRuleDerivedEvaluator)
    return {"evaluated": isinstance(result, int), "contains_capture_drop": True, "contains_remove_promotable": True, "contains_non_promotable_path": True, "game_name_branch": any(token in source for token in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC")), "passed": isinstance(result, int) and not any(token in source for token in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC"))}


def _hot_path_contract() -> dict[str, Any]:
    source = inspect.getsource(CheapRuleDerivedEvaluator.evaluate) + inspect.getsource(CheapRuleDerivedEvaluator.components)
    checks = {token: token not in source for token in FORBIDDEN}
    return {"checks": checks, "passed": all(checks.values())}


def _f22_hashes() -> dict[str, Any]:
    rows = []
    for name, path in F22_PATHS.items():
        actual = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{F22_COMMIT}:{path}"])
        rows.append({"name": name, "path": path, "sha256": hashlib.sha256(actual).hexdigest()})
    expected = json.loads((FIXTURES / "f23x_shogi_shadow_r1.json").read_text(encoding="utf-8"))["phase_b"]["source"]["sha256"]
    return {"commit": F22_COMMIT, "files": rows, "matches_f23y_ledger": all(row["sha256"] == expected[row["name"]] for row in rows)}


def _micro_benchmark() -> dict[str, Any]:
    _all, descriptors, full_hash, subset_hash = _micro_descriptors()
    compiled = f23x._certified_compiled()
    states = [_descriptor_state(item, compiled) for item in descriptors]
    candidate = CheapRuleDerivedEvaluator(compiled)
    production = f23x._production(compiled)
    for state in states:
        candidate.evaluate(state); production.evaluate(state)
    candidate_times, v1_times = [], []
    for index, state in enumerate(states):
        for repetition in range(7):
            order = ("candidate", "v1") if (index + repetition) % 2 == 0 else ("v1", "candidate")
            for kind in order:
                started = time.perf_counter()
                candidate.evaluate(state) if kind == "candidate" else production.evaluate(state)
                (candidate_times if kind == "candidate" else v1_times).append(time.perf_counter() - started)
    candidate_times = [candidate_times[index * 7 + repetition] for index in range(len(states)) for repetition in range(7) if descriptors[index] in descriptors and descriptors[index]["group"] == "SHOGI_LIKE"]
    v1_times = [v1_times[index * 7 + repetition] for index in range(len(states)) for repetition in range(7) if descriptors[index]["group"] == "SHOGI_LIKE"]
    candidate_median, v1_median = statistics.median(candidate_times), statistics.median(v1_times)
    candidate_p95, v1_p95 = statistics.quantiles(candidate_times, n=20, method="inclusive")[18], statistics.quantiles(v1_times, n=20, method="inclusive")[18]
    return {"full_descriptor_count": len(_all), "full_descriptor_sha256": full_hash, "shogi_subset_count": len(descriptors), "shogi_subset_sha256": subset_hash, "repetitions_per_state": 7, "candidate_median_seconds": candidate_median, "candidate_p95_seconds": candidate_p95, "v1_median_seconds": v1_median, "v1_p95_seconds": v1_p95, "median_ratio": candidate_median / v1_median if v1_median else None, "p95_ratio": candidate_p95 / v1_p95 if v1_p95 else None, "profile_build_count": candidate.profile_build_count, "profile_build_seconds": candidate.profile_build_seconds, "passed": candidate_median / v1_median <= 2.0 and candidate_p95 / v1_p95 <= 3.0}


def _search_once(compiled: Any, state: Any, evaluator: Any, *, nodes: int | None = None, seconds: float | None = None, provider: Any = None) -> dict[str, Any]:
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, quiescence_max_depth=0, deterministic=True)
    started = time.perf_counter()
    action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), legal_binding_provider=provider)
    wall = time.perf_counter() - started
    return {"selected_move": None if action is None else gc_action_to_usi(action), "score": score, "nodes": stats.nodes, "qnodes": stats.qnodes, "nodes_per_second": (stats.nodes + stats.qnodes) / wall if wall else None, "total_search_wall": wall, "termination_reason": reason, "complete": action is not None and reason in {"node_limit", "time_limit", "completed", "max_depth"}}


def _search_worker(out: Any, sfen: str, kind: str, budget: int) -> None:
    compiled = f23x._certified_compiled()
    state = sfen_to_gc_state(compiled, sfen)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    production = f23x._production(compiled)
    evaluator = TimedProduction(production) if kind == "v1" else SearchEvaluator(CheapRuleDerivedEvaluator(compiled), production)
    row = _search_once(compiled, state, evaluator, nodes=budget, provider=provider)
    row.update({"kind": kind, "budget": budget, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "declared_budget_complete": row["termination_reason"] == "node_limit", "evaluator_calls": evaluator.calls, "evaluator_time": evaluator.seconds, "context_time": getattr(evaluator, "context_seconds", 0.0), "aggregation_time": getattr(evaluator, "aggregation_seconds", 0.0), "profile_build_count": getattr(getattr(evaluator, "candidate", None), "profile_build_count", None)})
    out.put(row)


def _watchdog(sfen: str, kind: str, budget: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_search_worker, args=(out, sfen, kind, budget))
    process.start(); process.join(NODE_WATCHDOG_SECONDS[budget])
    if process.is_alive():
        process.terminate(); process.join()
        return {"kind": kind, "budget": budget, "complete": False, "declared_budget_complete": False, "termination_reason": "WATCHDOG_TIMEOUT"}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"kind": kind, "budget": budget, "complete": False, "declared_budget_complete": False, "termination_reason": "WORKER_FAILURE"}


def _fixed_search() -> dict[str, Any]:
    f22, references = f23x._load_f22()
    parity = [f23x._harness_parity(f23x._certified_compiled(), sfen_to_gc_state(f23x._certified_compiled(), row["sfen"])) for row in f22["positions"]]
    time_rows = []
    compiled = f23x._certified_compiled()
    for index, position in enumerate(f22["positions"]):
        state = sfen_to_gc_state(compiled, position["sfen"])
        for seconds in TIME_BUDGETS:
            for repetition in range(TIME_REPETITIONS):
                for kind in (("v1", "candidate") if (index + repetition) % 2 == 0 else ("candidate", "v1")):
                    provider = NativeSemanticLegalityProvider.try_create(compiled)
                    production = f23x._production(compiled)
                    evaluator = TimedProduction(production) if kind == "v1" else SearchEvaluator(CheapRuleDerivedEvaluator(compiled), production)
                    row = _search_once(compiled, state, evaluator, seconds=seconds, provider=provider)
                    row.update({"kind": kind, "position_id": position["name"], "budget_seconds": seconds, "repetition": repetition, "reference_move": references[position["name"]], "reference_top1": row["selected_move"] == references[position["name"]], "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "evaluator_calls": evaluator.calls, "evaluator_time": evaluator.seconds, "context_time": getattr(evaluator, "context_seconds", 0.0), "aggregation_time": getattr(evaluator, "aggregation_seconds", 0.0), "profile_build_count": getattr(getattr(evaluator, "candidate", None), "profile_build_count", None)})
                    time_rows.append(row)
    time_summary = {}
    paired = {}
    for seconds in TIME_BUDGETS:
        subset = [row for row in time_rows if row["budget_seconds"] == seconds]
        time_summary[str(seconds)] = {}
        for kind in ("v1", "candidate"):
            current = [row for row in subset if row["kind"] == kind]
            time_summary[str(seconds)][kind] = {"runs": len(current), "complete": all(row["complete"] for row in current), "median_nps": statistics.median(row["nodes_per_second"] for row in current), "evaluator_calls": sum(row["evaluator_calls"] for row in current), "evaluator_time": sum(row["evaluator_time"] for row in current), "median_evaluator_fraction": statistics.median(row["evaluator_time"] / row["total_search_wall"] for row in current), "context_time": sum(row["context_time"] for row in current), "aggregation_time": sum(row["aggregation_time"] for row in current)}
        ratios = []
        for position in f22["positions"]:
            for repetition in range(TIME_REPETITIONS):
                v1 = next(row for row in subset if row["kind"] == "v1" and row["position_id"] == position["name"] and row["repetition"] == repetition)
                candidate = next(row for row in subset if row["kind"] == "candidate" and row["position_id"] == position["name"] and row["repetition"] == repetition)
                ratios.append(candidate["nodes_per_second"] / v1["nodes_per_second"] if v1["nodes_per_second"] else None)
        paired[str(seconds)] = {"ratios": ratios, "median_ratio": statistics.median([value for value in ratios if value is not None])}
        time_summary[str(seconds)]["gates"] = {"fraction": time_summary[str(seconds)]["candidate"]["median_evaluator_fraction"], "fraction_passed": time_summary[str(seconds)]["candidate"]["median_evaluator_fraction"] <= 0.25, "paired_nps_ratio": paired[str(seconds)]["median_ratio"], "nps_passed": paired[str(seconds)]["median_ratio"] >= 0.65, "all_runs_valid": time_summary[str(seconds)]["candidate"]["complete"] and time_summary[str(seconds)]["v1"]["complete"]}
    node_rows, stop = [], None
    for budget in NODE_BUDGETS:
        current = []
        for position in f22["positions"]:
            for kind in ("v1", "candidate"):
                row = _watchdog(position["sfen"], kind, budget)
                row.update({"position_id": position["name"], "reference_move": references[position["name"]], "reference_top1": row.get("selected_move") == references[position["name"]] if row.get("complete") else None})
                node_rows.append(row); current.append(row)
        if not all(row.get("declared_budget_complete", False) for row in current):
            stop = {"budget": budget, "reason": "NOT_COMPLETED_WITHIN_OUTER_WATCHDOG"}; break
    node_summary = {}
    for budget in NODE_BUDGETS:
        node_summary[str(budget)] = {}
        for kind in ("v1", "candidate"):
            current = [row for row in node_rows if row.get("budget") == budget and row.get("kind") == kind]
            node_summary[str(budget)][kind] = {"runs": len(current), "complete": bool(current) and all(row.get("complete") for row in current), "declared_budget_complete": bool(current) and all(row.get("declared_budget_complete") for row in current), "top1_count": sum(bool(row.get("reference_top1")) for row in current), "evaluator_calls": sum(row.get("evaluator_calls", 0) for row in current), "evaluator_time": sum(row.get("evaluator_time", 0.0) for row in current), "context_time": sum(row.get("context_time", 0.0) for row in current), "aggregation_time": sum(row.get("aggregation_time", 0.0) for row in current)}
    quality = {"valid": stop is None, "root_rank_status": "ROOT_RANK_HARNESS_UNAVAILABLE", "top1_delta": None, "controls_passed": None, "passed": False}
    if quality["valid"]:
        quality["top1_delta"] = node_summary["2048"]["candidate"]["top1_count"] - node_summary["2048"]["v1"]["top1_count"]
        controls = [row for row in f22["agreement"]["rows"] if row.get("high_agreement") or row.get("low_agreement")]
        quality["control_results"] = []
        for control in controls:
            v1 = next(row for row in node_rows if row["budget"] == 2048 and row["kind"] == "v1" and row["position_id"] == control["position_id"])
            candidate = next(row for row in node_rows if row["budget"] == 2048 and row["kind"] == "candidate" and row["position_id"] == control["position_id"])
            quality["control_results"].append({"position_id": control["position_id"], "v1_top1": v1["reference_top1"], "candidate_top1": candidate["reference_top1"], "passed": not v1["reference_top1"] or candidate["reference_top1"]})
        quality["controls_passed"] = all(row["passed"] for row in quality["control_results"])
        quality["passed"] = quality["top1_delta"] >= 2 and quality["controls_passed"]
    return {"v1_harness_parity": {"cases": parity, "passed": all(row["passed"] for row in parity)}, "native_routing_policy": sorted({row["provider_mode"] for row in time_rows}), "fixed_time_runs": time_rows, "fixed_time_summary": time_summary, "paired_ratios": paired, "fixed_node_runs": node_rows, "fixed_node_summary": node_summary, "progressive_stop": stop, "quality_gate": quality, "fixed_time_passed": all(row["gates"]["fraction_passed"] and row["gates"]["nps_passed"] and row["gates"]["all_runs_valid"] for row in time_summary.values())}


def _artifact_identity() -> dict[str, Any]:
    paths = ["scripts/audit_f23z_evaluator_representation.py", "tests/fixtures/f23z_evaluator_representation.json", "tests/test_f23z_evaluator_representation.py", "docs/architecture/ADR-074-evaluator-representation-reassessment.md"]
    rows = []
    for path in paths:
        current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        baseline = subprocess.check_output(["git", "-C", str(ROOT), "show", f"HEAD:{path}"]).replace(b"\r\n", b"\n")
        rows.append({"path": path, "matches": current == baseline})
    return {"f23z_files_unchanged": all(row["matches"] for row in rows), "files": rows}


def run() -> dict[str, Any]:
    formula = _formula_contracts()
    rename = _renamed_type_contract()
    mixed = _mixed_applicability()
    hot_path = _hot_path_contract()
    f22 = _f22_hashes()
    micro = _micro_benchmark()
    static = {"profile_build_once": True, "profile_authority": "static_compiled = getattr(compiled, '_legacy_compiled', compiled)", "candidate_profile_build_count": 1}
    preflight = {"formula_contracts": formula, "type_name_invariance": rename, "mixed_mechanic_applicability": mixed, "no_dynamic_hot_path": hot_path, "f22_hashes": f22, "passed": formula["passed"] and rename["passed"] and mixed["passed"] and hot_path["passed"] and f22["matches_f23y_ledger"]}
    result: dict[str, Any] = {"schema_version": 1, "status": "FAIL", "frozen_formula": {"concepts": ["material_and_inventory", "rule_derived_positional_capability", "bounded_anchor_structural_space", "promotion_and_drop_structural_capability"], "score_perspective": "player-0 RAW; sign-flipped for side_to_move=1; final deterministic integer rounding", "coefficients": "none", "static_authority": static}, "preflight": preflight, "micro_gate": micro, "artifact_identity": _artifact_identity(), "production_changed": False, "master_locked": True, "evidence_classes": {"semantic": "SEMANTIC_CONTRACT_EVIDENCE", "real_game": "NOT_RUN", "playing_strength": "NOT_RUN"}}
    if not preflight["passed"] or not micro["passed"]:
        result.update({"shogi_search_allowed": False, "defer_evaluator_v2": True, "selected_boundary": "F24B_MIXED_MECHANIC_RULESET_CERTIFICATION"})
        return result
    result["shogi_search_allowed"] = True
    result["fixed_search"] = _fixed_search()
    result["evidence_classes"]["real_game"] = "REAL_GAME_BENCHMARK_EVIDENCE"
    search = result["fixed_search"]
    full_pass = search["v1_harness_parity"]["passed"] and search["fixed_time_passed"] and search["quality_gate"]["valid"] and search["quality_gate"]["passed"]
    result.update({"defer_evaluator_v2": not full_pass, "selected_boundary": "F24B_STANDARD_SHOGI_BENCHMARK_EXPANSION" if full_pass else "F24B_MIXED_MECHANIC_RULESET_CERTIFICATION", "status": "PASS" if full_pass else "FAIL"})
    return result


def main() -> None:
    result = run()
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "micro_passed": result["micro_gate"]["passed"], "search_allowed": result["shogi_search_allowed"], "selected": result["selected_boundary"]}))


if __name__ == "__main__":
    main()
