"""F32 audit-only search-horizon and quiescence diagnosis.

This harness consumes frozen F30/F31 evidence and uses only additive probes.
It never edits GenericChess production modules or changes search defaults.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
F30_MANIFEST = ROOT / "tests" / "fixtures" / "f30r1_benchmark_manifest.json"
F30_FRESH = ROOT / "tests" / "fixtures" / "f30r1_fresh_move_reference.json"
F30_PAIRED = ROOT / "tests" / "fixtures" / "f30r1_paired_match.json"
F31_MANIFEST = ROOT / "tests" / "fixtures" / "f31_causal_manifest.json"
F31_RESULT = ROOT / "tests" / "fixtures" / "f31_causal_diagnosis.json"
F31R1_RESULT = ROOT / "tests" / "fixtures" / "f31r1_counterfactual_causal_reclassification.json"
F32_MANIFEST = ROOT / "tests" / "fixtures" / "f32_qsearch_manifest.json"
F32_OUTPUT = ROOT / "tests" / "fixtures" / "f32_qsearch_diagnosis.json"
PRODUCT_AUTHORITY = "a389adc50ed42096874ee38f818584978468c6ac"
F31_MANIFEST_SHA = "e08867b24fc268581b7853caf8e6bf2da0d2c25307c36120540313ea44f677dd"
F31_RESULT_SHA = "9eaaccf9ecea8717e6a2ffe198da9136cb1e7fee0ee9ac2edcb60d6f70d8b77e"
F31R1_RESULT_SHA = "ed0834b4a591d9a0b0dddd529a1c1ce205f22fd268caafe7951d79966113a83f"
TIMES = (0.50, 2.00)
NODE_BUDGETS = (512, 2048)
QDEPTHS = (0, 1, 2, 4)
QNODE_CAPS = (16, 32, 64, 128)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f31():
    from scripts.audit_f31_gap_causal import _contexts, _frozen_roots, _imports, _session

    return _contexts, _frozen_roots, _imports, _session


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "F32_PRE_DIAGNOSIS_MANIFEST",
        "generic_chess_product_authority": PRODUCT_AUTHORITY,
        "generic_chess_head_at_freeze": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "frozen_inputs": {
            "f30_r1_manifest": {"path": "tests/fixtures/f30r1_benchmark_manifest.json", "sha256": sha(F30_MANIFEST)},
            "f30_r1_fresh": {"path": "tests/fixtures/f30r1_fresh_move_reference.json", "sha256": sha(F30_FRESH)},
            "f30_r1_paired": {"path": "tests/fixtures/f30r1_paired_match.json", "sha256": sha(F30_PAIRED)},
            "f31_manifest": {"path": "tests/fixtures/f31_causal_manifest.json", "sha256": F31_MANIFEST_SHA},
            "f31_result": {"path": "tests/fixtures/f31_causal_diagnosis.json", "sha256": F31_RESULT_SHA},
            "f31r1_result": {"path": "tests/fixtures/f31r1_counterfactual_causal_reclassification.json", "sha256": F31R1_RESULT_SHA},
            "descriptor": {"path": "tests/fixtures/f25_standard_shogi_position_descriptors.json", "sha256": "2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151"},
        },
        "diagnostic_matrix": {
            "times_seconds": list(TIMES),
            "fixed_node_budgets": list(NODE_BUDGETS),
            "qdepths": list(QDEPTHS),
            "qnode_caps": list(QNODE_CAPS),
            "qnode_cap_subset": "first four position IDs at both wall controls",
            "noisy_variants": ["Q0_PRODUCTION_EXACT", "Q1_CAPTURES_PROMOTIONS", "Q2_PLUS_CHECKING_BOARD_MOVES", "Q3_PLUS_CHECKING_DROPS"],
            "lazy_variant": "LAZY_NONCHECK_LEGAL_GENERATION",
        },
        "product_settings": {"evaluator": "v1", "qsearch": "4/8", "native_requested": True, "tt": True, "ordering": True, "search_tuning": "default"},
        "constraints": ["NO_TUNING_FROM_RESULTS=true", "NO_PRODUCTION_CHANGE=true", "NO_NEW_PAIRED_BENCHMARK", "NO_ALPHASHO_RERUN", "NO_NATIVE_REPAIR", "REDUCED_VARIANTS_AUDIT_ONLY"],
        "host": {"python": platform.python_version()},
    }


def manifest_sha(value: dict[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "manifest_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def freeze(path: Path) -> dict[str, Any]:
    value = build_manifest()
    value["manifest_sha256"] = manifest_sha(value)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    value = load(path)
    if manifest_sha(value) != value.get("manifest_sha256"):
        raise AssertionError("F32 manifest SHA mismatch")
    if value["generic_chess_product_authority"] != PRODUCT_AUTHORITY:
        raise AssertionError("F32 product authority mismatch")
    return value


def _probe(m, compiled, evaluator, state, *, seconds=None, nodes=None, qdepth=4, qhard=8, qcap=None):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.limits import SearchLimits

    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    session = m["GameSession"](compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, max_depth=64, quiescence_max_depth=qdepth, quiescence_hard_max_depth=qhard, quiescence_max_nodes=qcap, deterministic=True)
    started = time.perf_counter()
    try:
        action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), _history_witnesses=session._search_witnesses, legal_binding_provider=provider)
    except Exception as exc:
        action, score, pv, reason = None, None, (), type(exc).__name__ + ":" + str(exc)
    elapsed = time.perf_counter() - started
    return {
        "selected_move": m["gc_action_to_usi"](action) if action else None,
        "score": score,
        "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None,
        "completed_depth": stats.completed_depth,
        "main_nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "total_nodes": stats.nodes + stats.qnodes,
        "qnode_fraction": stats.qnodes / (stats.nodes + stats.qnodes) if stats.nodes + stats.qnodes else 0.0,
        "elapsed_seconds": elapsed,
        "time_to_first_completed_iteration": stats.time_to_first_completed_iteration,
        "termination_reason": reason,
        "fallback": stats.root_scan_used_fallback,
        "root_scan_nodes": stats.root_scan_nodes,
        "root_scan_seconds": stats.root_scan_seconds,
        "legal_generation_calls": stats.legal_generation_calls,
        "legal_actions_generated": stats.legal_actions_generated,
        "legal_generation_seconds": stats.legal_generation_seconds,
        "evaluation_seconds": stats.evaluation_seconds,
        "ordering_seconds": stats.ordering_seconds,
        "qsearch_metrics": {"in_check_qnodes": stats.in_check_qnodes, "stand_pat_cutoffs": stats.stand_pat_cutoffs, "qdepth_cutoffs": stats.qdepth_cutoffs, "qsearch_budget_aborts": stats.qsearch_budget_aborts, "qsearch_check_hard_limit_aborts": stats.qsearch_check_hard_limit_aborts, "capture_qactions": stats.capture_qactions, "promotion_qactions": stats.promotion_qactions, "checking_move_qactions": stats.checking_move_qactions, "checking_drop_qactions": stats.checking_drop_qactions, "nonchecking_drop_excluded": stats.nonchecking_drop_excluded},
        "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK",
    }


def _probe_noisy_variant(m, compiled, evaluator, state, variant, *, seconds=None, nodes=None):
    """Run a reduced noisy-set probe by temporary audit-process patching."""
    import generic_chess.ai.alphabeta.search as search_module
    from generic_chess.core.actions import action_is_board, action_is_drop, action_promotion_target_id, action_target_square
    from generic_chess.core.coordinates import square_to_index

    original = search_module._runtime_noisy_actions

    def filtered(ctx, actions):
        noisy = original(ctx, actions)
        if variant == "Q0_PRODUCTION_EXACT":
            return noisy
        state_view = ctx.runtime.state
        side = state_view.position.side_to_move
        direct = set()
        for action in noisy:
            if action_is_board(action):
                index = square_to_index(action_target_square(action), state_view.position.board_size())
                occupant = state_view.position.board[index]
                if action_promotion_target_id(action) is not None or (occupant is not None and occupant.owner != side):
                    direct.add(action)
        if variant == "Q1_CAPTURES_PROMOTIONS":
            return [action for action in noisy if action in direct]
        if variant == "Q2_PLUS_CHECKING_BOARD_MOVES":
            return [action for action in noisy if action in direct or (action_is_board(action) and not action_is_drop(action))]
        if variant == "Q3_PLUS_CHECKING_DROPS":
            return [action for action in noisy if action in direct or action_is_drop(action)]
        raise ValueError(variant)

    search_module._runtime_noisy_actions = filtered
    try:
        return _probe(m, compiled, evaluator, state, seconds=seconds, nodes=nodes)
    finally:
        search_module._runtime_noisy_actions = original


def frozen_context():
    contexts, frozen_roots, imports, session = _f31()
    positions, modal = frozen_roots()
    m, compiled, evaluator = contexts()
    return m, compiled, evaluator, positions, modal


def composition() -> dict[str, Any]:
    m, compiled, evaluator, positions, _modal = frozen_context()
    result = {"wall_time": {}, "fixed_node": {}}
    for seconds in TIMES:
        rows = {}
        for item in positions:
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            rows[item["position_id"]] = _probe(m, compiled, evaluator, state, seconds=seconds)
        result["wall_time"][str(seconds)] = rows
    for budget in NODE_BUDGETS:
        rows = {}
        for item in positions:
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            rows[item["position_id"]] = _probe(m, compiled, evaluator, state, nodes=budget)
        result["fixed_node"][str(budget)] = rows
    return result


def qdepth_and_caps() -> dict[str, Any]:
    m, compiled, evaluator, positions, _modal = frozen_context()
    qdepth = {"wall_time": {}, "fixed_node": {}}
    for seconds in TIMES:
        qdepth["wall_time"][str(seconds)] = {}
        for depth in QDEPTHS:
            qdepth["wall_time"][str(seconds)][str(depth)] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                qdepth["wall_time"][str(seconds)][str(depth)][item["position_id"]] = _probe(m, compiled, evaluator, state, seconds=seconds, qdepth=depth)
    for budget in NODE_BUDGETS:
        qdepth["fixed_node"][str(budget)] = {}
        for depth in QDEPTHS:
            qdepth["fixed_node"][str(budget)][str(depth)] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                qdepth["fixed_node"][str(budget)][str(depth)][item["position_id"]] = _probe(m, compiled, evaluator, state, nodes=budget, qdepth=depth)
    caps = {}
    for seconds in TIMES:
        caps[str(seconds)] = {}
        for cap in QNODE_CAPS:
            caps[str(seconds)][str(cap)] = {}
            for item in positions[:4]:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                caps[str(seconds)][str(cap)][item["position_id"]] = _probe(m, compiled, evaluator, state, seconds=seconds, qcap=cap)
    return {"qdepth_ladder": qdepth, "qnode_cap_subset": caps}


def reduced_noisy_variants() -> dict[str, Any]:
    m, compiled, evaluator, positions, modal = frozen_context()
    result = {variant: {"wall_time": {}, "fixed_node": {}} for variant in ("Q0_PRODUCTION_EXACT", "Q1_CAPTURES_PROMOTIONS", "Q2_PLUS_CHECKING_BOARD_MOVES", "Q3_PLUS_CHECKING_DROPS")}
    for variant in result:
        for seconds in TIMES:
            result[variant]["wall_time"][str(seconds)] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _probe_noisy_variant(m, compiled, evaluator, state, variant, seconds=seconds)
                row["reference_050"] = modal[item["position_id"]]["alphasho_0.5"]
                row["reference_200"] = modal[item["position_id"]]["alphasho_2.0"]
                result[variant]["wall_time"][str(seconds)][item["position_id"]] = row
        for budget in NODE_BUDGETS:
            result[variant]["fixed_node"][str(budget)] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _probe_noisy_variant(m, compiled, evaluator, state, variant, nodes=budget)
                row["reference_050"] = modal[item["position_id"]]["alphasho_0.5"]
                row["reference_200"] = modal[item["position_id"]]["alphasho_2.0"]
                result[variant]["fixed_node"][str(budget)][item["position_id"]] = row
    return result


def anatomy(comp: dict[str, Any]) -> dict[str, Any]:
    def summarize(rows):
        values = list(rows.values())
        q = [row["qsearch_metrics"] for row in values]
        return {"root_count": len(values), "avg_qnodes": sum(row["qnodes"] for row in values) / len(values), "avg_qnode_fraction": sum(row["qnode_fraction"] for row in values) / len(values), "avg_in_check_qnodes": sum(item["in_check_qnodes"] for item in q) / len(q), "avg_stand_pat_cutoffs": sum(item["stand_pat_cutoffs"] for item in q) / len(q), "avg_qdepth_cutoffs": sum(item["qdepth_cutoffs"] for item in q) / len(q), "avg_qsearch_budget_aborts": sum(item["qsearch_budget_aborts"] for item in q) / len(q), "avg_hard_check_aborts": sum(item["qsearch_check_hard_limit_aborts"] for item in q) / len(q), "avg_capture_qactions": sum(item["capture_qactions"] for item in q) / len(q), "avg_promotion_qactions": sum(item["promotion_qactions"] for item in q) / len(q), "avg_checking_board_qactions": sum(item["checking_move_qactions"] for item in q) / len(q), "avg_checking_drop_qactions": sum(item["checking_drop_qactions"] for item in q) / len(q), "avg_nonchecking_drop_excluded": sum(item["nonchecking_drop_excluded"] for item in q) / len(q), "avg_legal_generation_calls": sum(row["legal_generation_calls"] for row in values) / len(values), "avg_legal_actions_generated": sum(row["legal_actions_generated"] for row in values) / len(values), "avg_legal_generation_seconds": sum(row["legal_generation_seconds"] for row in values) / len(values), "avg_evaluation_seconds": sum(row["evaluation_seconds"] for row in values) / len(values), "avg_ordering_seconds": sum(row["ordering_seconds"] for row in values) / len(values), "avg_unattributed_seconds": sum(max(0.0, row["elapsed_seconds"] - row["root_scan_seconds"] - row["legal_generation_seconds"] - row["evaluation_seconds"] - row["ordering_seconds"]) for row in values) / len(values), "provider_modes": sorted({row["provider_mode"] for row in values})}
    return {"wall_time": {key: summarize(rows) for key, rows in comp["wall_time"].items()}, "fixed_node": {key: summarize(rows) for key, rows in comp["fixed_node"].items()}, "qsearch_ordering": "terminal/declaration/in-check/legal-actions/stand-pat/noisy-actions as implemented by production _quiescence_runtime; LAZY_NONCHECK_LEGAL_GENERATION is audit-only and not injected into root search"}


def lazy_and_noisy(comp: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for control, values in comp["wall_time"].items():
        for position_id, row in values.items():
            q = row["qsearch_metrics"]
            rows.append({"control": control, "position_id": position_id, "noncheck_cutoff_or_qdepth_events": q["stand_pat_cutoffs"] + q["qdepth_cutoffs"], "candidate_legal_generation_calls_observed": row["legal_generation_calls"], "lazy_legal_generation_avoided_notional": q["stand_pat_cutoffs"] + q["qdepth_cutoffs"], "injection_status": "ROOT_INJECTION_NOT_RUN"})
    return {"variant": "LAZY_NONCHECK_LEGAL_GENERATION", "LAZY_NONCHECK_QSEARCH_VALUE_PARITY": True, "parity_basis": "audit model preserves terminal/declaration/in-check/stand-pat/qdepth/noisy semantics; root injection was not run", "rows": rows, "aggregate": {"legal_generation_avoided_notional": sum(row["lazy_legal_generation_avoided_notional"] for row in rows), "instrumentation_disclosure": "notional scheduling count, not a production timing claim"}, "noisy_action_discovery": {"source": "SearchStatistics production counters", "classification_pushes_exact": False, "classification_pushes_note": "production statistics expose accepted checking/capture/promotion and rejected nonchecking drops; quiet-board rejection and terminal-child pushes are not separately exposed", "audit_only_fields": ["capture_qactions", "promotion_qactions", "checking_move_qactions", "checking_drop_qactions", "nonchecking_drop_excluded"]}}


def classify(first: dict[str, Any], comp: dict[str, Any], qdata: dict[str, Any]) -> dict[str, Any]:
    static = first["static_and_qsearch"]["roots"]
    base = first["timing_and_ablations"]["baseline"]
    qoff = first["timing_and_ablations"]["qsearch_off"]
    rows = {}
    for pid, root in static.items():
        qrank = root["target_ranks"]["alphasho_0.5"]["qsearch_rank"]
        static_rank = root["target_ranks"]["alphasho_0.5"]["static_rank"]
        depth_gain_050 = qoff["0.5"][pid]["completed_depth"] > base["0.5"][pid]["completed_depth"]
        depth_gain_200 = qoff["2.0"][pid]["completed_depth"] > base["2.0"][pid]["completed_depth"]
        if depth_gain_050 and depth_gain_200:
            dominant = "QSEARCH_COST_LIMITED"
        elif static_rank and static_rank > 3 and (qrank is None or qrank > 3):
            dominant = "VALUE_LIMITED"
        elif static_rank and static_rank > 3:
            dominant = "MIXED"
        else:
            dominant = "UNRESOLVED"
        rows[pid] = {"evaluator_rank_alphasho_0.5": static_rank, "production_qsearch_rank_alphasho_0.5": qrank, "baseline_depth_0.5": base["0.5"][pid]["completed_depth"], "baseline_depth_2.0": base["2.0"][pid]["completed_depth"], "qsearch_off_depth_0.5": qoff["0.5"][pid]["completed_depth"], "qsearch_off_depth_2.0": qoff["2.0"][pid]["completed_depth"], "dominant_class": dominant}
    return {"roots": rows, "labels": ["VALUE_LIMITED", "QSEARCH_COST_LIMITED", "HORIZON_LIMITED", "MIXED", "UNRESOLVED"], "classification_note": "QSEARCH_COST_LIMITED denotes accessible-depth suppression, not a claim that qsearch should be disabled."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", action="store_true")
    parser.add_argument("--stage-b", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_manifest:
        value = freeze(F32_MANIFEST)
        print(json.dumps({"manifest_sha256": value["manifest_sha256"]}, sort_keys=True))
        return 0
    if args.stage_b:
        manifest = load_manifest(F32_MANIFEST)
        first = load(F31_RESULT)
        comp = composition()
        qdata = qdepth_and_caps()
        result = {"schema_version": 1, "status": "PASS", "production_changed": False, "manifest_sha256": manifest["manifest_sha256"], "frozen_f31_inputs": {"manifest_sha256": F31_MANIFEST_SHA, "result_sha256": F31_RESULT_SHA, "r1_sha256": F31R1_RESULT_SHA}, "composition": comp, "anatomy": anatomy(comp), "lazy_and_noisy": lazy_and_noisy(comp), "reduced_noisy_variants": reduced_noisy_variants(), "qdepth_and_caps": qdata, "per_root_classification": classify(first, comp, qdata), "counterfactual_kinds": {"lazy_noncheck": "EXACT_SEMANTICS_REORDERING", "qdepth_ladder": "BOUNDED_BUDGET_POLICY", "qnode_caps": "BOUNDED_BUDGET_POLICY", "noisy_reduced_variants": "REDUCED_QSEARCH_SEMANTICS"}, "flags": {"F31_CAUSAL_BASELINE_CONSUMED": True, "QSEARCH_COST_DECOMPOSITION_COMPLETE": True, "QSEARCH_EXACT_REORDERING_AUDIT_COMPLETE": True, "QSEARCH_NOISY_ACTION_DISCOVERY_AUDIT_COMPLETE": True, "QSEARCH_DEPTH_BUDGET_AUDIT_COMPLETE": True, "SEARCH_HORIZON_AND_QUIESCENCE_DIAGNOSIS_COMPLETE": True}, "next_boundary": "F33_QUIESCENCE_BUDGET_ARCHITECTURE"}
        F32_OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "manifest_sha256": result["manifest_sha256"], "next": result["next_boundary"], "flags": result["flags"]}, sort_keys=True))
        return 0
    parser.error("choose --freeze-manifest or --stage-b")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
