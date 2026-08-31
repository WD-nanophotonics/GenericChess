"""F25 Standard Shogi product and dual-standard search baseline audit."""

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
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.position import GameState
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import canonical_json, compute_fingerprint
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession

from generic_chess.learning.shogi_rules import sfen_to_gc_state


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR_PATH = ROOT / "tests/fixtures/f25_standard_shogi_position_descriptors.json"
F24H_FIXTURE = ROOT / "tests/fixtures/f24h_western_search_baseline.json"
F24H_MANIFEST_SHA = "55b4e4c5253fae932bf201675b93636c80b68b7335a581711d2d475d4c4aa55b"
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
NODE_BUDGETS = (128, 512, 2048)
TIME_BUDGETS = (0.25, 1.0)
REPETITIONS = 3
_NATIVE_PROVIDER = None


def _git_sha():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _descriptors():
    payload = json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))
    if payload["source_commit"] != F22_COMMIT or len(payload["positions"]) != 10:
        raise AssertionError("F25 descriptor provenance/count mismatch")
    return payload


def _session_for(compiled, state):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    return session


def _state_for(compiled, sfen):
    # This adapter is audit-only; product code has no SFEN dependency.
    return sfen_to_gc_state(compiled, sfen)


def _metrics(decision):
    elapsed = decision.elapsed_seconds
    total = decision.nodes + decision.qnodes
    return {
        "action": action_to_dict(decision.action),
        "visible_action": visible_action_alias(decision.action) if decision.action else None,
        "score": decision.score,
        "pv": [action_to_dict(a) for a in decision.principal_variation],
        "pv_visible": [visible_action_alias(a) for a in decision.principal_variation],
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
        "qnode_fraction": decision.qnodes / total if total else 0.0,
        "capture_qactions": decision.capture_qactions,
        "promotion_qactions": decision.promotion_qactions,
        "checking_move_qactions": decision.checking_move_qactions,
        "checking_drop_qactions": decision.checking_drop_qactions,
        "termination_reason": decision.termination_reason,
        "provider_mode": "NATIVE" if _NATIVE_PROVIDER else "PYTHON_AUTHORITY_FALLBACK",
    }


def _player(compiled):
    return AlphaBetaPlayer(
        compiled, evaluation_config=EvaluationConfig(), use_disk_cache=False,
        use_tt=True, use_ordering=True, use_native_semantic_legality=True,
        tuning=SearchTuning(),
    )


def _run_once(compiled, state, limits):
    session = _session_for(compiled, state)
    before = session.state
    decision = _player(compiled).choose_action(session, limits)
    if decision.action not in session.legal_actions():
        raise AssertionError("AlphaBeta returned an illegal Standard Shogi action")
    if session.state != before:
        raise AssertionError("search mutated the Standard Shogi root")
    return _metrics(decision)


def _manifest(compiled, descriptors, commit_sha):
    config = EvaluationConfig()
    tuning = SearchTuning()
    return {
        "ruleset_fingerprint": compute_fingerprint(build_standard_shogi_ruleset()),
        "position_descriptor_sha256": hashlib.sha256(DESCRIPTOR_PATH.read_bytes()).hexdigest(),
        "positions": descriptors["positions"],
        "f22_source_commit": F22_COMMIT,
        "generic_chess_commit_sha": commit_sha,
        "python": platform.python_version(),
        "evaluation_config": asdict(config),
        "evaluation_config_hash": config_hash(config),
        "search_tuning": asdict(tuning),
        "tt": {"use_tt": True, "max_entries": 250000, "fresh_per_run": True},
        "ordering": {"use_ordering": True},
        "qsearch": {"quiescence_max_depth": 4, "quiescence_hard_max_depth": 8},
        "native_provider_policy": {
            "requested": True,
            "actual": "NATIVE" if _NATIVE_PROVIDER else "PYTHON_AUTHORITY_FALLBACK",
        },
        "fixed_node_budgets": list(NODE_BUDGETS),
        "fixed_time_budgets_seconds": list(TIME_BUDGETS),
        "repetitions": REPETITIONS,
        "western_f24h_manifest_sha256": F24H_MANIFEST_SHA,
        "western_fixture": str(F24H_FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "western_fixture_sha256": hashlib.sha256(F24H_FIXTURE.read_bytes()).hexdigest(),
        "compiled_ruleset_fingerprint": compiled.ruleset_fingerprint,
    }


def run_baseline(commit_sha=None):
    global _NATIVE_PROVIDER
    descriptors = _descriptors()
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    _NATIVE_PROVIDER = NativeSemanticLegalityProvider.try_create(compiled)
    manifest = _manifest(compiled, commit_sha or _git_sha())
    manifest_sha = hashlib.sha256(canonical_json(manifest).encode()).hexdigest()
    fixed_node = []
    for item in descriptors["positions"]:
        state = _state_for(compiled, item["sfen"])
        for budget in NODE_BUDGETS:
            limits = SearchLimits(max_nodes=budget, max_depth=8, quiescence_max_depth=4,
                                  quiescence_hard_max_depth=8, deterministic=True)
            repeats = [_run_once(compiled, state, limits) for _ in range(2)]
            keys = ("action", "score", "pv", "termination_reason", "completed_depth")
            if any(tuple(row[key] for key in keys) != tuple(repeats[0][key] for key in keys)
                   for row in repeats[1:]):
                raise AssertionError({"position_id": item["position_id"], "budget": budget, "repeats": repeats})
            fixed_node.append({
                "position_id": item["position_id"], "budget": budget,
                "repeats": repeats, "deterministic": True,
                "overshoot": max(row["total_nodes"] for row in repeats) - budget,
            })

    fixed_time = []
    fixed_time_summaries = []
    for item in descriptors["positions"]:
        state = _state_for(compiled, item["sfen"])
        for seconds in TIME_BUDGETS:
            limits = SearchLimits(max_time_seconds=seconds, max_depth=64,
                                  quiescence_max_depth=4, quiescence_hard_max_depth=8,
                                  deterministic=True)
            repeats = [_run_once(compiled, state, limits) for _ in range(REPETITIONS)]
            fixed_time.append({"position_id": item["position_id"], "seconds": seconds, "repeats": repeats})
            fixed_time_summaries.append({
                "position_id": item["position_id"], "seconds": seconds,
                "median_total_nodes": statistics.median(r["total_nodes"] for r in repeats),
                "median_nodes_per_second": statistics.median(r["nodes_per_second"] for r in repeats),
                "median_completed_depth": statistics.median(r["completed_depth"] for r in repeats),
                "median_evaluator_wall_fraction": statistics.median(r["evaluator_wall_fraction"] for r in repeats),
                "median_legal_generation_wall_fraction": statistics.median(r["legal_generation_wall_fraction"] for r in repeats),
                "median_ordering_wall_fraction": statistics.median(r["ordering_wall_fraction"] for r in repeats),
                "median_qnode_fraction": statistics.median(r["qnode_fraction"] for r in repeats),
            })

    return {
        "status": "PASS", "manifest": manifest, "manifest_sha256": manifest_sha,
        "fixed_node": fixed_node, "fixed_time": fixed_time,
        "fixed_time_summaries": fixed_time_summaries,
        "standard_shogi_product_surface_available": True,
        "standard_shogi_search_baseline_frozen": True,
        "standard_shogi_nyugyoku_supported": False,
        "standard_shogi_full_rule_product_ready": False,
        "dual_standard_internal_baseline": True,
        "next_boundary": "F26_SHOGI_DECLARATION_WIN_SEMANTIC_FOUNDATION",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--commit-sha")
    args = parser.parse_args(argv)
    result = run_baseline(args.commit_sha)
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(output, encoding="utf-8")
        print(f"F25_STATUS={result['status']}")
        print(f"F25_MANIFEST_SHA256={result['manifest_sha256']}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

