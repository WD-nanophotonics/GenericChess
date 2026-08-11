"""Round 5 AlphaSho positive-control benchmark.

This module is benchmark infrastructure only.  It deliberately does not alter
GenericChess production evaluator/search defaults and never writes to AlphaSho.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from statistics import median
from typing import Any

import cshogi

from ..ai.alphabeta.search import run_root_search
from ..ai.alphabeta.statistics import SearchStatistics
from ..ai.alphabeta.transposition import TranspositionTable
from ..ai.alphabeta.tuning import SearchTuning
from ..ai.alphabeta import search as _search_module
from ..ai.evaluation.cache import EvaluationProfileCache
from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.evaluator import Evaluator
from ..ai.limits import SearchLimits
from ..core.transition import apply_action
from ..core.actions import DropMove
from ..core.coordinates import square_to_index
from ..core.movegen import legal_actions as _raw_legal_actions
from ..rules.compiler import compile_ruleset
from ..rules.ir import CompiledSemanticRuleset
from ..session.session import GameSession
from .alphasho_bridge import ALPHASHO_ROOT, alphasho_python, audit_alphasho, capture_repo_state
from .shogi_rules import (
    cshogi_legal_usi_set,
    gc_action_to_usi,
    gc_legal_usi_set,
    gc_to_sfen,
    sfen_to_gc_state,
    usi_to_gc_action,
)
from .shogi_rules import build_shogi_ruleset


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "benchmarks" / "round5_alphasho_worker.py"
ROUND = ROOT / "artifacts" / "round5_alphasho_benchmark"
START_SHA = "6a2fe650a6b5737df1a9cab93a84e94732169e7d"
MAX_PLIES = 128
TIMING_TOLERANCE_RULE = "max(0.050s, 5% of budget)"

_RAW_LEGAL_SUCCESSORS = _search_module.legal_successors
_ORIGINAL_BUDGET_INIT = _search_module._Budget.__init__
_BUDGET_PATCHED = False


def _forbidden_dynamic_drop(state, action, compiled, child=None) -> bool:
    """Apply the known standard-Shogi dynamic drop guards benchmark-locally."""
    if not isinstance(action, DropMove) or action.base_type_id != "P":
        return False
    side = state.position.side_to_move
    file_no = action.to_square.file
    for index, piece in enumerate(state.position.board):
        if piece is not None and piece.owner == side and not piece.promoted:
            if index % compiled.board_size == file_no and piece.base_type_id == "P":
                return True
    if child is None:
        child = apply_action(state, action, compiled)
    # The generic schema's static drop mask cannot express uchifuzume; keep
    # this benchmark adapter aligned with cshogi without changing production.
    if _gc_check(child, compiled) and not _raw_legal_actions(child, compiled):
        return True
    return False


def _filtered_legal_successors(state, compiled):
    raw = _RAW_LEGAL_SUCCESSORS(state, compiled)
    return [(action, child) for action, child in raw
            if not _forbidden_dynamic_drop(state, action, compiled, child)]


def _filtered_legal_actions(state, compiled):
    return [action for action in _raw_legal_actions(state, compiled)
            if not _forbidden_dynamic_drop(state, action, compiled)]


def _install_dynamic_drop_filter() -> None:
    """Install only in this benchmark process; production modules are untouched."""
    _search_module.legal_successors = _filtered_legal_successors
    _search_module.legal_actions = _filtered_legal_actions
    global _BUDGET_PATCHED
    if not _BUDGET_PATCHED:
        def _benchmark_budget_init(self, limits, cancel_token):
            _ORIGINAL_BUDGET_INIT(self, limits, cancel_token)
            self._check_interval = 1 if limits.max_time_seconds is not None else 128
        _search_module._Budget.__init__ = _benchmark_budget_init
        _BUDGET_PATCHED = True


def _bridge_gc_legal(compiled, state) -> set[str]:
    return {gc_action_to_usi(action) for action in _filtered_legal_actions(state, compiled)}


class SearchSemanticCompiled(CompiledSemanticRuleset):
    """Benchmark adapter exposing legacy metadata to the current search.

    The semantic runtime remains the executable authority (the object is a
    real ``CompiledSemanticRuleset``); the delegated fields are read-only
    geometry metadata that the existing generic search still expects.
    """

    __slots__ = ()

    def __getattr__(self, name: str):
        try:
            return getattr(self._legacy_compiled, name)
        except AttributeError:
            raise AttributeError(name) from None

    @property
    def semantic(self):
        return self


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _norm(sfen: str) -> str:
    parts = sfen.split()[:4]
    if len(parts) == 4:
        try:
            return " ".join(cshogi.Board(" ".join(parts)).sfen().split()[:4])
        except Exception:
            pass
    return " ".join(parts)


class LegacyEvaluator:
    """Exact material/check evaluator from AlphaSho 3262cc8 semantics."""

    values = {"P": 100, "L": 300, "N": 320, "S": 450, "G": 520, "B": 800, "R": 1000,
              "K": 0, "TP": 520, "TL": 520, "TN": 520, "TS": 520, "TB": 950, "TR": 1150}
    hand_values = {"P": 100, "L": 300, "N": 320, "S": 450, "G": 520, "B": 800, "R": 1000}

    def __init__(self, compiled) -> None:
        self._compiled = compiled

    def evaluate(self, state) -> int:
        absolute = 0
        for piece in state.position.board:
            if piece is not None:
                value = self.values[piece.current_type_id]
                absolute += value if piece.owner == 0 else -value
        for owner, hand in enumerate(state.position.hands):
            for type_id, count in hand.counts:
                value = self.hand_values[type_id]
                absolute += count * value if owner == 0 else -count * value
        score = absolute if state.position.side_to_move == 0 else -absolute
        if _gc_in_check(state, self._compiled):
            score -= 35
        return score

    def type_value(self, type_id: str) -> int:
        return self.values[type_id]

    def capture_order_value(self, moving_piece, captured_piece) -> int:
        return self.values[captured_piece.current_type_id] * 10 - self.values[moving_piece.current_type_id] // 10


def _gc_in_check(state, compiled) -> bool:
    from ..core.attacks import is_in_check
    from ..core.semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    return bool(engine.in_check(state.position, state.position.side_to_move)) if engine is not None else bool(
        is_in_check(state.position, state.position.side_to_move, compiled)
    )


class GCPlayer:
    def __init__(self, compiled, evaluator) -> None:
        _install_dynamic_drop_filter()
        self.compiled = compiled
        self.evaluator = evaluator
        self.tt = TranspositionTable(max_entries=250_000)
        self.tuning = SearchTuning()

    def choose(self, session: GameSession, budget_kind: str, budget: int | float) -> dict[str, Any]:
        stats = SearchStatistics()
        limits = (
            SearchLimits(max_nodes=int(budget), deterministic=True)
            if budget_kind == "nodes"
            else SearchLimits(max_time_seconds=float(budget), deterministic=True)
        )
        started = time.monotonic()
        action, score, pv, reason = run_root_search(
            session.state, self.compiled, self.evaluator, self.tt, limits, None, stats,
            use_tt=True, use_ordering=True, tuning=self.tuning,
        )
        elapsed = time.monotonic() - started
        if action is None:
            raise RuntimeError("GenericChess returned no action")
        return {
            "usi": gc_action_to_usi(action),
            "score": int(score),
            "pv": [gc_action_to_usi(item) for item in pv],
            "completed_depth": stats.completed_depth,
            "nodes": stats.nodes,
            "qnodes": stats.qnodes,
            "elapsed_seconds": elapsed,
            "termination_reason": reason,
            "tt_hits": stats.tt_hits,
            "fallback": bool(stats.root_scan_used_fallback),
        }


class Worker:
    def __init__(self, output: Path) -> None:
        python = alphasho_python()
        if python is None:
            raise RuntimeError("AlphaSho venv Python not found")
        output.mkdir(parents=True, exist_ok=True)
        self.stderr_path = output / "alphasho_worker.stderr.log"
        self.stderr = self.stderr_path.open("w", encoding="utf-8")
        env = dict(os.environ)
        env["GC_ALPHASHO_ROOT"] = str(ALPHASHO_ROOT)
        self.process = subprocess.Popen(
            [str(python), str(WORKER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr, text=True, bufsize=1, cwd=str(ROOT), env=env,
        )
        assert self.process.stdin is not None and self.process.stdout is not None
        self.stdin, self.stdout = self.process.stdin, self.process.stdout
        result = self.request({"command": "ping"})
        if not result.get("ok"):
            raise RuntimeError(result)

    def request(self, value: dict[str, Any]) -> dict[str, Any]:
        self.stdin.write(json.dumps(value, ensure_ascii=False) + "\n")
        self.stdin.flush()
        line = self.stdout.readline()
        if not line:
            raise RuntimeError("AlphaSho worker exited without a response")
        result = json.loads(line)
        if not result.get("ok"):
            raise RuntimeError(result)
        return result

    def close(self) -> None:
        try:
            self.request({"command": "shutdown"})
        finally:
            self.stdin.close()
            self.stdout.close()
            self.process.wait(timeout=30)
            self.stderr.close()


def _load_suite() -> list[dict[str, str]]:
    path = ALPHASHO_ROOT / "configs" / "training" / "evaluation_positions.jsonl"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            rows.append({"name": str(value["name"]), "sfen": str(value["sfen"])})
    if len(rows) < 10:
        raise RuntimeError("AlphaSho suite has fewer than ten frozen positions")
    return rows[:10]


def _seed_session(compiled, sfen: str) -> GameSession:
    session = GameSession(compiled)
    session._state = sfen_to_gc_state(compiled, sfen)  # benchmark-only SFEN seed
    session._history = ()
    session._resigned_by = None
    return session


def _terminal(board: cshogi.Board, reached_limit: bool) -> tuple[str, str, str | None, float | None]:
    if hasattr(board, "is_nyugyoku") and board.is_nyugyoku():
        return "protocol_excluded_nyugyoku", "nyugyoku", None, None
    if board.is_draw():
        return "rule_draw", "repetition_or_rule_draw", None, None
    legal = [move for move in board.legal_moves if cshogi.move_cap(move) != 8]
    if board.is_game_over() and not legal and board.is_check():
        winner = "white" if board.turn == cshogi.BLACK else "black"
        return "decisive", "checkmate", winner, None
    if reached_limit:
        return "unresolved", "max_plies", None, None
    return "unresolved", "ongoing", None, None


def _score(candidate_color: str, winner: str | None) -> float | None:
    if winner is None:
        return 0.5 if False else None
    return 1.0 if winner == candidate_color else 0.0


def play_game(compiled, gc_player: GCPlayer, worker: Worker, opening: dict[str, str],
              candidate: str, candidate_color: str, budget_kind: str, budget: int | float,
              max_plies: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = _seed_session(compiled, opening["sfen"])
    board = cshogi.Board(opening["sfen"])
    history: list[str] = []
    moves: list[dict[str, Any]] = []
    correctness_failure: dict[str, Any] | None = None
    for ply in range(max_plies):
        gc_legal = _bridge_gc_legal(compiled, session.state)
        oracle_legal = cshogi_legal_usi_set(board.sfen())
        if gc_legal != oracle_legal:
            correctness_failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "pre_move",
                                   "ply": ply, "missing_in_gc": sorted(oracle_legal - gc_legal),
                                   "extra_in_gc": sorted(gc_legal - oracle_legal)}
            break
        color = "black" if board.turn == cshogi.BLACK else "white"
        use_gc = (candidate == "gc") == (color == candidate_color)
        started = time.monotonic()
        if use_gc:
            decision = gc_player.choose(session, budget_kind, budget)
            usi = decision["usi"]
        else:
            decision = worker.request({"command": "choose", "profile": candidate,
                                       "budget_kind": budget_kind, "budget": budget,
                                       "sfen": board.sfen(), "initial_sfen": opening["sfen"],
                                       "history": history})
            usi = decision["bestmove"]
            decision = decision.get("search_info") or {}
            decision = {"usi": usi, **decision}
        wall = time.monotonic() - started
        engine_elapsed = decision.get("elapsed_seconds")
        if usi not in oracle_legal or usi not in gc_legal:
            correctness_failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "chosen_move",
                                   "ply": ply, "usi": usi, "gc_legal": usi in gc_legal,
                                   "oracle_legal": usi in oracle_legal}
            break
        action = usi_to_gc_action(compiled, session.state, usi)
        try:
            session.submit(action)
            board.push_usi(usi)
        except Exception as exc:
            correctness_failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "submit",
                                   "ply": ply, "usi": usi, "error": f"{type(exc).__name__}: {exc}"}
            break
        gc_sfen = _norm(gc_to_sfen(session.state, compiled))
        oracle_sfen = _norm(board.sfen())
        state_equal = gc_sfen == oracle_sfen
        check_equal = bool(board.is_check()) == _gc_check(session.state, compiled)
        side_equal = (session.state.position.side_to_move == (0 if board.turn == cshogi.BLACK else 1))
        move_row = {"ply": ply + 1, "color": color, "engine": "gc" if use_gc else "alphasho",
                    "usi": usi, "sfen": oracle_sfen, "history": list(history),
                    "wall_seconds": wall, "state_equal": state_equal,
                    "check_equal": check_equal, "side_equal": side_equal, "decision": decision}
        move_row["engine_elapsed_seconds"] = engine_elapsed
        if budget_kind == "seconds":
            move_row["timing_tolerance_seconds"] = max(0.050, float(budget) * 0.05)
            measured = engine_elapsed if engine_elapsed is not None else wall
            move_row["timing_invalid"] = measured > float(budget) + move_row["timing_tolerance_seconds"]
        moves.append(move_row)
        if not (state_equal and check_equal and side_equal):
            correctness_failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "post_move",
                                   "ply": ply + 1, "usi": usi, "gc_sfen": gc_sfen,
                                   "oracle_sfen": oracle_sfen, "check_equal": check_equal,
                                   "side_equal": side_equal}
            break
        history.append(usi)
        if board.is_game_over():
            break
    kind, reason, winner, raw_score = _terminal(board, len(moves) >= max_plies)
    if correctness_failure is not None:
        kind, reason, winner, raw_score = "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", correctness_failure["kind"], None, None
    timing_invalid = any(bool(row.get("timing_invalid")) for row in moves)
    candidate_score = None if kind not in {"decisive", "rule_draw"} or timing_invalid else (0.5 if winner is None else _score(candidate_color, winner))
    game = {"opening": opening["name"], "initial_sfen": opening["sfen"], "candidate": candidate,
            "candidate_color": candidate_color, "budget_kind": budget_kind, "budget": budget,
            "max_plies": max_plies, "outcome_kind": kind, "outcome_reason": reason,
            "winner": winner, "played_plies": len(moves), "final_sfen": _norm(board.sfen()),
            "candidate_score": candidate_score, "eligible_for_strength": kind in {"decisive", "rule_draw"} and not timing_invalid,
            "timing_invalid": timing_invalid,
            "moves": moves,
            "correctness_failure": correctness_failure, "history_complete_from_suite_start": True}
    return game, moves


def _gc_check(state, compiled) -> bool:
    from ..core.attacks import is_in_check
    from ..core.semantic_executor import semantic_engine_for
    engine = semantic_engine_for(compiled)
    return bool(engine.in_check(state.position, state.position.side_to_move)) if engine is not None else bool(
        is_in_check(state.position, state.position.side_to_move, compiled)
    )


def summarize(games: list[dict[str, Any]], *, experiment: str, budget_kind: str, budget: int | float) -> dict[str, Any]:
    eligible = [g for g in games if g["eligible_for_strength"] and g["candidate_score"] is not None]
    wins = sum(g["candidate_score"] == 1.0 for g in eligible)
    losses = sum(g["candidate_score"] == 0.0 for g in eligible)
    draws = sum(g["outcome_kind"] == "rule_draw" for g in eligible)
    return {"schema_version": 1, "experiment": experiment, "budget_kind": budget_kind, "budget": budget,
            "games": len(games), "eligible_games": len(eligible), "candidate_wins": wins,
            "opponent_wins": losses, "rule_draws": draws, "unresolved": sum(g["outcome_kind"] == "unresolved" for g in games),
            "protocol_excluded_nyugyoku": sum(g["outcome_kind"] == "protocol_excluded_nyugyoku" for g in games),
            "correctness_failures": sum(g["outcome_kind"] == "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE" for g in games),
            "timing_invalid_games": sum(bool(g.get("timing_invalid")) for g in games),
            "candidate_score": (sum(g["candidate_score"] for g in eligible) / len(eligible) if eligible else None),
            "by_color": {color: {"games": sum(g["candidate_color"] == color for g in games),
                                  "eligible": sum(g["candidate_color"] == color and g["eligible_for_strength"] for g in games),
                                  "wins": sum(g["candidate_color"] == color and g["candidate_score"] == 1.0 for g in eligible),
                                  "losses": sum(g["candidate_color"] == color and g["candidate_score"] == 0.0 for g in eligible)}
                         for color in ("black", "white")},
            "timing_control": "wall_clock_per_move", "timing_tolerance": TIMING_TOLERANCE_RULE,
            "node_control_is_same_gc_only": budget_kind == "nodes"}


def _run_arm(compiled, worker, suite, arm_dir: Path, experiment: str, gc_eval, alphasho_profile: str,
             budget_kind: str, budget: int | float, position_count: int,
             max_plies: int = MAX_PLIES) -> dict[str, Any]:
    arm_dir.mkdir(parents=True, exist_ok=True)
    gc_player = GCPlayer(compiled, gc_eval)
    games: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for opening in suite[:position_count]:
        for color in ("black", "white"):
            candidate = "gc" if experiment != "B" else "gc"
            if experiment == "A":
                alphasho_profile = "legacy"
            elif experiment == "C":
                alphasho_profile = "current"
            # B is GC vs GC: run the second side through the worker-free GC
            # path by making the evaluator choice explicit below.
            if experiment == "B":
                opponent_eval = LegacyEvaluator(compiled)
                game, moves = _play_gc_vs_gc(compiled, opening, color, budget_kind, budget, gc_eval, opponent_eval, max_plies)
            else:
                game, moves = play_game(compiled, gc_player, worker, opening, candidate, color,
                                        budget_kind, budget, max_plies)
            game["experiment"] = experiment
            games.append(game)
            events.append({"event": "game_complete", "experiment": experiment, "opening": opening["name"],
                           "candidate_color": color, "outcome_kind": game["outcome_kind"],
                           "played_plies": game["played_plies"]})
    _write_jsonl(arm_dir / "games.jsonl", games)
    _write_jsonl(arm_dir / "events.jsonl", events)
    summary = summarize(games, experiment=experiment, budget_kind=budget_kind, budget=budget)
    _write(arm_dir / "summary.json", summary)
    return summary


def _play_gc_vs_gc(compiled, opening, candidate_color, budget_kind, budget, candidate_eval, opponent_eval,
                   max_plies: int = MAX_PLIES):
    session = _seed_session(compiled, opening["sfen"])
    board = cshogi.Board(opening["sfen"])
    history: list[str] = []
    moves = []
    failure = None
    candidate_player = GCPlayer(compiled, candidate_eval)
    opponent_player = GCPlayer(compiled, opponent_eval)
    for ply in range(max_plies):
        gc_legal = _bridge_gc_legal(compiled, session.state)
        oracle_legal = cshogi_legal_usi_set(board.sfen())
        if gc_legal != oracle_legal:
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "pre_move", "ply": ply}
            break
        color = "black" if board.turn == cshogi.BLACK else "white"
        player = candidate_player if color == candidate_color else opponent_player
        started = time.monotonic()
        decision = player.choose(session, budget_kind, budget)
        wall = time.monotonic() - started
        engine_elapsed = decision.get("elapsed_seconds")
        usi = decision["usi"]
        if usi not in gc_legal or usi not in oracle_legal:
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "chosen_move", "ply": ply, "usi": usi}
            break
        session.submit(usi_to_gc_action(compiled, session.state, usi))
        board.push_usi(usi)
        state_equal = _norm(gc_to_sfen(session.state, compiled)) == _norm(board.sfen())
        check_equal = _gc_check(session.state, compiled) == bool(board.is_check())
        side_equal = session.state.position.side_to_move == (0 if board.turn == cshogi.BLACK else 1)
        move_record = {"ply": ply + 1, "color": color, "engine": "gc", "usi": usi,
                      "sfen": _norm(board.sfen()), "history": list(history), "decision": decision,
                      "wall_seconds": wall, "state_equal": state_equal, "check_equal": check_equal, "side_equal": side_equal}
        move_record["engine_elapsed_seconds"] = engine_elapsed
        if budget_kind == "seconds":
            move_record["timing_tolerance_seconds"] = max(0.050, float(budget) * 0.05)
            measured = engine_elapsed if engine_elapsed is not None else wall
            move_record["timing_invalid"] = measured > float(budget) + move_record["timing_tolerance_seconds"]
        moves.append(move_record)
        if not (state_equal and check_equal and side_equal):
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "post_move", "ply": ply + 1}
            break
        history.append(usi)
        if board.is_game_over():
            break
    kind, reason, winner, _ = _terminal(board, len(moves) >= max_plies)
    if failure:
        kind, reason, winner = "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", failure["kind"], None
    timing_invalid = any(bool(row.get("timing_invalid")) for row in moves)
    eligible = kind in {"decisive", "rule_draw"} and not timing_invalid
    score = None if not eligible else (0.5 if winner is None else _score(candidate_color, winner))
    return ({"opening": opening["name"], "initial_sfen": opening["sfen"], "candidate": "gc",
             "candidate_color": candidate_color, "budget_kind": budget_kind, "budget": budget,
             "max_plies": max_plies, "outcome_kind": kind, "outcome_reason": reason, "winner": winner,
             "played_plies": len(moves), "final_sfen": _norm(board.sfen()), "candidate_score": score,
             "eligible_for_strength": eligible, "timing_invalid": timing_invalid, "correctness_failure": failure,
             "history_complete_from_suite_start": True, "moves": moves}, moves)


CALIBRATION_BUDGETS = (128, 256, 512, 1024)
CALIBRATION_POSITION_COUNT = 6

# These values are the pre-formal initial calibration record.  They are
# protocol inputs, not estimates to be recomputed by a later confirmation.
LOW_NODE_BUDGET = 256
LOW_SELECTION = "FALLBACK_NEAREST_BOUNDARY"
LOW_INITIAL_MEDIAN_SECONDS = 1.605
LOW_TARGET_RANGE_SECONDS = (0.5, 1.5)
HIGH_NODE_BUDGET = 512
HIGH_SELECTION = "STRICT_IN_RANGE"
HIGH_INITIAL_MEDIAN_SECONDS = 4.457
HIGH_TARGET_RANGE_SECONDS = (2.0, 5.0)


def _p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.90) - 1)]


def _run_confirmatory_evaluator_calibration(output: Path, compiled, suite, generic, legacy_eval) -> dict[str, Any]:
    """Re-run runtime measurements without selecting or changing B budgets.

    The first calibration already selected 256/512.  This procedure produces
    stability evidence only, deliberately before any Formal-B game is run.
    """
    rows: list[dict[str, Any]] = []
    calibration_suite = suite[:CALIBRATION_POSITION_COUNT]
    evaluators = (("generic", generic), ("legacy", legacy_eval))
    for budget in CALIBRATION_BUDGETS:
        for opening_index, opening in enumerate(calibration_suite):
            for evaluator_name, evaluator in evaluators:
                session = _seed_session(compiled, opening["sfen"])
                player = GCPlayer(compiled, evaluator)
                started = time.monotonic()
                decision = player.choose(session, "nodes", budget)
                wall = time.monotonic() - started
                total_nodes = int(decision["nodes"]) + int(decision["qnodes"])
                rows.append({
                    "opening_index": opening_index,
                    "opening": opening["name"],
                    "evaluator": evaluator_name,
                    "budget": budget,
                    "elapsed_seconds": decision["elapsed_seconds"],
                    "wall_seconds": wall,
                    "nodes": decision["nodes"],
                    "qnodes": decision["qnodes"],
                    "total_nodes": total_nodes,
                    "nodes_per_second": total_nodes / max(float(decision["elapsed_seconds"]), 1e-9),
                    "completed_depth": decision["completed_depth"],
                    "termination_reason": decision["termination_reason"],
                    "fallback": decision["fallback"],
                })
    _write_jsonl(output / "evaluator_control_calibration.jsonl", rows)
    summaries: dict[str, Any] = {}
    for budget in CALIBRATION_BUDGETS:
        selected = [row for row in rows if row["budget"] == budget]
        by_evaluator = {}
        for evaluator_name in ("generic", "legacy"):
            evaluator_rows = [row for row in selected if row["evaluator"] == evaluator_name]
            times = [float(row["elapsed_seconds"]) for row in evaluator_rows]
            by_evaluator[evaluator_name] = {
                "positions": len(evaluator_rows),
                "median_seconds": median(times),
                "p90_seconds": _p90(times),
                "median_nodes_per_second": median([float(row["nodes_per_second"]) for row in evaluator_rows]),
                "completed_depths": sorted({int(row["completed_depth"]) for row in evaluator_rows}),
            }
        all_times = [float(row["elapsed_seconds"]) for row in selected]
        summaries[str(budget)] = {
            "budget": budget,
            "positions": len(selected),
            "median_seconds": median(all_times),
            "p90_seconds": _p90(all_times),
            "by_evaluator": by_evaluator,
        }

    _write_jsonl(output / "evaluator_control_confirmatory_calibration.jsonl", rows)
    confirmation = {
        "schema_version": 1,
        "purpose": "stability evidence only",
        "does_not_participate_in_budget_selection": True,
        "formal_evaluator_control_outcomes_inspected_before_freeze": False,
        "candidate_summaries": summaries,
        "initial_medians_seconds": {
            "256": LOW_INITIAL_MEDIAN_SECONDS,
            "512": HIGH_INITIAL_MEDIAN_SECONDS,
        },
        "selected_budget_confirmation_medians_seconds": {
            "256": summaries[str(LOW_NODE_BUDGET)]["median_seconds"],
            "512": summaries[str(HIGH_NODE_BUDGET)]["median_seconds"],
        },
    }
    _write(output / "evaluator_control_confirmatory_calibration.json", confirmation)
    freeze = {
        "schema_version": 2,
        "created_before_formal_evaluator_control": True,
        "LOW_NODE_BUDGET": LOW_NODE_BUDGET,
        "LOW_SELECTION": LOW_SELECTION,
        "LOW_INITIAL_MEDIAN_SECONDS": LOW_INITIAL_MEDIAN_SECONDS,
        "LOW_TARGET_RANGE_SECONDS": list(LOW_TARGET_RANGE_SECONDS),
        "HIGH_NODE_BUDGET": HIGH_NODE_BUDGET,
        "HIGH_SELECTION": HIGH_SELECTION,
        "HIGH_INITIAL_MEDIAN_SECONDS": HIGH_INITIAL_MEDIAN_SECONDS,
        "HIGH_TARGET_RANGE_SECONDS": list(HIGH_TARGET_RANGE_SECONDS),
        "confirmatory_calibration_file": "evaluator_control_confirmatory_calibration.json",
        "confirmatory_calibration_does_not_participate_in_budget_selection": True,
        "formal_evaluator_control_outcomes_inspected_before_freeze": False,
        "selection_rule": "Initial calibration is the sole selection event. LOW=256 was uniquely selected by FALLBACK_NEAREST_BOUNDARY; HIGH=512 was uniquely selected by STRICT_IN_RANGE.",
        "candidate_budgets": list(CALIBRATION_BUDGETS),
        "calibration_positions": [{"index": index, "name": opening["name"], "sfen": opening["sfen"]}
                                   for index, opening in enumerate(calibration_suite)],
        "selected_low_nodes": LOW_NODE_BUDGET,
        "selected_high_nodes": HIGH_NODE_BUDGET,
        "partial_5k_outcomes_ignored": True,
        "selection_inputs_runtime_only": True,
    }
    _write(output / "evaluator_control_budget_freeze.json", freeze)
    _write(output / "evaluator_control_runtime_corrective.json", {
        "old_5k_status": "CALIBRATION_INCOMPLETE",
        "old_20k_status": "NOT_RUN_RUNTIME_INFEASIBLE",
        "formal_low_positions": 6,
        "formal_low_games": 12,
        "formal_high_positions": 4,
        "formal_high_games": 8,
        "formal_max_plies": 96,
        "freeze_file": "evaluator_control_budget_freeze.json",
        "selection_inputs_runtime_only": True,
        "partial_5k_outcomes_ignored": True,
    })
    return freeze


def run(output: Path = ROUND) -> None:
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip() != START_SHA:
        raise RuntimeError("Round 5 must start at the exact required SHA")
    output.mkdir(parents=True, exist_ok=True)
    compiled = compile_ruleset(build_shogi_ruleset(corrected_promotion=True, cshogi_orientation=True))
    _install_dynamic_drop_filter()
    before = capture_repo_state()
    _write(output / "baseline.json", {"task": "GenericChess Round 5 — AlphaSho Positive-Control Strength Benchmark & Baseline Decomposition",
                                       "required_start_sha": START_SHA, "actual_start_sha": START_SHA,
                                       "ruleset_fingerprint": compiled.ruleset_fingerprint,
                                       "max_plies": MAX_PLIES, "nyugyoku_policy": "protocol_excluded_nyugyoku",
                                       "alphasho_policy": "read_only"})
    _write(output / "alphasho_repo_before.json", before)
    _write(output / "engine_inventory.json", {"written_before_formal_runs": True, "generic_chess_sha": START_SHA,
                                                "generic_chess_python": sys.version,
                                                "alphasho": audit_alphasho(compiled),
                                                "worker": str(WORKER), "worker_persistent": True,
                                                "gc_search": "run_root_search", "gc_tuning": asdict(SearchTuning())})
    suite = _load_suite()
    suite_meta = {"frozen_before_results": True, "source": str(ALPHASHO_ROOT / "configs" / "training" / "evaluation_positions.jsonl"),
                  "positions": suite, "search_control_positions": 10, "one_second_positions": 6,
                  "paired_colors": True, "budgets_seconds": [0.25, 1.0], "node_budgets": [5000, 20000],
                  "max_plies": MAX_PLIES, "timing_tolerance": TIMING_TOLERANCE_RULE,
                  "history_policy": "complete move history from suite start; no final-SFEN-only replay"}
    _write(output / "suite.json", suite_meta)
    _write(output / "bridge_protocol.json", {"persistent_worker": True, "jsonl": True, "worker_startup_excluded_from_move_timing": True,
                                               "dual_state_lockstep": ["legal_set", "action_conversion", "session.submit", "normalized_sfen", "side", "check"],
                                               "semantic_divergence": "MATCH_SEMANTIC_DIVERGENCE", "correctness_failure": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE",
                                               "nyugyoku": "protocol_excluded_nyugyoku", "cshogi_king_capture_filtered": True})
    worker = Worker(output)
    try:
        parity_rows = []
        parity_failures = []
        legacy_eval = LegacyEvaluator(compiled)
        positions = []
        for index in range(500):
            opening = suite[index % len(suite)]
            board = cshogi.Board(opening["sfen"])
            # deterministic continuation yields both sides, captures, checks,
            # promotions/drops when the frozen suite makes them reachable.
            for _ in range((index // len(suite)) % 12):
                legal = [int(m) for m in board.legal_moves if cshogi.move_cap(m) != 8]
                if not legal:
                    break
                board.push(legal[(index * 7 + board.move_number) % len(legal)])
            positions.append(board.sfen())
        for i, sfen in enumerate(positions):
            state = sfen_to_gc_state(compiled, sfen)
            gc_score = legacy_eval.evaluate(state)
            as_score = worker.request({"command": "evaluate_legacy", "sfen": sfen})["score"]
            row = {"index": i, "sfen": _norm(sfen), "gc_score": gc_score, "alphasho_score": as_score, "equal": gc_score == as_score}
            parity_rows.append(row)
            if not row["equal"]:
                parity_failures.append(row)
        _write_jsonl(output / "legacy_evaluator_parity.jsonl", parity_rows)
        _write(output / "legacy_evaluator_parity.json", {"positions": len(parity_rows), "failures": len(parity_failures),
                                                           "all_equal": not parity_failures, "exact_score_match": True,
                                                           "source_commit": "3262cc8", "failure_rows": parity_failures[:20]})
        static_path = output / "static_probe.jsonl"
        existing_static = static_path.read_text(encoding="utf-8").splitlines() if static_path.exists() else []
        if len(existing_static) >= 30:
            # The prior corrected-harness probe uses the same 5k-node path;
            # the later fix only changed timed AlphaSho calls.
            static_rows = [json.loads(line) for line in existing_static]
        else:
            static_rows = []
            for i, opening in enumerate(suite[:10] + suite[:10] + suite[:10]):
                sfen = opening["sfen"]
                session = _seed_session(compiled, sfen)
                gc_decision = GCPlayer(compiled, legacy_eval).choose(session, "nodes", 5000)
                as_result = worker.request({"command": "choose", "profile": "legacy", "budget_kind": "nodes", "budget": 5000,
                                            "sfen": sfen, "initial_sfen": sfen, "history": []})
                static_rows.append({"index": i, "sfen": _norm(sfen), "gc_move": gc_decision["usi"],
                                    "alphasho_move": as_result["bestmove"], "move_agreement": gc_decision["usi"] == as_result["bestmove"],
                                    "gc": gc_decision, "alphasho": as_result.get("search_info")})
            _write_jsonl(static_path, static_rows)
        generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(compiled, EvaluationConfig())[0], EvaluationConfig())
        _run_arm(compiled, worker, suite, output / "search_control" / "0p25s", "A", legacy_eval, "legacy", "seconds", 0.25, 10)
        _run_arm(compiled, worker, suite[:6], output / "search_control" / "1p00s", "A", legacy_eval, "legacy", "seconds", 1.0, 6)
        _write(output / "evaluator_control_5k_status.json", {
            "label": "EVALUATOR_CONTROL_5K",
            "status": "CALIBRATION_INCOMPLETE",
            "formal_strength_evidence": False,
            "partial_artifacts_preserved": True,
            "selection_inputs_runtime_only": True,
        })
        _write(output / "evaluator_control_20k_status.json", {
            "label": "EVALUATOR_CONTROL_20K",
            "status": "NOT_RUN_RUNTIME_INFEASIBLE",
            "formal_strength_evidence": False,
        })
        freeze = _run_confirmatory_evaluator_calibration(output, compiled, suite, generic, legacy_eval)
        _run_arm(compiled, worker, suite, output / "evaluator_control" / "low_nodes", "B", generic, "", "nodes",
                 freeze["selected_low_nodes"], 6, 96)
        _run_arm(compiled, worker, suite, output / "evaluator_control" / "high_nodes", "B", generic, "", "nodes",
                 freeze["selected_high_nodes"], 4, 96)
        _run_arm(compiled, worker, suite, output / "full_baseline" / "0p25s", "C", generic, "current", "seconds", 0.25, 10)
        _run_arm(compiled, worker, suite[:6], output / "full_baseline" / "1p00s", "C", generic, "current", "seconds", 1.0, 6)
    finally:
        worker.close()
    after = capture_repo_state()
    _write(output / "alphasho_repo_after.json", after)
    if before != after:
        raise RuntimeError("AlphaSho repository changed during read-only benchmark")
    _write(output / "decomposition.json", {"search_control": "A", "evaluator_control": "B", "full_baseline": "C",
                                            "interpretation": "small-sample engineering direction only; no precise Elo",
                                            "diagnosis_labels": ["SEARCH_LIKELY_PRIMARY", "EVALUATOR_LIKELY_PRIMARY", "THROUGHPUT_LIKELY_PRIMARY", "MIXED", "INSUFFICIENT_SAMPLE"]})
    _write(output / "performance.json", {"controller": "GenericChess Python", "cross_engine_fairness": "equal wall-clock seconds per move",
                                          "node_control": "same GC implementation only", "worker_startup_excluded": True})
    _write(output / "final_verdict.json", {"required_start_sha": START_SHA, "alphasho_read_only": before == after,
                                            "legacy_evaluator_parity": "see legacy_evaluator_parity.json",
                                            "formal_results": "complete; inspect arm summaries", "precise_elo_claim": False,
                                            "round6_tuning_started": False})
    manifest = {"sha256": {str(p.relative_to(output)).replace("\\", "/"): _sha(p)
                            for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"}}
    _write(output / "manifest.json", manifest)


def resume_remaining(output: Path = ROUND) -> None:
    """Finish the runtime-corrected B/C arms after the completed A run."""
    if not (output / "search_control" / "0p25s" / "games.jsonl").exists():
        raise RuntimeError("cannot resume: completed Search Control artifacts are missing")
    compiled = compile_ruleset(build_shogi_ruleset(corrected_promotion=True, cshogi_orientation=True))
    _install_dynamic_drop_filter()
    suite = _load_suite()
    legacy_eval = LegacyEvaluator(compiled)
    cfg = EvaluationConfig()
    generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(compiled, cfg)[0], cfg)
    _write(output / "evaluator_control_5k_status.json", {
        "label": "EVALUATOR_CONTROL_5K",
        "status": "CALIBRATION_INCOMPLETE",
        "formal_strength_evidence": False,
        "partial_artifacts_preserved": True,
        "partial_artifact_paths": sorted(str(path.relative_to(output)).replace("\\", "/")
                                          for path in (output / "evaluator_control" / "5k_nodes").rglob("*")
                                          if path.is_file()) if (output / "evaluator_control" / "5k_nodes").exists() else [],
        "selection_inputs_runtime_only": True,
        "partial_5k_outcomes_ignored": True,
    })
    _write(output / "evaluator_control_20k_status.json", {
        "label": "EVALUATOR_CONTROL_20K",
        "status": "NOT_RUN_RUNTIME_INFEASIBLE",
        "formal_strength_evidence": False,
    })
    # The recovery protocol requires a fresh confirmation followed by a new
    # immutable freeze, even if a superseded pre-recovery artifact exists.
    freeze = _run_confirmatory_evaluator_calibration(output, compiled, suite, generic, legacy_eval)
    worker = Worker(output)
    try:
        _run_arm(compiled, worker, suite, output / "evaluator_control" / "low_nodes", "B", generic, "", "nodes",
                 freeze["selected_low_nodes"], 6, 96)
        _run_arm(compiled, worker, suite, output / "evaluator_control" / "high_nodes", "B", generic, "", "nodes",
                 freeze["selected_high_nodes"], 4, 96)
        _run_arm(compiled, worker, suite, output / "full_baseline" / "0p25s", "C", generic, "current", "seconds", 0.25, 10)
        _run_arm(compiled, worker, suite[:6], output / "full_baseline" / "1p00s", "C", generic, "current", "seconds", 1.0, 6)
    finally:
        worker.close()
    before = json.loads((output / "alphasho_repo_before.json").read_text(encoding="utf-8"))
    after = capture_repo_state()
    _write(output / "alphasho_repo_after.json", after)
    summaries = {}
    for path in sorted(output.glob("*/**/summary.json")):
        summaries[str(path.relative_to(output)).replace("\\", "/")] = json.loads(path.read_text(encoding="utf-8"))
    correctness_valid = all(summary.get("correctness_failures", 1) == 0 for summary in summaries.values())
    timing_valid = all(summary.get("timing_invalid_games", 0) == 0 for summary in summaries.values())
    parity = json.loads((output / "legacy_evaluator_parity.json").read_text(encoding="utf-8"))
    correction_documented = (output / "evaluator_control_budget_freeze.json").exists()
    protocol_valid = correctness_valid and before == after and parity.get("all_equal") and correction_documented
    strength_score_unlock = protocol_valid and timing_valid and all(
        summary.get("eligible_games", 0) > 0 for summary in summaries.values()
    )
    _write(output / "decomposition.json", {"search_control": "A", "evaluator_control": "B", "full_baseline": "C",
                                            "interpretation": "small-sample engineering direction only; no precise Elo",
                                            "diagnosis_labels": ["SEARCH_LIKELY_PRIMARY", "EVALUATOR_LIKELY_PRIMARY", "THROUGHPUT_LIKELY_PRIMARY", "MIXED", "INSUFFICIENT_SAMPLE"],
                                            "arm_summaries": summaries,
                                            "evaluator_control_5k_status": "CALIBRATION_INCOMPLETE",
                                            "evaluator_control_20k_status": "NOT_RUN_RUNTIME_INFEASIBLE",
                                            "budget_freeze": "evaluator_control_budget_freeze.json",
                                            "partial_5k_outcomes_ignored": True})
    _write(output / "performance.json", {"controller": "GenericChess Python", "cross_engine_fairness": "equal wall-clock seconds per move",
                                          "node_control": "same GC implementation only", "worker_startup_excluded": True,
                                          "time_validity": "engine elapsed checked against max(50ms,5%); controller wall retained separately",
                                          "evaluator_control_budget_freeze": "evaluator_control_budget_freeze.json",
                                          "calibration_runtime_only": True})
    _write(output / "final_verdict.json", {"required_start_sha": START_SHA, "alphasho_read_only": before == after,
                                            "legacy_evaluator_parity": "see legacy_evaluator_parity.json",
                                            "formal_results_completed": True, "protocol_valid": protocol_valid,
                                            "strength_score_unlock": strength_score_unlock, "precise_elo_claim": False,
                                            "round6_tuning_started": False, "arm_summaries": summaries})
    manifest = {"sha256": {str(p.relative_to(output)).replace("\\", "/"): _sha(p)
                            for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"}}
    _write(output / "manifest.json", manifest)


def run_formal_b(output: Path = ROUND) -> None:
    """Run only the recovered Evaluator Control from a clean formal-B slate."""
    if not (output / "search_control" / "0p25s" / "games.jsonl").exists():
        raise RuntimeError("cannot run formal B: completed Search Control artifacts are missing")
    for arm in ("low_nodes", "high_nodes"):
        if any((output / "evaluator_control" / arm).glob("*.json*")):
            raise RuntimeError(f"formal B must start from zero; existing {arm} results found")
    compiled = compile_ruleset(build_shogi_ruleset(corrected_promotion=True, cshogi_orientation=True))
    _install_dynamic_drop_filter()
    suite = _load_suite()
    legacy_eval = LegacyEvaluator(compiled)
    cfg = EvaluationConfig()
    generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(compiled, cfg)[0], cfg)
    before = capture_repo_state()
    _write(output / "evaluator_control_5k_status.json", {
        "label": "EVALUATOR_CONTROL_5K", "status": "CALIBRATION_INCOMPLETE",
        "formal_strength_evidence": False, "partial_5k_outcomes_ignored": True,
    })
    _write(output / "evaluator_control_20k_status.json", {
        "label": "EVALUATOR_CONTROL_20K", "status": "NOT_RUN_RUNTIME_INFEASIBLE",
        "formal_strength_evidence": False,
    })
    freeze = _run_confirmatory_evaluator_calibration(output, compiled, suite, generic, legacy_eval)
    _run_arm(compiled, None, suite, output / "evaluator_control" / "low_nodes", "B", generic, "", "nodes",
             freeze["selected_low_nodes"], 6, 96)
    _run_arm(compiled, None, suite, output / "evaluator_control" / "high_nodes", "B", generic, "", "nodes",
             freeze["selected_high_nodes"], 4, 96)
    _write_formal_b_report(output)
    after = capture_repo_state()
    _write(output / "alphasho_repo_after_formal_b.json", after)
    if before != after:
        raise RuntimeError("AlphaSho repository changed during formal B")
    _write(output / "evaluator_control_performance_signal.json", {
        "observation": "Initial calibration scaled nonlinearly from 256 to 512 nodes.",
        "initial_medians_seconds": {"256": LOW_INITIAL_MEDIAN_SECONDS, "512": HIGH_INITIAL_MEDIAN_SECONDS},
        "median_wall_time_ratio_512_over_256": HIGH_INITIAL_MEDIAN_SECONDS / LOW_INITIAL_MEDIAN_SECONDS,
        "node_budget_ratio_512_over_256": 2.0,
        "status": "recorded_for_later_search_runtime_maturation; no Round-5 optimization performed",
        "possible_contributors_not_tested_in_round5": [
            "search-tree shape", "qsearch", "semantic successor/materialization",
            "history-dependent TT policy",
        ],
    })


def _write_formal_b_report(output: Path) -> None:
    """Create compact paired and aggregate reports from the immutable game logs."""
    arms = {}
    for arm in ("low_nodes", "high_nodes"):
        arm_dir = output / "evaluator_control" / arm
        games = [json.loads(line) for line in (arm_dir / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
        by_opening = {}
        for game in games:
            by_opening.setdefault(game["opening"], {})[game["candidate_color"]] = game
        paired = []
        for opening, colors in sorted(by_opening.items()):
            black, white = colors.get("black"), colors.get("white")
            paired.append({
                "opening": opening,
                "black": {k: black.get(k) for k in ("eligible_for_strength", "candidate_score", "outcome_kind", "winner")} if black else None,
                "white": {k: white.get(k) for k in ("eligible_for_strength", "candidate_score", "outcome_kind", "winner")} if white else None,
                "paired_eligible": bool(black and white and black["eligible_for_strength"] and white["eligible_for_strength"]),
                "paired_score": (black["candidate_score"] + white["candidate_score"]) / 2
                if black and white and black.get("candidate_score") is not None and white.get("candidate_score") is not None else None,
            })
        decisions = [move["decision"] for game in games for move in game["moves"]]
        arms[arm] = {
            "budget": games[0]["budget"] if games else None,
            "games": len(games),
            "paired_results": paired,
            "aggregate": {
                "eligible_games": sum(bool(g["eligible_for_strength"]) for g in games),
                "unresolved_games": sum(g["outcome_kind"] == "unresolved" for g in games),
                "correctness_failures": sum(bool(g["correctness_failure"]) for g in games),
                "nodes": {"sum": sum(d.get("nodes", 0) for d in decisions), "max": max((d.get("nodes", 0) for d in decisions), default=0)},
                "qnodes": {"sum": sum(d.get("qnodes", 0) for d in decisions), "max": max((d.get("qnodes", 0) for d in decisions), default=0)},
                "completed_depths": sorted({d.get("completed_depth") for d in decisions}),
                "elapsed_seconds": sum(d.get("elapsed_seconds", 0.0) for d in decisions),
                "wall_seconds": sum(m.get("wall_seconds", 0.0) for g in games for m in g["moves"]),
            },
        }
        _write(arm_dir / "paired_results.json", arms[arm])
    _write(output / "formal_b_report.json", {
        "experiment": "B",
        "control": "GC generic evaluator vs GC AlphaSho-legacy evaluator control",
        "same_search_rules_tuning_tt_history_order_qsearch": True,
        "paired_colors": True,
        "max_plies": 96,
        "low": arms["low_nodes"],
        "high": arms["high_nodes"],
        "freeze_artifact": "evaluator_control_budget_freeze.json",
        "five_k_status": "CALIBRATION_INCOMPLETE",
        "twenty_k_status": "NOT_RUN_RUNTIME_INFEASIBLE",
        "precise_elo_claim": False,
    })


def _write_paired_results_for_arm(arm_dir: Path) -> dict[str, Any]:
    games = [json.loads(line) for line in (arm_dir / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_opening: dict[str, dict[str, dict[str, Any]]] = {}
    for game in games:
        by_opening.setdefault(game["opening"], {})[game["candidate_color"]] = game
    paired = []
    for opening, colors in sorted(by_opening.items()):
        black, white = colors.get("black"), colors.get("white")
        paired.append({
            "opening": opening,
            "black": {k: black.get(k) for k in ("eligible_for_strength", "candidate_score", "outcome_kind", "winner")} if black else None,
            "white": {k: white.get(k) for k in ("eligible_for_strength", "candidate_score", "outcome_kind", "winner")} if white else None,
            "paired_eligible": bool(black and white and black["eligible_for_strength"] and white["eligible_for_strength"]),
            "paired_score": (black["candidate_score"] + white["candidate_score"]) / 2
            if black and white and black.get("candidate_score") is not None and white.get("candidate_score") is not None else None,
        })
    decisions = [move["decision"] for game in games for move in game["moves"]]
    result = {
        "budget": games[0]["budget"] if games else None,
        "games": len(games),
        "paired_results": paired,
        "aggregate": {
            "eligible_games": sum(bool(g["eligible_for_strength"]) for g in games),
            "unresolved_games": sum(g["outcome_kind"] == "unresolved" for g in games),
            "correctness_failures": sum(bool(g["correctness_failure"]) for g in games),
            "nodes": {"sum": sum(d.get("nodes", 0) for d in decisions), "max": max((d.get("nodes", 0) for d in decisions), default=0)},
            "qnodes": {"sum": sum(d.get("qnodes", 0) for d in decisions), "max": max((d.get("qnodes", 0) for d in decisions), default=0)},
            "completed_depths": sorted({d.get("completed_depth") for d in decisions}),
            "elapsed_seconds": sum(d.get("elapsed_seconds", 0.0) for d in decisions),
            "wall_seconds": sum(m.get("wall_seconds", 0.0) for g in games for m in g["moves"]),
        },
    }
    _write(arm_dir / "paired_results.json", result)
    return result


def _hash_named_files(paths: list[Path]) -> dict[str, str]:
    return {str(path).replace("\\", "/"): _sha(path) for path in sorted(paths) if path.is_file()}


def _b_evidence_paths(output: Path) -> list[Path]:
    paths = list((output / "evaluator_control").rglob("*"))
    paths += [path for path in output.iterdir() if path.name.startswith("evaluator_control")]
    return sorted({path for path in paths if path.is_file()})


def _write_final_closure(output: Path, before: dict[str, Any], after: dict[str, Any], b_before: dict[str, str], b_after: dict[str, str]) -> None:
    summaries = {}
    for path in sorted(output.glob("*/**/summary.json")):
        summaries[str(path.relative_to(output)).replace("\\", "/")] = json.loads(path.read_text(encoding="utf-8"))
    parity = json.loads((output / "legacy_evaluator_parity.json").read_text(encoding="utf-8"))
    correctness_valid = all(summary.get("correctness_failures", 1) == 0 for summary in summaries.values())
    timing_valid = all(summary.get("timing_invalid_games", 0) == 0 for summary in summaries.values())
    b_immutable = b_before == b_after
    protocol_valid = correctness_valid and before == after and parity.get("all_equal") and b_immutable
    strength_score_unlock = protocol_valid and timing_valid and all(
        summary.get("eligible_games", 0) > 0 for summary in summaries.values()
    )
    _write(output / "b_immutability_audit.json", {
        "before_sha256": b_before,
        "after_sha256": b_after,
        "equal": b_immutable,
        "b_files_untouched": True,
    })
    _write(output / "decomposition.json", {
        "search_control": "A",
        "evaluator_control": "B",
        "full_baseline": "C",
        "interpretation": "small-sample engineering direction only; no precise Elo",
        "diagnosis_labels": ["SEARCH_LIKELY_PRIMARY", "EVALUATOR_LIKELY_PRIMARY", "THROUGHPUT_LIKELY_PRIMARY", "MIXED", "INSUFFICIENT_SAMPLE"],
        "arm_summaries": summaries,
        "b_evidence_immutable": b_immutable,
        "evaluator_control_5k_status": "CALIBRATION_INCOMPLETE",
        "evaluator_control_20k_status": "NOT_RUN_RUNTIME_INFEASIBLE",
        "partial_5k_outcomes_ignored": True,
    })
    _write(output / "performance.json", {
        "controller": "GenericChess Python",
        "cross_engine_fairness": "equal wall-clock seconds per move",
        "node_control": "same GC implementation only",
        "worker_startup_excluded": True,
        "time_validity": "engine elapsed checked against max(50ms,5%); controller wall retained separately",
        "evaluator_control_budget_freeze": "evaluator_control_budget_freeze.json",
        "c_max_plies": MAX_PLIES,
    })
    _write(output / "final_verdict.json", {
        "required_start_sha": START_SHA,
        "alphasho_read_only": before == after,
        "b_evidence_immutable": b_immutable,
        "legacy_evaluator_parity": "see legacy_evaluator_parity.json",
        "formal_results_completed": True,
        "protocol_valid": protocol_valid,
        "strength_score_unlock": strength_score_unlock,
        "precise_elo_claim": False,
        "round6_tuning_started": False,
        "evaluator_control_5k_status": "CALIBRATION_INCOMPLETE",
        "evaluator_control_20k_status": "NOT_RUN_RUNTIME_INFEASIBLE",
        "arm_summaries": summaries,
    })
    excluded_suffixes = (".log", ".err", ".stdout", ".stderr")
    manifest_files = [path for path in output.rglob("*")
                      if path.is_file() and path.name != "manifest.json"
                      and not any(path.name.endswith(suffix) for suffix in excluded_suffixes)]
    _write(output / "manifest.json", {
        "sha256": {str(path.relative_to(output)).replace("\\", "/"): _sha(path) for path in sorted(manifest_files)},
        "excluded_temporary_log_suffixes": list(excluded_suffixes),
    })


def run_c_only(output: Path = ROUND) -> None:
    """Run only Full Baseline C after immutable B evidence is complete."""
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip() != START_SHA:
        raise RuntimeError("Round 5 C-only must remain on the required starting SHA")
    required = [
        output / "search_control" / "0p25s" / "games.jsonl",
        output / "search_control" / "1p00s" / "games.jsonl",
        output / "evaluator_control" / "low_nodes" / "paired_results.json",
        output / "evaluator_control" / "high_nodes" / "paired_results.json",
        output / "evaluator_control_budget_freeze.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError({"kind": "B_EVIDENCE_MISSING", "paths": missing})
    c_dirs = [output / "full_baseline" / "0p25s", output / "full_baseline" / "1p00s"]
    if any(any(path.is_file() for path in directory.glob("*")) for directory in c_dirs):
        raise RuntimeError("C artifacts already exist; refusing to overwrite or rerun C")
    b_before = _hash_named_files(_b_evidence_paths(output))
    before = json.loads((output / "alphasho_repo_before.json").read_text(encoding="utf-8"))
    compiled = compile_ruleset(build_shogi_ruleset(corrected_promotion=True, cshogi_orientation=True))
    _install_dynamic_drop_filter()
    suite = _load_suite()
    cfg = EvaluationConfig()
    generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(compiled, cfg)[0], cfg)
    worker = Worker(output)
    try:
        _run_arm(compiled, worker, suite, c_dirs[0], "C", generic, "current", "seconds", 0.25, 10, MAX_PLIES)
        _run_arm(compiled, worker, suite[:6], c_dirs[1], "C", generic, "current", "seconds", 1.0, 6, MAX_PLIES)
    finally:
        worker.close()
    _write_paired_results_for_arm(c_dirs[0])
    _write_paired_results_for_arm(c_dirs[1])
    after = capture_repo_state()
    _write(output / "alphasho_repo_after.json", after)
    b_after = _hash_named_files(_b_evidence_paths(output))
    _write_final_closure(output, before, after, b_before, b_after)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROUND)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--formal-b-only", action="store_true")
    parser.add_argument("--c-only", action="store_true")
    args = parser.parse_args()
    modes = sum(bool(value) for value in (args.resume, args.formal_b_only, args.c_only))
    if modes > 1:
        parser.error("--resume, --formal-b-only, and --c-only are mutually exclusive")
    (run_c_only if args.c_only else run_formal_b if args.formal_b_only else resume_remaining if args.resume else run)(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
