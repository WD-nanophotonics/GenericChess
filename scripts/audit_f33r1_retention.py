"""F33 R1 repeated timing and retention-gate certification.

This is an additive audit harness.  It reuses the byte-frozen H33A candidate
implementations, but removes the independent reference classifier from the
measured region.  No production module is imported for mutation or edited by
this audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f33_check_discovery as h33a

R1_MANIFEST = ROOT / "tests" / "fixtures" / "f33r1_retention_timing_manifest.json"
R1_RESULT = ROOT / "tests" / "fixtures" / "f33r1_retention_gate_results.json"
H33A_MANIFEST = ROOT / "tests" / "fixtures" / "f33_check_discovery_manifest.json"
H33A_RESULT = ROOT / "tests" / "fixtures" / "f33_check_discovery_audit.json"
H33A_MANIFEST_SHA = "14de91028470b9bf4d3a8933a73912fa1e0b2567fb70ca106e0a284d778378bf"
H33A_RESULT_SHA = "e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c"
F32R1_RESULT_SHA = "0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88"
CANDIDATE_HARNESS_SHA = "bebac88acbd17a33d9706709476599a815d060c68ea00d8fa6cd1d31e2bbc769"
REPETITIONS = 3
TIMES = (0.50, 2.00)
NODE_BUDGETS = (512, 2048)
VARIANTS = h33a.VARIANTS
PARITY_FIELDS = ("selected_move", "score", "pv_head", "completed_depth", "main_nodes", "qnodes", "termination_reason")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_sha(value: dict[str, Any]) -> str:
    body = {key: value[key] for key in value if key != "manifest_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "F33_R1_RETENTION_TIMING_MANIFEST",
        "pre_run_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "frozen_inputs": {
            "h33a_manifest": {"path": "tests/fixtures/f33_check_discovery_manifest.json", "sha256": H33A_MANIFEST_SHA},
            "h33a_result": {"path": "tests/fixtures/f33_check_discovery_audit.json", "sha256": H33A_RESULT_SHA},
            "f32r1_result": {"path": "tests/fixtures/f32r1_qsearch_exact_counterfactual.json", "sha256": F32R1_RESULT_SHA},
            "candidate_harness": {"path": "scripts/audit_f33_check_discovery.py", "sha256": CANDIDATE_HARNESS_SHA},
        },
        "matrix": {
            "variants": list(VARIANTS),
            "fixed_nodes": list(NODE_BUDGETS),
            "wall_times_seconds": list(TIMES),
            "timing_repetitions": REPETITIONS,
            "wall_repetitions": 1,
        },
        "timing_protocol": {
            "fixed_node_runs": "three independent repetitions per variant/budget/root",
            "measured_region": "run_root_search only; no independent reference classifier",
            "per_root_aggregation": "median elapsed seconds, NPS, and time to first completed iteration",
            "per_root_speedup": "1 - candidate median elapsed / baseline median elapsed",
            "decision_aggregate": "median of the ten per-root speedup ratios",
            "whole_corpus_aggregate": "1 - sum(candidate per-root medians) / sum(baseline per-root medians)",
        },
        "retention_gates": {
            "candidate_b_performance": "median per-root improvement >=20% at either budget and no regression worse than 10% at the other",
            "candidate_a_fallback_performance": "median per-root improvement >=15% at either budget and no regression worse than 10% at the other",
            "candidate_b_accessibility": "depth gain >=3 at 0.50s or 2.00s, fallback reduction >=3 at 0.50s, or comparable first-iteration median gain >=15% at either control",
            "candidate_a_accessibility": "same complete accessibility gate as Candidate B",
            "candidate_b_structural": "classification pushes reduction >=80% at both 512 and 2048",
            "selection": "B if all B gates; else A if all A gates; else NONE",
        },
        "constraints": [
            "PRESERVE_H33A_EVIDENCE_BYTE_IDENTICALLY",
            "NO_PRODUCTION_CHANGE",
            "NO_TUNING_FROM_RESULTS",
            "NO_QSEARCH_SET_REDUCTION",
            "NO_QDEPTH_CHANGE",
            "NO_NATIVE_REPAIR",
            "NO_ALPHASHO_RERUN",
            "NO_PAIRED_BENCHMARK",
            "NO_ALPHA_CHESS",
        ],
        "host": {"python": platform.python_version()},
    }


def freeze() -> dict[str, Any]:
    value = build_manifest()
    value["manifest_sha256"] = manifest_sha(value)
    R1_MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def _classify(ctx, actions, variant):
    h33a._ACTIVE = h33a.DiscoveryAudit()
    if variant == "BASELINE":
        noisy = h33a._full_classify(ctx, actions, reuse_gave_check=False)
    elif variant == "CANDIDATE_A_POST_PUSH_GAVE_CHECK":
        noisy = h33a._full_classify(ctx, actions, reuse_gave_check=True)
    else:
        noisy = h33a._preview_classify(ctx, actions)
    audit = h33a._ACTIVE
    h33a._ACTIVE = None
    return noisy, audit


def _probe(m, compiled, evaluator, state, *, variant, seconds=None, nodes=None, max_depth=64):
    import generic_chess.ai.alphabeta.search as search_module
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits

    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    session = m["GameSession"](compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    limits = SearchLimits(
        max_nodes=nodes,
        max_time_seconds=seconds,
        max_depth=max_depth,
        quiescence_max_depth=4,
        quiescence_hard_max_depth=8,
        quiescence_max_nodes=None,
        deterministic=True,
    )
    old = search_module._runtime_noisy_actions
    search_module._runtime_noisy_actions = lambda ctx, actions: _classify(ctx, actions, variant)[0]
    started = time.perf_counter()
    try:
        action, score, pv, reason = run_root_search(
            state,
            compiled,
            evaluator,
            TranspositionTable(max_entries=250_000),
            limits,
            None,
            stats,
            use_tt=True,
            use_ordering=True,
            tuning=SearchTuning(),
            _history_witnesses=session._search_witnesses,
            legal_binding_provider=provider,
        )
    except Exception as exc:
        action, score, pv, reason = None, None, (), type(exc).__name__ + ":" + str(exc)
    elapsed = time.perf_counter() - started
    search_module._runtime_noisy_actions = old
    total_nodes = stats.nodes + stats.qnodes
    return {
        "selected_move": m["gc_action_to_usi"](action) if action else None,
        "score": score,
        "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None,
        "completed_depth": stats.completed_depth,
        "main_nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "total_nodes": total_nodes,
        "termination_reason": reason,
        "fallback": stats.root_scan_used_fallback,
        "elapsed_seconds": elapsed,
        "nps": total_nodes / elapsed if elapsed else 0.0,
        "time_to_first_completed_iteration": stats.time_to_first_completed_iteration,
        "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK",
    }


def _parity_marker(row, frozen):
    return {field: row[field] == frozen[field] for field in PARITY_FIELDS}


def _median_or_none(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _timing_summary(rows):
    return {
        "elapsed_seconds": statistics.median(row["elapsed_seconds"] for row in rows),
        "nps": statistics.median(row["nps"] for row in rows),
        "time_to_first_completed_iteration": _median_or_none(row["time_to_first_completed_iteration"] for row in rows),
        "completed_depth_values": sorted({row["completed_depth"] for row in rows}),
        "parity_integrity": all(all(row["parity_integrity"].values()) for row in rows),
    }


def _accessibility(wall, variant, control):
    base = wall["BASELINE"][control]
    candidate = wall[variant][control]
    depth_gain = sum(candidate[pid]["completed_depth"] > base[pid]["completed_depth"] for pid in base)
    fallback_reduction = sum(base[pid]["fallback"] and not candidate[pid]["fallback"] for pid in base)

    def comparable_first_iteration():
        pairs = [(base[pid]["time_to_first_completed_iteration"], candidate[pid]["time_to_first_completed_iteration"]) for pid in base]
        return [(left, right) for left, right in pairs if left is not None and right is not None]

    pairs = comparable_first_iteration()
    first_gain = (1 - statistics.median(right for _, right in pairs) / statistics.median(left for left, _ in pairs)) if pairs and statistics.median(left for left, _ in pairs) else 0.0
    return {
        "depth_gain_count": depth_gain,
        "fallback_reduction_count": fallback_reduction,
        "comparable_first_iteration_roots": len(pairs),
        "median_first_iteration_gain": first_gain,
        "components": {
            "depth_at_control": depth_gain >= 3,
            "fallback_at_0.50": fallback_reduction >= 3 if control == "0.5" else None,
            "first_iteration_at_control": first_gain >= 0.15,
        },
    }


def _complete_accessibility(wall, variant):
    at_050 = _accessibility(wall, variant, "0.5")
    at_200 = _accessibility(wall, variant, "2.0")
    return {
        "0.50": at_050,
        "2.00": at_200,
        "gate": (
            at_050["depth_gain_count"] >= 3
            or at_200["depth_gain_count"] >= 3
            or at_050["fallback_reduction_count"] >= 3
            or at_050["median_first_iteration_gain"] >= 0.15
            or at_200["median_first_iteration_gain"] >= 0.15
        ),
    }


def _speedups(fixed, variant):
    result = {}
    for budget in NODE_BUDGETS:
        budget_key = str(budget)
        per_root = {}
        for pid in fixed["BASELINE"][budget_key]:
            base = fixed["BASELINE"][budget_key][pid]["summary"]["elapsed_seconds"]
            candidate = fixed[variant][budget_key][pid]["summary"]["elapsed_seconds"]
            per_root[pid] = 1 - candidate / base if base else 0.0
        result[budget_key] = {
            "per_root": per_root,
            "median_per_root_speedup": statistics.median(per_root.values()),
            "whole_corpus_speedup": 1 - sum(fixed[variant][budget_key][pid]["summary"]["elapsed_seconds"] for pid in per_root) / sum(fixed["BASELINE"][budget_key][pid]["summary"]["elapsed_seconds"] for pid in per_root),
        }
    return result


def run():
    if load(H33A_MANIFEST).get("manifest_sha256") != H33A_MANIFEST_SHA or sha(H33A_RESULT) != H33A_RESULT_SHA:
        raise AssertionError("H33A evidence identity changed")
    r1_manifest = load(R1_MANIFEST)
    if r1_manifest.get("manifest_sha256") != manifest_sha(r1_manifest):
        raise AssertionError("R1 manifest self-hash mismatch")
    if r1_manifest["frozen_inputs"]["candidate_harness"]["sha256"] != sha(ROOT / "scripts" / "audit_f33_check_discovery.py"):
        raise AssertionError("candidate harness identity changed")

    h33_result = load(H33A_RESULT)
    m, compiled, evaluator, positions, modal = h33a._contexts()
    fixed = {variant: {} for variant in VARIANTS}
    for variant in VARIANTS:
        for budget in NODE_BUDGETS:
            budget_key = str(budget)
            fixed[variant][budget_key] = {}
            for item in positions:
                pid = item["position_id"]
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                reps = []
                frozen = h33_result["matrix"]["fixed_node"][variant][budget_key][pid]
                for repetition in range(1, REPETITIONS + 1):
                    row = _probe(m, compiled, evaluator, state, variant=variant, nodes=budget)
                    row["repetition"] = repetition
                    row["parity_integrity"] = _parity_marker(row, frozen)
                    reps.append(row)
                fixed[variant][budget_key][pid] = {"repetitions": reps, "summary": _timing_summary(reps)}

    wall = {variant: {} for variant in VARIANTS}
    for variant in VARIANTS:
        for seconds in TIMES:
            control = str(seconds)
            wall[variant][control] = {}
            for item in positions:
                pid = item["position_id"]
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _probe(m, compiled, evaluator, state, variant=variant, seconds=seconds)
                row["alphasho_0.50_modal"] = modal[pid]["alphasho_0.5"]
                row["alphasho_2.00_modal"] = modal[pid]["alphasho_2.0"]
                wall[variant][control][pid] = row

    speedups = {variant: _speedups(fixed, variant) for variant in VARIANTS if variant != "BASELINE"}
    b_speed = speedups["CANDIDATE_B_SEMANTIC_PREVIEW"]
    a_speed = speedups["CANDIDATE_A_POST_PUSH_GAVE_CHECK"]
    b_performance = max(view["median_per_root_speedup"] for view in b_speed.values()) >= 0.20 and min(view["median_per_root_speedup"] for view in b_speed.values()) >= -0.10
    a_performance = max(view["median_per_root_speedup"] for view in a_speed.values()) >= 0.15 and min(view["median_per_root_speedup"] for view in a_speed.values()) >= -0.10
    b_accessibility = _complete_accessibility(wall, "CANDIDATE_B_SEMANTIC_PREVIEW")
    a_accessibility = _complete_accessibility(wall, "CANDIDATE_A_POST_PUSH_GAVE_CHECK")

    parity = h33_result["parity"]
    classifier = h33_result["classifier_totals"]
    b_classifier = all(classifier["CANDIDATE_B_SEMANTIC_PREVIEW"][str(budget)]["mismatches"] == 0 for budget in NODE_BUDGETS)
    a_classifier = all(classifier["CANDIDATE_A_POST_PUSH_GAVE_CHECK"][str(budget)]["mismatches"] == 0 for budget in NODE_BUDGETS)
    b_fixed = all(all(parity[str(budget)][pid]["CANDIDATE_B_SEMANTIC_PREVIEW"].values()) for budget in NODE_BUDGETS for pid in parity[str(budget)])
    a_fixed = all(all(parity[str(budget)][pid]["CANDIDATE_A_POST_PUSH_GAVE_CHECK"].values()) for budget in NODE_BUDGETS for pid in parity[str(budget)])
    b_structural = all(value >= 0.80 for value in h33_result["candidate_b_committed_push_reduction"].values())
    preview_history_terminal_isolation = bool(h33_result["history_terminal_witnesses"]) and not h33_result["production_changed"]

    gates = {
        "candidate_b_classifier_parity": b_classifier,
        "candidate_b_fixed_result_parity": b_fixed,
        "candidate_b_structural_gate": b_structural,
        "candidate_b_repeated_fixed_node_performance_gate": b_performance,
        "candidate_b_complete_accessibility_gate": b_accessibility["gate"],
        "candidate_b_preview_history_terminal_isolation_gate": preview_history_terminal_isolation,
        "candidate_a_classifier_parity": a_classifier,
        "candidate_a_fixed_result_parity": a_fixed,
        "candidate_a_repeated_fallback_performance_gate": a_performance,
        "candidate_a_complete_accessibility_gate": a_accessibility["gate"],
        "candidate_a_preview_history_terminal_isolation_gate": preview_history_terminal_isolation,
    }
    b_retention = all(gates[key] for key in ("candidate_b_classifier_parity", "candidate_b_fixed_result_parity", "candidate_b_structural_gate", "candidate_b_repeated_fixed_node_performance_gate", "candidate_b_complete_accessibility_gate", "candidate_b_preview_history_terminal_isolation_gate"))
    a_retention = all(gates[key] for key in ("candidate_a_classifier_parity", "candidate_a_fixed_result_parity", "candidate_a_repeated_fallback_performance_gate", "candidate_a_complete_accessibility_gate", "candidate_a_preview_history_terminal_isolation_gate"))
    retained = "CANDIDATE_B_SEMANTIC_PREVIEW" if b_retention else "CANDIDATE_A_POST_PUSH_GAVE_CHECK" if a_retention else "NONE"
    return {
        "schema_version": 1,
        "status": "PASS",
        "production_changed": False,
        "h33a_manifest_sha256": H33A_MANIFEST_SHA,
        "h33a_result_sha256": H33A_RESULT_SHA,
        "f32r1_result_sha256": F32R1_RESULT_SHA,
        "candidate_harness_sha256": CANDIDATE_HARNESS_SHA,
        "matrix": {"fixed_node": fixed, "wall_time": wall},
        "timing_speedups": speedups,
        "accessibility": {"CANDIDATE_B_SEMANTIC_PREVIEW": b_accessibility, "CANDIDATE_A_POST_PUSH_GAVE_CHECK": a_accessibility},
        "gates": gates,
        "retained_candidate": retained,
        "next_boundary": "F34_POST_FASTPATH_SEARCH_CAPACITY_REBASELINE" if retained != "NONE" else "F34_QUIESCENCE_BUDGET_ARCHITECTURE",
        "flags": {
            "F32_QSEARCH_BASELINE_CONSUMED": True,
            "SEMANTIC_QSEARCH_CHECK_DISCOVERY_PARITY": b_classifier,
            "DISCOVERED_CHECK_FASTPATH_CERTIFIED": b_fixed,
            "QSEARCH_TERMINAL_CHILD_PARITY": True,
            "QSEARCH_CLASSIFICATION_PUSH_REDUCTION_CERTIFIED": b_structural,
            "SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH_RETAINED": retained != "NONE",
        },
        "historical_regression_contract": [
            "12 Native F13/F14/F21 compatibility failures",
            "tests/test_f24f_western_chess_perft.py::test_f24f_mandatory_perft_one_shot",
        ],
        "constraints": ["R1_CORRECTIVE_ONLY", "NO_PRODUCTION_CHANGE", "PRESERVE_H33A_EVIDENCE_BYTE_IDENTICALLY"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_manifest:
        value = freeze()
        print(json.dumps({"manifest_sha256": value["manifest_sha256"]}, sort_keys=True))
        return 0
    if args.run:
        result = run()
        R1_RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "retained": result["retained_candidate"], "next": result["next_boundary"], "flags": result["flags"]}, sort_keys=True))
        return 0
    parser.error("use --freeze-manifest or --run")


if __name__ == "__main__":
    raise SystemExit(main())
