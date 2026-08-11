"""Round 5 Corrective R1.2 runner.

This module is deliberately separate from the historical Round 5 runner.  It
uses the certified semantic ruleset for every formal measurement and never
installs benchmark-local Shogi legality patches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import cshogi

from ..ai.alphabeta.search import run_root_search
from ..ai.alphabeta.statistics import SearchStatistics
from ..ai.alphabeta.transposition import TranspositionTable
from ..ai.alphabeta.tuning import SearchTuning
from ..ai.evaluation.cache import EvaluationProfileCache
from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.evaluator import Evaluator
from ..ai.limits import SearchLimits
from ..core.movegen import legal_actions
from ..core.semantic_executor import semantic_engine_for
from ..rules.compiler import compile_semantic_ruleset
from ..rules.ir import CompiledSemanticRuleset
from ..session.session import GameSession
from .alphasho_bridge import ALPHASHO_ROOT, audit_alphasho, capture_repo_state
from .round5_benchmark import (
    LegacyEvaluator,
    SearchSemanticCompiled,
    Worker,
    _gc_check,
    _load_suite,
    _norm,
    _seed_session,
    _sha,
    _terminal,
    _write,
    _write_jsonl,
)
from .shogi_rules import cshogi_legal_usi_set, gc_action_to_usi, gc_to_sfen, sfen_to_gc_state
from .shogi_semantic_rules import build_semantic_shogi_ruleset


ROOT = Path(__file__).resolve().parents[2]
ROUND = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1_2"
HISTORICAL = ROOT / "artifacts" / "round5_alphasho_benchmark"
HISTORICAL_R1 = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1"
BASELINE_SHA = "6a2fe650a6b5737df1a9cab93a84e94732169e7d"
R1_1_SOURCE_SHA = "682760f3c43b33660fbc760abf29564cc8e67cc3"
CHECKPOINT_SHA = "de176441aa45b245cc5f14920f9df93fccfd0f2d"
CERTIFIED_FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
MAX_PLIES = 128
B_MAX_PLIES = 512
LOW_NODE_BUDGET = 256
HIGH_NODE_BUDGET = 512
WALL_BUDGETS = (0.50, 1.00, 2.00, 3.00, 5.00)
TIMING_TOLERANCE = "max(0.050s, 5% of budget)"


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _assert_certified() -> SearchSemanticCompiled:
    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    if semantic.ruleset_fingerprint != CERTIFIED_FINGERPRINT:
        raise RuntimeError({
            "kind": "CERTIFIED_RULESET_FINGERPRINT_MISMATCH",
            "expected": CERTIFIED_FINGERPRINT,
            "actual": semantic.ruleset_fingerprint,
        })
    # The wrapper only exposes read-only geometry metadata required by the
    # existing search/evaluator.  Core move generation sees the semantic IR.
    return SearchSemanticCompiled(
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )


def _action_map(compiled, state) -> dict[str, list[Any]]:
    mapping: dict[str, list[Any]] = {}
    for action in legal_actions(state, compiled):
        mapping.setdefault(gc_action_to_usi(action), []).append(action)
    return mapping


def _resolve_semantic_action(compiled, state, usi: str) -> Any:
    matches = _action_map(compiled, state).get(usi, [])
    if len(matches) == 0:
        raise RuntimeError({"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "semantic_action_lookup", "usi": usi})
    if len(matches) > 1:
        raise RuntimeError({"kind": "SEMANTIC_USI_AMBIGUITY", "usi": usi, "matches": len(matches)})
    return matches[0]


def _semantic_legal_usis(compiled, state) -> set[str]:
    return set(_action_map(compiled, state))


def _history_manifest(root: Path) -> dict[str, Any]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    sha256: dict[str, Any] = {}
    for path in files:
        sha256[str(path.relative_to(root)).replace("\\", "/")] = {
            "sha256": _sha(path),
            "size_bytes": path.stat().st_size,
        }
    return {"root": str(root.relative_to(ROOT)).replace("\\", "/"), "file_count": len(files), "sha256": sha256}


def _write_historical_manifest(
    output: Path, name: str, root: Path = HISTORICAL
) -> dict[str, Any]:
    value = _history_manifest(root)
    _write(output / name, value)
    return value


def _public_surface_audit(output: Path) -> dict[str, Any]:
    """Record the public-surface patch without changing any public branch."""
    source = "313936a"
    changed = subprocess.run(
        ["git", "-C", str(ROOT), "diff-tree", "--no-commit-id", "--name-only", "-r", source],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    local_master = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "refs/heads/master"],
        capture_output=True, text=True,
    )
    remote_master = subprocess.run(
        ["git", "-C", str(ROOT), "ls-remote", "origin", "refs/heads/master"],
        capture_output=True, text=True,
    )
    remote_line = remote_master.stdout.strip().splitlines()
    value = {
        "source_commit": source,
        "source_commit_changed_paths": changed,
        "readme_only_patch": changed == ["README.md"],
        "functional_code_changed": any(path != "README.md" for path in changed),
        "local_master": local_master.stdout.strip() if local_master.returncode == 0 else None,
        "remote_master": remote_line[0].split()[0] if remote_line and len(remote_line[0].split()) >= 2 else None,
        "remote_master_query_returncode": remote_master.returncode,
        "remote_master_query_error": remote_master.stderr.strip() or None,
        "master_modified": False,
        "metadata_write": "DEFERRED_NO_SAFE_WRITE",
        "alpha_sho_source_touched": False,
    }
    _write(output / "public_surface_audit.json", value)
    return value


class R1GCPlayer:
    def __init__(self, compiled, evaluator) -> None:
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
        return {
            "usi": gc_action_to_usi(action) if action is not None else None,
            "score": int(score),
            "pv": [gc_action_to_usi(item) for item in pv],
            "completed_depth": stats.completed_depth,
            "nodes": stats.nodes,
            "qnodes": stats.qnodes,
            "elapsed_seconds": elapsed,
            "termination_reason": reason,
            "tt_hits": stats.tt_hits,
            "fallback": bool(stats.root_scan_used_fallback),
            "first_legal_latency_seconds": stats.time_to_first_legal_action,
            "first_completed_iteration_seconds": stats.time_to_first_completed_iteration,
            "controller_wall_seconds": elapsed,
        }


def _timing_invalid(decision: dict[str, Any], budget: float) -> bool:
    elapsed = float(decision.get("elapsed_seconds", decision.get("wall_seconds", 0.0)))
    return elapsed > float(budget) + max(0.050, float(budget) * 0.05)


def _run_one_game(compiled, worker, opening, candidate_color, profile, budget_kind, budget,
                  max_plies, gc_player, label) -> dict[str, Any]:
    session = _seed_session(compiled, opening["sfen"])
    board = cshogi.Board(opening["sfen"])
    history: list[str] = []
    moves: list[dict[str, Any]] = []
    failure = None
    for ply in range(max_plies):
        gc_legal = _semantic_legal_usis(compiled, session.state)
        oracle_legal = cshogi_legal_usi_set(board.sfen())
        if gc_legal != oracle_legal:
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "pre_move", "ply": ply,
                       "missing_in_gc": sorted(oracle_legal - gc_legal), "extra_in_gc": sorted(gc_legal - oracle_legal)}
            break
        color = "black" if board.turn == cshogi.BLACK else "white"
        use_gc = color == candidate_color
        started = time.monotonic()
        if use_gc:
            decision = gc_player.choose(session, budget_kind, budget)
            usi = decision["usi"]
        else:
            result = worker.request({"command": "choose", "profile": profile, "budget_kind": budget_kind,
                                     "budget": budget, "sfen": board.sfen(), "initial_sfen": opening["sfen"],
                                     "history": history})
            usi = result["bestmove"]
            decision = result.get("search_info") or {}
            decision = {"usi": usi, **decision}
        wall = time.monotonic() - started
        if usi not in oracle_legal or usi not in gc_legal:
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "chosen_move", "ply": ply,
                       "usi": usi, "gc_legal": usi in gc_legal, "oracle_legal": usi in oracle_legal}
            break
        try:
            action = _resolve_semantic_action(compiled, session.state, usi)
            session.submit(action)
            board.push_usi(usi)
        except Exception as exc:
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "submit", "ply": ply,
                       "usi": usi, "error": f"{type(exc).__name__}: {exc}"}
            break
        gc_sfen = _norm(gc_to_sfen(session.state, compiled))
        oracle_sfen = _norm(board.sfen())
        state_equal = gc_sfen == oracle_sfen
        check_equal = bool(board.is_check()) == _gc_check(session.state, compiled)
        side_equal = session.state.position.side_to_move == (0 if board.turn == cshogi.BLACK else 1)
        elapsed = float(decision.get("elapsed_seconds", wall))
        row = {"ply": ply + 1, "color": color, "engine": "gc" if use_gc else "alphasho", "usi": usi,
               "sfen": oracle_sfen, "history": list(history), "wall_seconds": wall,
               "engine_elapsed_seconds": elapsed, "decision": decision,
               "state_equal": state_equal, "check_equal": check_equal, "side_equal": side_equal}
        if budget_kind == "seconds":
            row["timing_tolerance_seconds"] = max(0.050, float(budget) * 0.05)
            row["timing_invalid"] = _timing_invalid(decision, float(budget))
        moves.append(row)
        if not (state_equal and check_equal and side_equal):
            failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "post_move", "ply": ply + 1,
                       "usi": usi, "gc_sfen": gc_sfen, "oracle_sfen": oracle_sfen,
                       "check_equal": check_equal, "side_equal": side_equal}
            break
        history.append(usi)
        if board.is_game_over():
            break
    kind, reason, winner, _ = _terminal(board, len(moves) >= max_plies)
    if failure:
        kind, reason, winner = failure["kind"], failure["kind"], None
    timing_invalid = any(bool(row.get("timing_invalid")) for row in moves)
    eligible = kind in {"decisive", "rule_draw"} and not timing_invalid
    score = None if not eligible else (0.5 if winner is None else (1.0 if winner == candidate_color else 0.0))
    return {"opening": opening["name"], "initial_sfen": opening["sfen"], "candidate": "gc", "candidate_color": candidate_color,
            "profile": profile, "label": label, "budget_kind": budget_kind, "budget": budget,
            "max_plies": max_plies, "outcome_kind": kind, "outcome_reason": reason, "winner": winner,
            "played_plies": len(moves), "final_sfen": _norm(board.sfen()), "candidate_score": score,
            "eligible_for_strength": eligible, "timing_invalid": timing_invalid, "correctness_failure": failure,
            "history_complete_from_suite_start": True, "moves": moves}


def _summarize(games: list[dict[str, Any]], experiment: str, budget_kind: str, budget: int | float) -> dict[str, Any]:
    eligible = [g for g in games if g["eligible_for_strength"] and g["candidate_score"] is not None]
    return {"schema_version": 2, "experiment": experiment, "budget_kind": budget_kind, "budget": budget,
            "games": len(games), "eligible_games": len(eligible),
            "candidate_wins": sum(g["candidate_score"] == 1.0 for g in eligible),
            "opponent_wins": sum(g["candidate_score"] == 0.0 for g in eligible),
            "rule_draws": sum(g["outcome_kind"] == "rule_draw" for g in eligible),
            "unresolved": sum(g["outcome_kind"] == "unresolved" for g in games),
            "protocol_excluded_nyugyoku": sum(g["outcome_kind"] == "protocol_excluded_nyugyoku" for g in games),
            "correctness_failures": sum(g["outcome_kind"] == "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE" for g in games),
            "semantic_usi_ambiguity": sum(g["outcome_reason"] == "SEMANTIC_USI_AMBIGUITY" for g in games),
            "timing_invalid_games": sum(bool(g.get("timing_invalid")) for g in games),
            "candidate_score": (sum(g["candidate_score"] for g in eligible) / len(eligible) if eligible else None),
            "by_color": {color: {"games": sum(g["candidate_color"] == color for g in games),
                                  "eligible": sum(g["candidate_color"] == color and g["eligible_for_strength"] for g in games),
                                  "wins": sum(g["candidate_color"] == color and g["candidate_score"] == 1.0 for g in eligible),
                                  "losses": sum(g["candidate_color"] == color and g["candidate_score"] == 0.0 for g in eligible)}
                         for color in ("black", "white")},
            "average_plies": statistics.mean([g["played_plies"] for g in games]) if games else 0,
            "median_plies": statistics.median([g["played_plies"] for g in games]) if games else 0,
            "timing_control": "wall_clock_per_move", "timing_tolerance": TIMING_TOLERANCE}


def _paired(arm_dir: Path) -> dict[str, Any]:
    games = [json.loads(line) for line in (arm_dir / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_opening: dict[str, dict[str, Any]] = {}
    for game in games:
        by_opening.setdefault(game["opening"], {})[game["candidate_color"]] = game
    rows = []
    for opening, colors in sorted(by_opening.items()):
        black, white = colors.get("black"), colors.get("white")
        both = bool(black and white and black["eligible_for_strength"] and white["eligible_for_strength"])
        rows.append({"opening": opening, "black": black, "white": white, "paired_eligible": both,
                     "paired_score": (black["candidate_score"] + white["candidate_score"]) / 2 if both else None})
    result = {"games": len(games), "paired_results": rows,
              "paired_openings": sum(r["paired_eligible"] for r in rows),
              "paired_eligible": sum(r["paired_eligible"] for r in rows),
              "paired_score": (sum(r["paired_score"] for r in rows if r["paired_score"] is not None) /
                               max(1, sum(r["paired_score"] is not None for r in rows)) if any(r["paired_score"] is not None for r in rows) else None)}
    _write(arm_dir / "paired_results.json", result)
    return result


def _run_formal_arm(compiled, worker, suite, arm_dir, experiment, profile, evaluator, budget_kind, budget, count, max_plies):
    arm_dir.mkdir(parents=True, exist_ok=True)
    player = R1GCPlayer(compiled, evaluator)
    games = []
    for opening in suite[:count]:
        for color in ("black", "white"):
            games.append(_run_one_game(compiled, worker, opening, color, profile, budget_kind, budget, max_plies, player, experiment))
    _write_jsonl(arm_dir / "games.jsonl", games)
    _write_jsonl(arm_dir / "events.jsonl", [{"event": "game_complete", "experiment": experiment,
                                               "opening": g["opening"], "candidate_color": g["candidate_color"],
                                               "outcome_kind": g["outcome_kind"], "played_plies": g["played_plies"]} for g in games])
    summary = _summarize(games, experiment, budget_kind, budget)
    _write(arm_dir / "summary.json", summary)
    _paired(arm_dir)
    return summary


def _run_b_arm(compiled, suite, arm_dir, evaluator, budget, count):
    arm_dir.mkdir(parents=True, exist_ok=True)
    candidate = R1GCPlayer(compiled, evaluator)
    opponent = R1GCPlayer(compiled, LegacyEvaluator(compiled))
    games = []
    for opening in suite[:count]:
        for candidate_color in ("black", "white"):
            session = _seed_session(compiled, opening["sfen"])
            board = cshogi.Board(opening["sfen"])
            history = []
            moves = []
            failure = None
            for ply in range(B_MAX_PLIES):
                gc_legal = _semantic_legal_usis(compiled, session.state)
                oracle = cshogi_legal_usi_set(board.sfen())
                if gc_legal != oracle:
                    failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "pre_move", "ply": ply}
                    break
                color = "black" if board.turn == cshogi.BLACK else "white"
                decision = (candidate if color == candidate_color else opponent).choose(session, "nodes", budget)
                usi = decision["usi"]
                try:
                    if usi not in gc_legal or usi not in oracle:
                        raise RuntimeError("chosen move absent from legal set")
                    action = _resolve_semantic_action(compiled, session.state, usi)
                    session.submit(action)
                    board.push_usi(usi)
                except Exception as exc:
                    failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "submit", "ply": ply,
                               "error": f"{type(exc).__name__}: {exc}"}
                    break
                state_equal = _norm(gc_to_sfen(session.state, compiled)) == _norm(board.sfen())
                check_equal = _gc_check(session.state, compiled) == bool(board.is_check())
                side_equal = session.state.position.side_to_move == (0 if board.turn == cshogi.BLACK else 1)
                moves.append({"ply": ply + 1, "color": color, "engine": "gc", "usi": usi,
                              "sfen": _norm(board.sfen()), "history": list(history), "decision": decision,
                              "state_equal": state_equal, "check_equal": check_equal, "side_equal": side_equal})
                if not (state_equal and check_equal and side_equal):
                    failure = {"kind": "ENGINE_OR_ADAPTER_CORRECTNESS_FAILURE", "phase": "post_move", "ply": ply + 1}
                    break
                history.append(usi)
                if board.is_game_over():
                    break
            kind, reason, winner, _ = _terminal(board, len(moves) >= B_MAX_PLIES)
            if failure:
                kind, reason, winner = failure["kind"], failure["kind"], None
            eligible = kind in {"decisive", "rule_draw"}
            score = None if not eligible else (0.5 if winner is None else (1.0 if winner == candidate_color else 0.0))
            games.append({"opening": opening["name"], "initial_sfen": opening["sfen"], "candidate": "gc-generic",
                          "candidate_color": candidate_color, "budget_kind": "nodes", "budget": budget,
                          "max_plies": B_MAX_PLIES, "outcome_kind": kind, "outcome_reason": reason, "winner": winner,
                          "played_plies": len(moves), "final_sfen": _norm(board.sfen()), "candidate_score": score,
                          "eligible_for_strength": eligible, "timing_invalid": False, "correctness_failure": failure,
                          "history_complete_from_suite_start": True, "moves": moves})
    _write_jsonl(arm_dir / "games.jsonl", games)
    summary = _summarize(games, "B", "nodes", budget)
    _write(arm_dir / "summary.json", summary)
    _paired(arm_dir)
    return summary


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) * fraction + 0.999999) - 1)))
    return ordered[index]


def _calibration_profile_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for profile in sorted({row["profile"] for row in rows}):
        for budget in WALL_BUDGETS:
            selected = [
                row for row in rows
                if row["profile"] == profile and row["budget"] == budget
            ]
            walls = [float(row["wall_seconds"]) for row in selected]
            engine = [float(row["engine_elapsed_seconds"]) for row in selected]
            first = [
                float(row["first_legal_latency_seconds"])
                for row in selected
                if row["first_legal_latency_seconds"] is not None
            ]
            key = f"{profile}@{budget:.2f}s"
            summary[key] = {
                "profile": profile,
                "budget": budget,
                "trials": len(selected),
                "median_wall_seconds": statistics.median(walls) if walls else None,
                "p90_wall_seconds": _percentile(walls, 0.90),
                "max_wall_seconds": max(walls) if walls else None,
                "median_engine_elapsed_seconds": statistics.median(engine) if engine else None,
                "p90_engine_elapsed_seconds": _percentile(engine, 0.90),
                "max_engine_elapsed_seconds": max(engine) if engine else None,
                "timing_invalid": sum(not row["timing_valid"] for row in selected),
                "first_legal_latency_trials": len(first),
                "first_legal_latency_median_seconds": statistics.median(first) if first else None,
                "first_legal_latency_p90_seconds": _percentile(first, 0.90),
                "first_legal_latency_max_seconds": max(first) if first else None,
            }
    return summary


def _calibrate(output: Path, compiled, worker, suite, legacy_eval, generic) -> dict[str, Any]:
    rows = []
    profiles = (
        ("gc_legacy", "gc", legacy_eval),
        ("alphasho_legacy", "alphasho", "legacy"),
        ("gc_generic", "gc", generic),
        ("alphasho_current", "alphasho", "current"),
    )
    for budget in WALL_BUDGETS:
        for opening in suite[:10]:
            for color in ("black", "white"):
                for name, engine, evaluator_or_profile in profiles:
                    session = _seed_session(compiled, opening["sfen"])
                    started = time.monotonic()
                    if engine == "gc":
                        decision = R1GCPlayer(
                            compiled, evaluator_or_profile
                        ).choose(session, "seconds", budget)
                    else:
                        result = worker.request({
                            "command": "choose",
                            "profile": evaluator_or_profile,
                            "budget_kind": "seconds",
                            "budget": budget,
                            "sfen": opening["sfen"],
                            "initial_sfen": opening["sfen"],
                            "history": [],
                        })
                        decision = result.get("search_info") or {}
                    wall = time.monotonic() - started
                    engine_elapsed = float(
                        decision.get("elapsed_seconds", wall)
                    )
                    first_legal = decision.get(
                        "first_legal_latency_seconds",
                        decision.get("time_to_first_legal_action"),
                    )
                    first_iteration = decision.get(
                        "first_completed_iteration_seconds",
                        decision.get("time_to_first_completed_iteration"),
                    )
                    tolerance = max(0.050, budget * 0.05)
                    rows.append({
                        "budget": budget,
                        "opening": opening["name"],
                        "color": color,
                        "profile": name,
                        "engine_elapsed_seconds": engine_elapsed,
                        "wall_seconds": wall,
                        "controller_minus_engine_seconds": wall - engine_elapsed,
                        "timing_tolerance_seconds": tolerance,
                        "timing_valid": wall <= budget + tolerance,
                        "first_legal_latency_seconds": first_legal,
                        "first_completed_iteration_seconds": first_iteration,
                        "nodes": decision.get("nodes"),
                        "qnodes": decision.get("qnodes"),
                        "completed_depth": decision.get("completed_depth"),
                        "termination_reason": decision.get("termination_reason"),
                    })
    _write_jsonl(output / "runtime_calibration.jsonl", rows)
    profile_summary = _calibration_profile_summary(rows)
    _write(output / "runtime_calibration_profile_summary.json", profile_summary)
    summary = {}
    for budget in WALL_BUDGETS:
        selected = [row for row in rows if row["budget"] == budget]
        summary[str(budget)] = {
            "budget": budget,
            "trials": len(selected),
            "timing_invalid": sum(not row["timing_valid"] for row in selected),
            "max_wall_seconds": max((row["wall_seconds"] for row in selected), default=None),
            "median_wall_seconds": statistics.median(
                [row["wall_seconds"] for row in selected]
            ) if selected else None,
            "profiles": {
                profile: profile_summary[f"{profile}@{budget:.2f}s"]
                for profile, _engine, _value in profiles
            },
        }
    _write(output / "runtime_calibration_summary.json", summary)
    qualified = [
        budget for budget in WALL_BUDGETS
        if summary[str(budget)]["timing_invalid"] == 0
    ]
    if len(qualified) < 2:
        failure = {
            "kind": "R1.2_TIMING_CALIBRATION",
            "status": "FAIL_INSUFFICIENT_VALID_BUDGETS_R1_2",
            "candidate_budgets_seconds": list(WALL_BUDGETS),
            "qualified_budgets_seconds": qualified,
            "required_profiles": [profile[0] for profile in profiles],
            "timing_tolerance": TIMING_TOLERANCE,
            "profile_summary": profile_summary,
            "summary": summary,
            "formal_abc_started": False,
            "final_closure_created": False,
        }
        _write(output / "runtime_calibration_failure.json", failure)
        raise RuntimeError(failure)
    freeze = {
        "schema_version": 2,
        "candidate_budgets_seconds": list(WALL_BUDGETS),
        "qualified_budgets_seconds": qualified,
        "LOW_SECONDS": qualified[0],
        "HIGH_SECONDS": qualified[1],
        "selection_inputs_runtime_only": True,
        "profiles": [p[0] for p in profiles],
        "timing_tolerance": TIMING_TOLERANCE,
        "calibration_trials": len(rows),
    }
    _write(output / "timing_budget_freeze.json", freeze)
    return freeze


def _preflight(output: Path, compiled, suite) -> None:
    cases = [{"name": "initial", "sfen": suite[0]["sfen"]}]
    failures = []
    for case in cases:
        state = sfen_to_gc_state(compiled, case["sfen"])
        gc = _semantic_legal_usis(compiled, state)
        oracle = cshogi_legal_usi_set(case["sfen"])
        if gc != oracle:
            failures.append({"name": case["name"], "missing": sorted(oracle - gc), "extra": sorted(gc - oracle)})
    result = {"schema_version": 1, "corpus": [c["name"] for c in cases], "correctness_failures": len(failures),
              "semantic_engine": True, "cshogi_comparison": True, "failures": failures,
              "status": "PASS" if not failures else "FAIL"}
    _write(output / "semantic_lockstep_preflight.json", result)
    if failures:
        raise RuntimeError(result)


def run(output: Path = ROUND) -> None:
    harness_sha = _git_head()
    source_parent = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD^"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    clean = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip() == ""
    checkpoint_ancestor = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", CHECKPOINT_SHA, harness_sha],
        capture_output=True,
    ).returncode == 0
    baseline_ancestor = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", BASELINE_SHA, harness_sha],
        capture_output=True,
    ).returncode == 0
    if (
        not clean
        or source_parent != R1_1_SOURCE_SHA
        or not checkpoint_ancestor
        or not baseline_ancestor
    ):
        raise RuntimeError({"kind": "R1_HARNESS_PROVENANCE_INVALID", "harness_sha": harness_sha,
                            "source_parent": source_parent,
                            "required_parent": R1_1_SOURCE_SHA,
                            "clean": clean, "checkpoint_ancestor": checkpoint_ancestor,
                            "baseline_ancestor": baseline_ancestor})
    output.mkdir(parents=True, exist_ok=True)
    compiled = _assert_certified()
    suite = _load_suite()
    _write(output / "baseline.json", {"r1_1_source_sha": R1_1_SOURCE_SHA,
                                       "harness_sha": harness_sha,
                                       "source_parent": source_parent,
                                       "checkpoint_sha": CHECKPOINT_SHA, "baseline_ancestor": BASELINE_SHA,
                                       "certified_ruleset_fingerprint": CERTIFIED_FINGERPRINT,
                                       "formal_ruleset_authority": "compile_semantic_ruleset(build_semantic_shogi_ruleset())",
                                       "historical_tree_immutable": True, "max_plies": MAX_PLIES, "b_max_plies": B_MAX_PLIES})
    _write(output / "harness_provenance.json", {"mode": "R1.2", "harness_sha_required": harness_sha,
                                                 "r1_1_source_sha": R1_1_SOURCE_SHA,
                                                 "source_parent": source_parent,
                                                 "branch": "sandbox", "legal_rule_monkey_patch": False,
                                                 "lossless_semantic_action_mapping": True})
    old_before = _write_historical_manifest(
        output, "legacy_round5_artifact_tree_before.json", HISTORICAL
    )
    old_r1_before = _write_historical_manifest(
        output, "legacy_round5_corrective_r1_tree_before.json", HISTORICAL_R1
    )
    before = capture_repo_state()
    _write(output / "alphasho_repo_before.json", before)
    _write(output / "ruleset_authority.json", {"constructor": "build_semantic_shogi_ruleset", "compiler": "compile_semantic_ruleset",
                                                 "fingerprint": compiled.ruleset_fingerprint, "asserted": compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT})
    public_surface = _public_surface_audit(output)
    _preflight(output, compiled, suite)
    _write(output / "bridge_protocol.json", {"persistent_worker": True, "semantic_engine_sole_legality_authority": True,
                                               "lossless_usi_mapping": True, "dual_state_lockstep": ["legal_set", "submit", "normalized_sfen", "side", "check"],
                                               "nyugyoku": "protocol_excluded_nyugyoku", "timing_tolerance": TIMING_TOLERANCE})
    _write(output / "suite.json", {"source": str(ALPHASHO_ROOT / "configs" / "training" / "evaluation_positions.jsonl"),
                                    "positions": suite, "low_positions": 10, "high_positions": 6, "paired_colors": True,
                                    "a_c_max_plies": MAX_PLIES, "b_max_plies": B_MAX_PLIES})
    worker = Worker(output)
    calibration_failure = None
    try:
        legacy = LegacyEvaluator(compiled)
        cfg = EvaluationConfig()
        generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(compiled, cfg)[0], cfg)
        parity = []
        for i, opening in enumerate(suite * 50):
            sfen = opening["sfen"]
            state = sfen_to_gc_state(compiled, sfen)
            score = legacy.evaluate(state)
            remote = worker.request({"command": "evaluate_legacy", "sfen": sfen})["score"]
            parity.append({"index": i, "sfen": _norm(sfen), "gc_score": score, "alphasho_score": remote, "equal": score == remote})
        _write_jsonl(output / "legacy_evaluator_parity_sanity.jsonl", parity)
        _write(output / "legacy_evaluator_parity_sanity.json", {"positions": len(parity), "failures": sum(not r["equal"] for r in parity), "all_equal": all(r["equal"] for r in parity)})
        try:
            freeze = _calibrate(output, compiled, worker, suite, legacy, generic)
        except RuntimeError as exc:
            detail = exc.args[0] if exc.args and isinstance(exc.args[0], dict) else None
            if not detail or detail.get("status") != "FAIL_INSUFFICIENT_VALID_BUDGETS_R1_2":
                raise
            calibration_failure = detail
        if calibration_failure is None:
            low, high = freeze["LOW_SECONDS"], freeze["HIGH_SECONDS"]
            _run_formal_arm(compiled, worker, suite, output / "search_control" / "low", "A", "legacy", legacy, "seconds", low, 10, MAX_PLIES)
            _run_formal_arm(compiled, worker, suite, output / "search_control" / "high", "A", "legacy", legacy, "seconds", high, 6, MAX_PLIES)
            _run_b_arm(compiled, suite, output / "evaluator_control" / "low_nodes", generic, LOW_NODE_BUDGET, 6)
            _run_b_arm(compiled, suite, output / "evaluator_control" / "high_nodes", generic, HIGH_NODE_BUDGET, 4)
            _run_formal_arm(compiled, worker, suite, output / "full_baseline" / "low", "C", "current", generic, "seconds", low, 10, MAX_PLIES)
            _run_formal_arm(compiled, worker, suite, output / "full_baseline" / "high", "C", "current", generic, "seconds", high, 6, MAX_PLIES)
    finally:
        worker.close()
    after = capture_repo_state()
    _write(output / "alphasho_repo_after.json", after)
    if before != after:
        raise RuntimeError("AlphaSho repository changed during R1.2")
    old_after = _write_historical_manifest(
        output, "legacy_round5_artifact_tree_after.json", HISTORICAL
    )
    old_r1_after = _write_historical_manifest(
        output, "legacy_round5_corrective_r1_tree_after.json", HISTORICAL_R1
    )
    old_evidence_immutable = old_before == old_after and old_r1_before == old_r1_after
    if not old_evidence_immutable:
        raise RuntimeError("historical Round 5 evidence changed")
    if calibration_failure is not None:
        calibration_failure["alphasho_read_only"] = before == after
        calibration_failure["old_evidence_immutable"] = old_evidence_immutable
        calibration_failure["formal_abc_started"] = False
        calibration_failure["final_closure_created"] = False
        calibration_failure["public_surface_audit"] = public_surface
        _write(output / "diagnostic_verdict.json", calibration_failure)
        raise RuntimeError(calibration_failure)
    summaries = {str(p.relative_to(output)).replace("\\", "/"): json.loads(p.read_text(encoding="utf-8"))
                 for p in output.glob("*/**/summary.json")}
    paired = {str(p.relative_to(output)).replace("\\", "/"): json.loads(p.read_text(encoding="utf-8"))
              for p in output.glob("*/**/paired_results.json")}
    gates = {
        "R1_HARNESS_PROVENANCE": _git_head() == harness_sha,
        "CERTIFIED_RULESET_AUTHORITY": compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT,
        "LEGAL_RULE_MONKEY_PATCH_ABSENT": True,
        "LOSSLESS_SEMANTIC_ACTION_MAPPING": True,
        "R1_SEMANTIC_LOCKSTEP_PREFLIGHT": True,
        "LEGACY_ROUND5_ARTIFACT_TREE_IMMUTABLE": old_evidence_immutable,
        "LEGACY_R1_ARTIFACT_TREE_IMMUTABLE": old_r1_before == old_r1_after,
        "ALPHASHO_READ_ONLY": before == after,
        "R1_TIMING_CALIBRATION": True,
        "PUBLIC_SURFACE_READ_ONLY_AUDIT": public_surface["readme_only_patch"] and not public_surface["functional_code_changed"],
    }
    for path, summary in summaries.items():
        gates[path + ":correctness"] = summary["correctness_failures"] == 0
        if summary["budget_kind"] == "seconds":
            gates[path + ":timing"] = summary["timing_invalid_games"] == 0
    for path, result in paired.items():
        gates[path + ":paired"] = result["paired_eligible"] > 0
    if not all(gates.values()):
        _write(output / "closure_failure.json", {"gates": gates, "summaries": summaries, "paired": paired})
        raise RuntimeError({"kind": "R1_CLOSURE_GATE_FAILED", "gates": gates})
    _write(output / "decomposition.json", {"experiments": {"A": "Search Control", "B": "Evaluator Control", "C": "Full Baseline"},
                                            "arm_summaries": summaries, "paired": paired, "precise_elo_claim": False})
    _write(output / "performance.json", {"controller": "GenericChess Python", "worker_startup_excluded": True,
                                          "timing_tolerance": TIMING_TOLERANCE, "a_c_budgets": json.loads((output / "timing_budget_freeze.json").read_text())})
    _write(output / "final_verdict.json", {"ROUND5_CORRECTIVE_R1_2": "PASS", "R1_HARNESS_SHA": harness_sha,
                                            "R1_1_SOURCE_SHA": R1_1_SOURCE_SHA,
                                            "CERTIFIED_RULESET_AUTHORITY": "PASS", "ALPHASHO_READ_ONLY": "PASS",
                                            "LEGACY_ROUND5_ARTIFACT_TREE_IMMUTABLE": "PASS", "gates": gates,
                                            "summaries": summaries, "paired": paired, "round6_started": False})
    manifest_files = [p for p in output.rglob("*") if p.is_file() and p.name != "manifest.json" and not p.name.endswith((".log", ".err", ".stdout", ".stderr"))]
    _write(output / "manifest.json", {"sha256": {str(p.relative_to(output)).replace("\\", "/"): _sha(p) for p in sorted(manifest_files)},
                                       "excluded_temporary_log_suffixes": [".log", ".err", ".stdout", ".stderr"]})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROUND)
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
