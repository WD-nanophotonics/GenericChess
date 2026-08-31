"""F24H Western product and AlphaBeta reference-baseline audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig, config_hash
from generic_chess.ai.limits import SearchLimits
from generic_chess.cli.play import visible_action_alias
from generic_chess.core.identity import position_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.rules.schema import canonical_json, compute_fingerprint
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.position import GameState

from scripts.audit_f24g_canonical_western_perft import (
    CANONICAL_CORPUS,
    perft,
    position_from_fen,
    root_divide,
)


ROOT = Path(__file__).resolve().parents[1]
FIXED_NODE_BUDGETS = (128, 512, 2048)
FIXED_TIME_BUDGETS = (0.25, 1.0)
REPETITIONS = 3


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _session_for(compiled, position):
    engine = semantic_engine_for(compiled)
    if engine is None:
        raise RuntimeError("F24H baseline requires the semantic Western engine")
    key = position_identity_key(position, compiled)
    status = engine.terminal_result(position, 0, ((key, 1),))
    session = GameSession(compiled)
    session._state = GameState(
        position=position,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=status,
    )
    session._search_history_witnesses = (position,)
    return session


def _action_dict(action):
    from generic_chess.core.actions import action_to_dict

    return action_to_dict(action) if action is not None else None


def _decision_metrics(decision, elapsed=None):
    elapsed = decision.elapsed_seconds if elapsed is None else elapsed
    total = decision.nodes + decision.qnodes
    return {
        "action": _action_dict(decision.action),
        "visible_action": visible_action_alias(decision.action) if decision.action else None,
        "score": decision.score,
        "pv": [_action_dict(action) for action in decision.principal_variation],
        "pv_visible": [visible_action_alias(action) for action in decision.principal_variation],
        "completed_depth": decision.completed_depth,
        "selective_depth": decision.selective_depth,
        "main_nodes": decision.nodes,
        "qnodes": decision.qnodes,
        "total_nodes": total,
        "elapsed_seconds": elapsed,
        "nodes_per_second": total / elapsed if elapsed else None,
        "tt_probes": decision.tt_probes,
        "tt_hits": decision.tt_hits,
        "tt_cutoffs": decision.tt_cutoffs,
        "beta_cutoffs": decision.beta_cutoffs,
        "evaluation_calls": decision.evaluation_calls,
        "evaluation_seconds": decision.evaluation_seconds,
        "evaluator_wall_fraction": decision.evaluation_seconds / elapsed if elapsed else 0.0,
        "legal_generation_calls": decision.legal_generation_calls,
        "legal_generation_seconds": decision.legal_generation_seconds,
        "legal_generation_wall_fraction": decision.legal_generation_seconds / elapsed if elapsed else 0.0,
        "ordering_calls": decision.ordering_calls,
        "ordering_seconds": decision.ordering_seconds,
        "ordering_wall_fraction": decision.ordering_seconds / elapsed if elapsed else 0.0,
        "capture_qactions": decision.capture_qactions,
        "promotion_qactions": decision.promotion_qactions,
        "checking_move_qactions": decision.checking_move_qactions,
        "checking_drop_qactions": decision.checking_drop_qactions,
        "termination_reason": decision.termination_reason,
        "provider_mode": "NATIVE" if decision is not None and _NATIVE_PROVIDER else "PYTHON_AUTHORITY_FALLBACK",
    }


def _player(compiled):
    return AlphaBetaPlayer(
        compiled,
        evaluation_config=EvaluationConfig(),
        use_disk_cache=False,
        use_tt=True,
        use_ordering=True,
        use_native_semantic_legality=True,
        tuning=SearchTuning(),
    )


def _run_once(compiled, position, limits):
    session = _session_for(compiled, position)
    before = session.state
    decision = _player(compiled).choose_action(session, limits)
    if decision.action not in session.legal_actions():
        raise AssertionError("AlphaBeta returned an illegal action")
    if session.state != before:
        raise AssertionError("search mutated the input session state")
    return _decision_metrics(decision)


def canonical_perft(compiled):
    engine = semantic_engine_for(compiled)
    rows = []
    for label, fen, expected in CANONICAL_CORPUS:
        position = position_from_fen(fen, compiled)
        for depth, wanted in enumerate(expected, 1):
            started = time.perf_counter()
            actual = perft(engine, position, depth)
            elapsed = time.perf_counter() - started
            row = {
                "label": label, "depth": depth, "expected": wanted,
                "actual": actual, "wall_seconds": elapsed,
                "nodes_per_second": actual / elapsed if elapsed else None,
            }
            rows.append(row)
            if actual != wanted:
                divide = root_divide(engine, position, depth - 1)
                payload = json.dumps(sorted(divide), separators=(",", ":"))
                raise AssertionError({
                    "status": "FIRST_CANONICAL_MISMATCH",
                    "row": row,
                    "divide": sorted(divide),
                    "divide_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                })
    return rows


def _manifest(compiled, commit_sha):
    config = EvaluationConfig()
    tuning = SearchTuning()
    return {
        "ruleset_fingerprint": compute_fingerprint(build_western_chess_ruleset()),
        "compiled_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "fen_corpus": [
            {"label": label, "fen": fen, "expected": list(expected)}
            for label, fen, expected in CANONICAL_CORPUS
        ],
        "fixed_node_budgets": list(FIXED_NODE_BUDGETS),
        "fixed_time_budgets_seconds": list(FIXED_TIME_BUDGETS),
        "repetitions": REPETITIONS,
        "evaluation_config": asdict(config),
        "evaluation_config_hash": config_hash(config),
        "search_tuning": asdict(tuning),
        "tt": {"use_tt": True, "max_entries": 250000, "fresh_per_run": True},
        "ordering": {"use_ordering": True},
        "qsearch": {
            "quiescence_max_depth": 4,
            "quiescence_hard_max_depth": 8,
        },
        "native_provider_policy": {
            "requested": True,
            "actual": "NATIVE" if _NATIVE_PROVIDER else "PYTHON_AUTHORITY_FALLBACK",
            "reason": "certified subject_ref shape is intentionally unsupported by Native",
        },
        "python": platform.python_version(),
        "generic_chess_commit_sha": commit_sha,
    }


def run_baseline(commit_sha=None):
    global _NATIVE_PROVIDER
    ruleset = build_western_chess_ruleset()
    compiled = compile_ruleset_for_execution(ruleset)
    _NATIVE_PROVIDER = NativeSemanticLegalityProvider.try_create(compiled)
    manifest = _manifest(compiled, commit_sha or _git_sha())
    manifest_sha = hashlib.sha256(canonical_json(manifest).encode()).hexdigest()
    perft_rows = canonical_perft(compiled)

    fixed_node_rows = []
    for label, fen, _expected in CANONICAL_CORPUS:
        position = position_from_fen(fen, compiled)
        for budget in FIXED_NODE_BUDGETS:
            limits = SearchLimits(
                max_nodes=budget, max_depth=8,
                quiescence_max_depth=4, quiescence_hard_max_depth=8,
                deterministic=True,
            )
            repeats = [_run_once(compiled, position, limits) for _ in range(2)]
            signature_keys = ("action", "score", "pv", "termination_reason", "completed_depth")
            if any(
                tuple(row[key] for key in signature_keys)
                != tuple(repeats[0][key] for key in signature_keys)
                for row in repeats[1:]
            ):
                raise AssertionError({"label": label, "budget": budget, "repeats": repeats})
            fixed_node_rows.append({
                "label": label, "budget": budget, "repeats": repeats,
                "deterministic": True,
                "overshoot": max(row["total_nodes"] for row in repeats) - budget,
            })

    fixed_time_rows = []
    fixed_time_summaries = []
    for label, fen, _expected in CANONICAL_CORPUS:
        position = position_from_fen(fen, compiled)
        for seconds in FIXED_TIME_BUDGETS:
            limits = SearchLimits(
                max_time_seconds=seconds, max_depth=64,
                quiescence_max_depth=4, quiescence_hard_max_depth=8,
                deterministic=True,
            )
            repeats = [_run_once(compiled, position, limits) for _ in range(REPETITIONS)]
            fixed_time_rows.append({"label": label, "seconds": seconds, "repeats": repeats})
            fixed_time_summaries.append({
                "label": label,
                "seconds": seconds,
                "median_total_nodes": statistics.median(row["total_nodes"] for row in repeats),
                "median_nodes_per_second": statistics.median(row["nodes_per_second"] for row in repeats),
                "median_completed_depth": statistics.median(row["completed_depth"] for row in repeats),
                "median_evaluator_wall_fraction": statistics.median(row["evaluator_wall_fraction"] for row in repeats),
                "median_legal_generation_wall_fraction": statistics.median(row["legal_generation_wall_fraction"] for row in repeats),
                "median_ordering_wall_fraction": statistics.median(row["ordering_wall_fraction"] for row in repeats),
            })

    return {
        "status": "PASS",
        "manifest": manifest,
        "manifest_sha256": manifest_sha,
        "canonical_perft": perft_rows,
        "fixed_node": fixed_node_rows,
        "fixed_time": fixed_time_rows,
        "fixed_time_summaries": fixed_time_summaries,
        "western_chess_product_ready_baseline": True,
        "next_boundary": "F25_STANDARD_SHOGI_PRODUCTIZATION_AND_DUAL_STANDARD_SEARCH_BASELINE",
    }


_NATIVE_PROVIDER = None


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--commit-sha")
    args = parser.parse_args(argv)
    result = run_baseline(args.commit_sha)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
        print(f"F24H_STATUS={result['status']}")
        print(f"F24H_MANIFEST_SHA256={result['manifest_sha256']}")
        print(f"F24H_WESTERN_CHESS_PRODUCT_READY_BASELINE={str(result['western_chess_product_ready_baseline']).lower()}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
