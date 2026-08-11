"""Round 5 Corrective R1.3: bounded evaluator-control replacement.

The old R1.2 full-game evaluator-control run is retained as immutable history
but is never resumed.  This module adds only benchmark orchestration: the
certified semantic ruleset, production AlphaBeta, evaluators, and AlphaSho
source remain unchanged.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import cshogi

from ..ai.evaluation.cache import EvaluationProfileCache
from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.evaluator import Evaluator
from ..session.session import GameSession
from .alphasho_bridge import ALPHASHO_ROOT, capture_repo_state
from .round5_benchmark import LegacyEvaluator, Worker
from .round5_corrective_r1_2 import (
    BASELINE_SHA,
    CERTIFIED_FINGERPRINT,
    CHECKPOINT_SHA,
    HISTORICAL,
    HISTORICAL_R1,
    HIGH_NODE_BUDGET,
    LOW_NODE_BUDGET,
    MAX_PLIES,
    R1_1_SOURCE_SHA,
    R1GCPlayer,
    _gc_check,
    _history_manifest,
    _load_suite,
    _norm,
    _resolve_semantic_action,
    _semantic_legal_usis,
    _sha,
    _write,
    _write_jsonl,
    _assert_certified,
    _run_formal_arm,
    _seed_session,
)
from .shogi_rules import cshogi_legal_usi_set, gc_to_sfen, sfen_to_gc_state


ROOT = Path(__file__).resolve().parents[2]
ROUND = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1_3"
OLD_R1_2 = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1_2"
ROLL_OUT_HORIZON = 64
NODE_OVERSHOOT_CONTRACT = 128
TIMING_BUDGET_FILE = OLD_R1_2 / "timing_budget_freeze.json"


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _git_branch() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _assert_clean_and_provenance() -> str:
    head = _git_head()
    clean = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout.strip() == ""
    if not clean or _git_branch() != "sandbox":
        raise RuntimeError({"kind": "R1_3_WORKTREE_PROVENANCE_INVALID", "head": head,
                            "branch": _git_branch(), "clean": clean})
    return head


def _material_differential(state) -> int:
    values = LegacyEvaluator.values
    absolute = 0
    for piece in state.position.board:
        if piece is not None:
            value = values[piece.current_type_id]
            absolute += value if piece.owner == 0 else -value
    for owner, hand in enumerate(state.position.hands):
        for type_id, count in hand.counts:
            value = LegacyEvaluator.hand_values[type_id]
            absolute += count * value if owner == 0 else -count * value
    return int(absolute)


def _move_flags(usi: str) -> tuple[bool, bool]:
    promoted = usi.endswith("+")
    captured = False
    try:
        move = cshogi.move_from_usi(usi)
        captured = cshogi.move_cap(move) not in (0, 8)
    except Exception:
        # The lockstep legal-set check remains authoritative; this optional
        # cheap counter must never turn a valid rollout into a failure.
        captured = False
    return captured, promoted


def _position_record(compiled, opening: dict[str, str], budget: int,
                     evaluator_name: str, evaluator: Any) -> dict[str, Any]:
    session = _seed_session(compiled, opening["sfen"])
    oracle = cshogi_legal_usi_set(opening["sfen"])
    semantic_legal = _semantic_legal_usis(compiled, session.state)
    legal_set_equal = semantic_legal == oracle
    started = time.monotonic()
    decision = R1GCPlayer(compiled, evaluator).choose(session, "nodes", budget)
    wall = time.monotonic() - started
    usi = decision.get("usi")
    chosen_legal = usi in semantic_legal and usi in oracle
    action_resolves = False
    action_error = None
    if chosen_legal:
        try:
            _resolve_semantic_action(compiled, session.state, usi)
            action_resolves = True
        except Exception as exc:
            action_error = f"{type(exc).__name__}: {exc}"
    total_nodes = int(decision.get("nodes", 0)) + int(decision.get("qnodes", 0))
    return {
        "position_id": opening["name"],
        "normalized_sfen": _norm(opening["sfen"]),
        "budget": budget,
        "evaluator": evaluator_name,
        "search": "GenericChess current production Python AlphaBeta",
        "chosen_usi_move": usi,
        "chosen_semantic_public_action_identity": usi,
        "score": decision.get("score"),
        "pv": decision.get("pv", []),
        "pv_first_action_identity": decision.get("pv", [None])[0] if decision.get("pv") else None,
        "completed_depth": decision.get("completed_depth"),
        "nodes": decision.get("nodes"),
        "qnodes": decision.get("qnodes"),
        "total_nodes": total_nodes,
        "termination_reason": decision.get("termination_reason"),
        "wall_seconds": wall,
        "legal_result_validity": {
            "semantic_legal_set_equals_cshogi": legal_set_equal,
            "chosen_move_in_both_legal_sets": chosen_legal,
            "semantic_action_resolves_uniquely": action_resolves,
            "error": action_error,
        },
        "node_budget_contract": {
            "max_nodes": budget,
            "allowed_check_interval_overshoot": NODE_OVERSHOOT_CONTRACT,
            "compliant": total_nodes <= budget + NODE_OVERSHOOT_CONTRACT,
        },
    }


def _run_position_arm(compiled, suite: list[dict[str, str]], arm_dir: Path,
                      budget: int, requested_positions: int,
                      generic: Any, legacy: Any) -> dict[str, Any]:
    arm_dir.mkdir(parents=True, exist_ok=True)
    used = suite[:min(requested_positions, len(suite))]
    rows: list[dict[str, Any]] = []
    for opening in used:
        rows.append(_position_record(compiled, opening, budget, "generic", generic))
        rows.append(_position_record(compiled, opening, budget, "legacy_exact_alphasho", legacy))
    _write_jsonl(arm_dir / "results.jsonl", rows)
    by_position: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_position.setdefault(row["position_id"], {})[row["evaluator"]] = row
    comparisons = []
    for position_id in sorted(by_position):
        pair = by_position[position_id]
        generic_row = pair["generic"]
        legacy_row = pair["legacy_exact_alphasho"]
        comparisons.append({
            "position_id": position_id,
            "chosen_move_agreement": generic_row["chosen_usi_move"] == legacy_row["chosen_usi_move"],
            "chosen_move_generic": generic_row["chosen_usi_move"],
            "chosen_move_legacy": legacy_row["chosen_usi_move"],
            "score_delta_generic_minus_legacy": (
                generic_row["score"] - legacy_row["score"]
                if generic_row["score"] is not None and legacy_row["score"] is not None else None
            ),
            "pv_first_move_agreement": generic_row["pv_first_action_identity"] == legacy_row["pv_first_action_identity"],
        })
    validity_failures = [row for row in rows if not (
        row["legal_result_validity"]["semantic_legal_set_equals_cshogi"]
        and row["legal_result_validity"]["chosen_move_in_both_legal_sets"]
        and row["legal_result_validity"]["semantic_action_resolves_uniquely"]
        and row["node_budget_contract"]["compliant"]
    )]
    summary = {
        "schema_version": 1,
        "protocol": "Formal B2-A fixed-position evaluator isolation",
        "budget": budget,
        "requested_positions": requested_positions,
        "available_frozen_positions": len(suite),
        "positions_used": len(used),
        "used_all_available_when_short": len(suite) < requested_positions,
        "evaluator_records": len(rows),
        "comparisons": comparisons,
        "chosen_move_agreement_count": sum(c["chosen_move_agreement"] for c in comparisons),
        "chosen_move_disagreement_count": sum(not c["chosen_move_agreement"] for c in comparisons),
        "pv_first_move_agreement_count": sum(c["pv_first_move_agreement"] for c in comparisons),
        "score_deltas_comparable": sum(c["score_delta_generic_minus_legacy"] is not None for c in comparisons),
        "legal_result_failures": len(validity_failures),
        "node_budget_failures": sum(not row["node_budget_contract"]["compliant"] for row in rows),
        "sample_complete": len(used) == min(requested_positions, len(suite)) and len(rows) == 2 * len(used),
        "results_file": "results.jsonl",
    }
    _write(arm_dir / "summary.json", summary)
    return summary


def _rollout_terminal_status(board: cshogi.Board, reached_horizon: bool) -> tuple[str, str]:
    if hasattr(board, "is_nyugyoku") and board.is_nyugyoku():
        return "PROTOCOL_EXCLUDED_NYUGYOKU", "nyugyoku"
    if board.is_game_over():
        if board.is_draw():
            return "TERMINAL", "rule_draw"
        if board.is_check():
            return "TERMINAL", "checkmate"
        return "TERMINAL", "game_over"
    if reached_horizon:
        return "HORIZON_REACHED", "fixed_64_ply_horizon"
    return "ONGOING", "unexpected_early_stop"


def _run_rollout_arm(compiled, suite: list[dict[str, str]], arm_dir: Path,
                     budget: int, requested_openings: int,
                     generic: Any, legacy: Any) -> dict[str, Any]:
    arm_dir.mkdir(parents=True, exist_ok=True)
    games: list[dict[str, Any]] = []
    for opening in suite[:min(requested_openings, len(suite))]:
        for generic_color in ("black", "white"):
            session = _seed_session(compiled, opening["sfen"])
            board = cshogi.Board(opening["sfen"])
            history: list[str] = []
            moves: list[dict[str, Any]] = []
            failure = None
            semantic_divergence = 0
            legal_action_failures = 0
            budget_failures = 0
            captures = promotions = checks = 0
            for ply in range(ROLL_OUT_HORIZON):
                semantic_legal = _semantic_legal_usis(compiled, session.state)
                oracle = cshogi_legal_usi_set(board.sfen())
                if semantic_legal != oracle:
                    failure = {"phase": "pre_move_legal_set", "ply": ply,
                               "missing_in_gc": sorted(oracle - semantic_legal),
                               "extra_in_gc": sorted(semantic_legal - oracle)}
                    legal_action_failures += 1
                    break
                color = "black" if board.turn == cshogi.BLACK else "white"
                evaluator_name = "generic" if color == generic_color else "legacy_exact_alphasho"
                player = R1GCPlayer(compiled, generic if evaluator_name == "generic" else legacy)
                decision = player.choose(session, "nodes", budget)
                usi = decision.get("usi")
                total_nodes = int(decision.get("nodes", 0)) + int(decision.get("qnodes", 0))
                budget_ok = total_nodes <= budget + NODE_OVERSHOOT_CONTRACT
                if not budget_ok:
                    budget_failures += 1
                if usi not in semantic_legal or usi not in oracle:
                    failure = {"phase": "chosen_move", "ply": ply, "usi": usi,
                               "semantic_legal": usi in semantic_legal, "oracle_legal": usi in oracle}
                    legal_action_failures += 1
                    break
                try:
                    action = _resolve_semantic_action(compiled, session.state, usi)
                    before_state = session.state
                    session.submit(action)
                    board.push_usi(usi)
                except Exception as exc:
                    failure = {"phase": "submit", "ply": ply, "usi": usi,
                               "error": f"{type(exc).__name__}: {exc}"}
                    legal_action_failures += 1
                    break
                gc_sfen = _norm(gc_to_sfen(session.state, compiled))
                oracle_sfen = _norm(board.sfen())
                state_equal = gc_sfen == oracle_sfen
                side_equal = session.state.position.side_to_move == (0 if board.turn == cshogi.BLACK else 1)
                check_equal = _gc_check(session.state, compiled) == bool(board.is_check())
                divergence = not (state_equal and side_equal and check_equal)
                if divergence:
                    semantic_divergence += 1
                captured, promoted = _move_flags(usi)
                captures += int(captured)
                promotions += int(promoted)
                checks += int(board.is_check())
                moves.append({
                    "ply": ply + 1, "color": color, "evaluator": evaluator_name,
                    "usi": usi, "semantic_public_action_identity": usi,
                    "sfen": oracle_sfen, "history": list(history),
                    "decision": decision, "state_equal": state_equal,
                    "side_equal": side_equal, "check_equal": check_equal,
                    "semantic_divergence": divergence,
                    "node_budget_compliant": budget_ok,
                })
                if divergence:
                    failure = {"phase": "post_move_lockstep", "ply": ply + 1,
                               "gc_sfen": gc_sfen, "oracle_sfen": oracle_sfen,
                               "state_equal": state_equal, "side_equal": side_equal,
                               "check_equal": check_equal}
                    break
                history.append(usi)
                if board.is_game_over() or (hasattr(board, "is_nyugyoku") and board.is_nyugyoku()):
                    break
            status, reason = _rollout_terminal_status(board, len(moves) >= ROLL_OUT_HORIZON)
            if failure is not None:
                status, reason = "CORRECTNESS_FAILURE", failure.get("phase", "failure")
            games.append({
                "opening": opening["name"], "initial_sfen": opening["sfen"],
                "generic_color": generic_color, "legacy_color": "white" if generic_color == "black" else "black",
                "budget": budget, "horizon_plies": ROLL_OUT_HORIZON,
                "terminal_or_horizon_status": status, "termination_reason": reason,
                "plies_completed": len(moves), "final_normalized_sfen": _norm(board.sfen()),
                "material_differential_black_minus_white": _material_differential(session.state),
                "capture_count": captures, "promotion_count": promotions, "check_count": checks,
                "correctness_failure": failure, "semantic_divergence_count": semantic_divergence,
                "legal_action_failure_count": legal_action_failures,
                "node_budget_failure_count": budget_failures,
                "history_complete_from_suite_start": True, "moves": moves,
            })
    _write_jsonl(arm_dir / "rollouts.jsonl", games)
    by_opening: dict[str, dict[str, Any]] = {}
    for game in games:
        by_opening.setdefault(game["opening"], {})[game["generic_color"]] = game
    paired = []
    for opening, colors in sorted(by_opening.items()):
        paired.append({"opening": opening, "black_generic": colors.get("black"),
                       "white_generic": colors.get("white"),
                       "pair_complete": "black" in colors and "white" in colors})
    _write(arm_dir / "paired_rollouts.json", {"horizon_plies": ROLL_OUT_HORIZON, "pairs": paired})
    summary = {
        "schema_version": 1, "protocol": "Formal B2-B bounded paired short-horizon rollout",
        "budget": budget, "horizon_plies": ROLL_OUT_HORIZON,
        "requested_openings": requested_openings, "available_frozen_openings": len(suite),
        "openings_used": min(requested_openings, len(suite)), "games": len(games),
        "expected_games": 2 * min(requested_openings, len(suite)),
        "sample_complete": len(games) == 2 * min(requested_openings, len(suite))
                           and all(p["pair_complete"] for p in paired),
        "terminal_games": sum(g["terminal_or_horizon_status"] == "TERMINAL" for g in games),
        "horizon_reached": sum(g["terminal_or_horizon_status"] == "HORIZON_REACHED" for g in games),
        "protocol_excluded_nyugyoku": sum(g["terminal_or_horizon_status"] == "PROTOCOL_EXCLUDED_NYUGYOKU" for g in games),
        "correctness_failures": sum(g["terminal_or_horizon_status"] == "CORRECTNESS_FAILURE" for g in games),
        "semantic_divergence": sum(g["semantic_divergence_count"] for g in games),
        "legal_action_failures": sum(g["legal_action_failure_count"] for g in games),
        "node_budget_failures": sum(g["node_budget_failure_count"] for g in games),
        "paired_rollouts_file": "paired_rollouts.json",
    }
    _write(arm_dir / "summary.json", summary)
    return summary


def _write_protocol(output: Path, suite: list[dict[str, str]]) -> None:
    protocol = {
        "name": "Formal B2 — Bounded Evaluator Control",
        "replacement_for": "Formal B legacy full-game protocol, aborted for runtime",
        "outcome_driven_protocol_change": False,
        "certified_ruleset_fingerprint": CERTIFIED_FINGERPRINT,
        "ruleset_authority": "compile_semantic_ruleset(build_semantic_shogi_ruleset())",
        "budgets": {"LOW": LOW_NODE_BUDGET, "HIGH": HIGH_NODE_BUDGET},
        "position_isolation": {"requested_LOW": 16, "requested_HIGH": 12,
                               "available_frozen_positions": len(suite),
                               "fallback": "use all available frozen positions if fewer"},
        "short_horizon_rollout": {"horizon_plies": ROLL_OUT_HORIZON,
                                  "LOW_openings": 6, "HIGH_openings": 4,
                                  "paired_colors": True, "no_heuristic_adjudication": True},
        "lockstep": ["legal_set", "move_conversion", "submit", "normalized_sfen", "side", "check"],
        "nyugyoku": "protocol exclusion",
        "node_budget_contract": "total nodes + qnodes <= max_nodes + 128 check-interval allowance",
        "source_corpus": str(ALPHASHO_ROOT / "configs" / "training" / "evaluation_positions.jsonl"),
    }
    _write(output / "b2_protocol.json", protocol)
    (output / "b2_protocol.md").write_text(
        "# Formal B2 — Bounded Evaluator Control\n\n"
        "This is a runtime-suitability replacement for the aborted legacy full-game B protocol; it is not outcome-driven.\n\n"
        f"- Certified ruleset fingerprint: `{CERTIFIED_FINGERPRINT}`\n"
        f"- Node budgets: LOW `{LOW_NODE_BUDGET}`, HIGH `{HIGH_NODE_BUDGET}`\n"
        f"- Fixed-position corpus available: `{len(suite)}`; requested LOW 16 / HIGH 12; use all available if short\n"
        f"- Paired rollout horizon: `{ROLL_OUT_HORIZON}` plies; LOW 6 openings / HIGH 4 openings\n"
        "- Required lockstep: legal set, conversion, submit, normalized SFEN, side, check\n"
        "- HORIZON_REACHED is not a draw and receives no W/L/D adjudication.\n",
        encoding="utf-8",
    )


def _b2_gate(position_summaries: dict[str, dict[str, Any]], rollout_summaries: dict[str, dict[str, Any]]) -> dict[str, bool]:
    gates: dict[str, bool] = {}
    for name, summary in position_summaries.items():
        gates[f"{name}:sample_complete"] = bool(summary["sample_complete"])
        gates[f"{name}:legal_result_failures"] = summary["legal_result_failures"] == 0
        gates[f"{name}:node_budget_failures"] = summary["node_budget_failures"] == 0
    for name, summary in rollout_summaries.items():
        gates[f"{name}:sample_complete"] = bool(summary["sample_complete"])
        gates[f"{name}:correctness_failures"] = summary["correctness_failures"] == 0
        gates[f"{name}:semantic_divergence"] = summary["semantic_divergence"] == 0
        gates[f"{name}:legal_action_failures"] = summary["legal_action_failures"] == 0
        gates[f"{name}:node_budget_failures"] = summary["node_budget_failures"] == 0
    return gates


def _manifest(output: Path) -> None:
    files = [p for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"
             and not p.name.endswith((".log", ".err", ".stdout", ".stderr"))]
    _write(output / "manifest.json", {
        "sha256": {str(p.relative_to(output)).replace("\\", "/"): _sha(p) for p in sorted(files)},
        "excluded_temporary_log_suffixes": [".log", ".err", ".stdout", ".stderr"],
    })


def run(output: Path = ROUND) -> None:
    head = _assert_clean_and_provenance()
    compiled = _assert_certified()
    suite = _load_suite()
    output.mkdir(parents=True, exist_ok=True)
    _write_protocol(output, suite)
    _write(output / "harness_provenance.json", {
        "mode": "R1.3", "harness_sha": head, "branch": "sandbox",
        "source_parent": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD^"],
                                         capture_output=True, text=True, check=True).stdout.strip(),
        "r1_1_source_sha": R1_1_SOURCE_SHA, "checkpoint_sha": CHECKPOINT_SHA,
        "baseline_sha": BASELINE_SHA, "certified_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "production_ai_changed": False, "alphasho_source_touched": False,
        "legacy_rule_monkey_patch": False,
    })
    before_old = _history_manifest(OLD_R1_2)
    before_round5 = _history_manifest(HISTORICAL)
    before_r1 = _history_manifest(HISTORICAL_R1)
    _write(output / "old_r1_2_partial_artifact_manifest.json", before_old)
    _write(output / "legacy_round5_artifact_tree_before.json", before_round5)
    _write(output / "legacy_round5_corrective_r1_tree_before.json", before_r1)
    alphasho_before = capture_repo_state()
    _write(output / "alphasho_repo_before.json", alphasho_before)
    _write(output / "ruleset_authority.json", {
        "constructor": "build_semantic_shogi_ruleset", "compiler": "compile_semantic_ruleset",
        "fingerprint": compiled.ruleset_fingerprint, "expected": CERTIFIED_FINGERPRINT,
        "asserted": compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT,
    })
    _write(output / "suite.json", {
        "source": str(ALPHASHO_ROOT / "configs" / "training" / "evaluation_positions.jsonl"),
        "positions_available": len(suite), "positions": suite,
        "b2_position_requests": {"low": 16, "high": 12},
        "b2_rollout_requests": {"low": 6, "high": 4}, "b2_horizon": ROLL_OUT_HORIZON,
        "c_max_plies": MAX_PLIES,
    })
    if not TIMING_BUDGET_FILE.exists():
        raise RuntimeError("inherited R1.2 timing budget freeze is missing")
    timing_freeze = json.loads(TIMING_BUDGET_FILE.read_text(encoding="utf-8"))
    _write(output / "inherited_timing_budget_freeze.json", timing_freeze)
    generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(
        compiled, EvaluationConfig())[0], EvaluationConfig())
    legacy = LegacyEvaluator(compiled)

    position_summaries = {
        "B2_LOW_positions": _run_position_arm(compiled, suite, output / "evaluator_control" / "b2_low_positions",
                                                LOW_NODE_BUDGET, 16, generic, legacy),
        "B2_HIGH_positions": _run_position_arm(compiled, suite, output / "evaluator_control" / "b2_high_positions",
                                                 HIGH_NODE_BUDGET, 12, generic, legacy),
    }
    rollout_summaries = {
        "B2_LOW_rollouts": _run_rollout_arm(compiled, suite, output / "evaluator_control" / "b2_low_rollouts",
                                              LOW_NODE_BUDGET, 6, generic, legacy),
        "B2_HIGH_rollouts": _run_rollout_arm(compiled, suite, output / "evaluator_control" / "b2_high_rollouts",
                                               HIGH_NODE_BUDGET, 4, generic, legacy),
    }
    gates = _b2_gate(position_summaries, rollout_summaries)
    b2_pass = all(gates.values()) and compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT
    b2_verdict = {
        "FORMAL_B_LEGACY_PROTOCOL": "ABORTED_FOR_RUNTIME",
        "FORMAL_B_LEGACY_RESULTS_VALID_FOR_CLOSURE": False,
        "FORMAL_B2_BOUNDED_REPLACEMENT": "PASS" if b2_pass else "FAIL",
        "PROTOCOL_CHANGE_REASON": "execution/runtime suitability for evaluator isolation",
        "OUTCOME_DRIVEN_PROTOCOL_CHANGE": False,
        "B2_POSITION_SAMPLE_COMPLETE": all(v["sample_complete"] for v in position_summaries.values()),
        "B2_SHORT_HORIZON_SAMPLE_COMPLETE": all(v["sample_complete"] for v in rollout_summaries.values()),
        "B2_CORRECTNESS_FAILURES": sum(v["correctness_failures"] for v in rollout_summaries.values()),
        "B2_SEMANTIC_DIVERGENCE": sum(v["semantic_divergence"] for v in rollout_summaries.values()),
        "B2_LEGAL_ACTION_FAILURES": sum(v["legal_action_failures"] for v in rollout_summaries.values()) +
                                    sum(v["legal_result_failures"] for v in position_summaries.values()),
        "position_summaries": position_summaries, "rollout_summaries": rollout_summaries,
        "gates": gates, "node_budgets": {"LOW": LOW_NODE_BUDGET, "HIGH": HIGH_NODE_BUDGET},
        "horizon_plies": ROLL_OUT_HORIZON,
    }
    _write(output / "b2_verdict.json", b2_verdict)
    if not b2_pass:
        _write(output / "diagnostic_verdict.json", {
            "ROUND5_CORRECTIVE_R1_3": "BLOCKED", "reason": "B2 hard validity gate failed",
            "b2_verdict": b2_verdict, "c_started": False,
        })
        alphasho_after = capture_repo_state()
        _write(output / "alphasho_repo_after.json", alphasho_after)
        _write(output / "closure_failure.json", {"gates": gates, "b2_verdict": b2_verdict})
        _manifest(output)
        raise RuntimeError({"kind": "ROUND5_CORRECTIVE_R1_3_BLOCKED", "gates": gates})

    # C is the already frozen Full Baseline.  It starts only after B2 PASS and
    # inherits the runtime-only A/C wall budgets; B2 never selects them.
    worker = Worker(output)
    try:
        low_seconds = float(timing_freeze["LOW_SECONDS"])
        high_seconds = float(timing_freeze["HIGH_SECONDS"])
        _run_formal_arm(compiled, worker, suite, output / "full_baseline" / "low", "C",
                         "current", generic, "seconds", low_seconds, 10, MAX_PLIES)
        _run_formal_arm(compiled, worker, suite, output / "full_baseline" / "high", "C",
                         "current", generic, "seconds", high_seconds, 6, MAX_PLIES)
    finally:
        worker.close()
    alphasho_after = capture_repo_state()
    _write(output / "alphasho_repo_after.json", alphasho_after)
    after_old = _history_manifest(OLD_R1_2)
    after_round5 = _history_manifest(HISTORICAL)
    after_r1 = _history_manifest(HISTORICAL_R1)
    immutable = before_old == after_old and before_round5 == after_round5 and before_r1 == after_r1
    if alphasho_before != alphasho_after or not immutable:
        _write(output / "closure_failure.json", {
            "ALPHASHO_READ_ONLY": alphasho_before == alphasho_after,
            "OLD_EVIDENCE_IMMUTABLE": immutable,
            "old_r1_2_unchanged": before_old == after_old,
            "old_round5_unchanged": before_round5 == after_round5,
            "old_r1_unchanged": before_r1 == after_r1,
        })
        _manifest(output)
        raise RuntimeError("R1.3 provenance closure failed")
    _write(output / "legacy_round5_artifact_tree_after.json", after_round5)
    _write(output / "legacy_round5_corrective_r1_tree_after.json", after_r1)
    _write(output / "old_r1_2_partial_artifact_manifest_after.json", after_old)

    c_summaries = {
        str(p.relative_to(output)).replace("\\", "/"): json.loads(p.read_text(encoding="utf-8"))
        for p in output.glob("full_baseline/**/summary.json")
    }
    c_paired = {
        str(p.relative_to(output)).replace("\\", "/"): json.loads(p.read_text(encoding="utf-8"))
        for p in output.glob("full_baseline/**/paired_results.json")
    }
    a_summaries = {}
    for path in (OLD_R1_2 / "search_control").glob("*/summary.json"):
        a_summaries[str(path.relative_to(ROOT)).replace("\\", "/")] = json.loads(path.read_text(encoding="utf-8"))
    _write(output / "decomposition.json", {
        "experiments": {"A": "Search Control (R1.2 immutable evidence)",
                        "B": "Formal B2 Bounded Evaluator Control", "C": "Full Baseline"},
        "A_immutable_source_summaries": a_summaries, "B2": b2_verdict,
        "C_summaries": c_summaries, "C_paired": c_paired,
        "precise_elo_claim": False,
    })
    _write(output / "performance.json", {
        "controller": "GenericChess current production Python AlphaBeta",
        "alphasho": "current mature heuristic evaluator + mature heuristic ABP",
        "worker_startup_excluded": True, "max_plies": MAX_PLIES,
        "inherited_runtime_only_c_budgets": {"LOW": timing_freeze["LOW_SECONDS"], "HIGH": timing_freeze["HIGH_SECONDS"]},
        "b2_node_budgets": {"LOW": LOW_NODE_BUDGET, "HIGH": HIGH_NODE_BUDGET},
    })
    _write(output / "final_verdict.json", {
        "ROUND5_CORRECTIVE_R1_3": "PASS", "R1_3_HARNESS_SHA": head,
        "FORMAL_B_LEGACY_PROTOCOL": "ABORTED_FOR_RUNTIME",
        "FORMAL_B2_BOUNDED_REPLACEMENT": "PASS",
        "PROTOCOL_CHANGE_REASON": "execution/runtime suitability for evaluator isolation",
        "OUTCOME_DRIVEN_PROTOCOL_CHANGE": False,
        "ALPHASHO_READ_ONLY": alphasho_before == alphasho_after,
        "OLD_EVIDENCE_IMMUTABLE": immutable,
        "B2": b2_verdict, "A_immutable_source_summaries": a_summaries,
        "C_summaries": c_summaries, "C_paired": c_paired,
        "round6_started": False,
    })
    _manifest(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROUND)
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
