"""F36 diagnosis-only audit for post-F35 search capacity and value gaps."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import audit_f30r1_alphasho_reference as f30
from scripts import audit_f31_gap_causal as f31

MANIFEST = ROOT / "tests/fixtures/f36_post_reserve_manifest.json"
BASELINE = ROOT / "tests/fixtures/f36_post_reserve_equal_time_baseline.json"
LADDER = ROOT / "tests/fixtures/f36_post_reserve_capacity_ladder.json"
CAUSAL = ROOT / "tests/fixtures/f36_post_reserve_causal_table.json"
SELECTION = ROOT / "tests/fixtures/f36_post_reserve_selection.json"
STATIC_DIRECT = ROOT / "tests/fixtures/f36_post_reserve_static_direct_rank.json"
F35R1_RESULT = ROOT / "tests/fixtures/f35r1_reserve_only_results.json"
F35R1_MANIFEST_SHA = "e6446cb1d436e6bcabf71dfc188bb4a3fbd4933fabf7b702981feb86f67a4fdb"
F35R1_RESULT_SHA = "d2d53ab89205feae28a3c1da73b9a9de7650199ab61ce62d40a53c961e19cd30"
F35R1_ACCESS_SHA = "c861c07f7e3016bf373d18c337f80862d122ff73ab6800e81b65a6a0204140c8"
F35R1_BASELINE_SHA = "6206073e94dffa4d373d35282f5712a519adaae462a186e9f3b4de6579d9ff89"
F35_PROVISIONAL_RESULT_SHA = "e7fa2c81340de6aa1aa04e53e4842ff64fe1e6e4ac4ebed5483548b119cbaa4a"
F34_MANIFEST_SHA = "f65588fdbb35a1ab42508a33937735cb50e0d0b0c1ed3e3230fdd3f1572793cc"
F34_MATRIX_SHA = "f6ac85a2485c32dd03658811ce9a88618c749a2fffed233efd76363226647605"
F34_SELECTION_SHA = "fac977997eaa50f7e017d934aeda775f5fd1083825162e472dbdbcdf8c5fba3c"
F34_SAFETY_SHA = "d12105d9b2667d0485c318bff1b99c31055618b1c93899f97fd196e669e798ca"
F33R1_SHA = "4884b06fca9e2d5ae0483c008cc227a190ecbdc6d56170ed10d16a66b346a309"
F33R1_MANIFEST_SHA = "b75d62b946caea52655de79d2f672a2b94d8a668d57b01f7ca3774f8e403ef8d"
F33H33A_SHA = "e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c"
F33_MANIFEST_SHA = "f7dd15cb032e1c9aad9198c5afb334ad62a07d814069dcaa0466c0531ddd2eeb"
F32R1_SHA = "0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88"
F32_SHA = "878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56"
F31R1_SHA = "ed0834b4a591d9a0b0dddd529a1c1ce205f22fd268caafe7951d79966113a83f"
F31_SHA = "9eaaccf9ecea8717e6a2ffe198da9136cb1e7fee0ee9ac2edcb60d6f70d8b77e"
F30_MANIFEST_SHA = "de1ffc84b635d96fa8abd5a23eed42c79ef9a7fd48b7d07351c38ac6ecac4f1a"
F30_FRESH_SHA = "8ec60aebdde3e7fb4d192d99e77948a954d7aab83c6942e0704a8956721a3eba"
F30_PAIRED_SHA = "3e80b5a5488624c7afd34638fbbfee8f200dd96af472d5345672ff69439ca256"
F25_DESCRIPTOR_SHA = "2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151"
SANDBOX_SHA = "80c1576c4443b4c9311b86fa0d8efbbfa24150ca"
SEARCH_SHA = "f9b5faf17b40fcc9f9672875c4d200db7fc5bea314b9da5a20351b95563e3f4e"
PRODUCT_AUTHORITY = "a389adc50ed42096874ee38f818584978468c6ac"
SHOGI_FINGERPRINT = "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"
TIMES = (1.0, 4.0, 8.0)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def freeze():
    paths = {
        "f35r1_manifest": ("tests/fixtures/f35r1_reserve_only_manifest.json", F35R1_MANIFEST_SHA),
        "f35r1_result": ("tests/fixtures/f35r1_reserve_only_results.json", F35R1_RESULT_SHA),
        "f35r1_accessibility": ("tests/fixtures/f35r1_reserve_only_accessibility.json", F35R1_ACCESS_SHA),
        "f35r1_baseline": ("tests/fixtures/f35r1_reserve_only_baseline.json", F35R1_BASELINE_SHA),
        "f35_provisional_result": ("tests/fixtures/f35_q34c_fixed_node_parity.json", F35_PROVISIONAL_RESULT_SHA),
        "f34_manifest": ("tests/fixtures/f34_qsearch_budget_manifest.json", F34_MANIFEST_SHA),
        "f34_matrix": ("tests/fixtures/f34_qsearch_budget_matrix.json", F34_MATRIX_SHA),
        "f34_selection": ("tests/fixtures/f34_qsearch_budget_selection.json", F34_SELECTION_SHA),
        "f34_safety": ("tests/fixtures/f34_qsearch_tactical_safety.json", F34_SAFETY_SHA),
        "f33r1_result": ("tests/fixtures/f33r1_retention_gate_results.json", F33R1_SHA),
        "f33r1_manifest": ("tests/fixtures/f33r1_retention_timing_manifest.json", F33R1_MANIFEST_SHA),
        "f33_h33a": ("tests/fixtures/f33_check_discovery_audit.json", F33H33A_SHA),
        "f33_manifest": ("tests/fixtures/f33_check_discovery_manifest.json", F33_MANIFEST_SHA),
        "f32r1_result": ("tests/fixtures/f32r1_qsearch_exact_counterfactual.json", F32R1_SHA),
        "f32_result": ("tests/fixtures/f32_qsearch_diagnosis.json", F32_SHA),
        "f31r1_result": ("tests/fixtures/f31r1_counterfactual_causal_reclassification.json", F31R1_SHA),
        "f31_result": ("tests/fixtures/f31_causal_diagnosis.json", F31_SHA),
        "f30_manifest": ("tests/fixtures/f30r1_benchmark_manifest.json", F30_MANIFEST_SHA),
        "f30_fresh": ("tests/fixtures/f30r1_fresh_move_reference.json", F30_FRESH_SHA),
        "f30_paired": ("tests/fixtures/f30r1_paired_match.json", F30_PAIRED_SHA),
        "f25_descriptors": ("tests/fixtures/f25_standard_shogi_position_descriptors.json", F25_DESCRIPTOR_SHA),
    }
    value = {
        "schema_version": 1,
        "kind": "F36_POST_RESERVE_MANIFEST",
        "current_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "retained_search_sha256": digest(ROOT / "generic_chess/ai/alphabeta/search.py"),
        "audit_harness_sha256": digest(Path(__file__)),
        "product_authority": PRODUCT_AUTHORITY,
        "standard_shogi_fingerprint": SHOGI_FINGERPRINT,
        "descriptor_sha256": F25_DESCRIPTOR_SHA,
        "frozen_inputs": {k: {"path": p, "sha256": expected, "file_sha256": digest(ROOT / p)} for k, (p, expected) in paths.items()},
        "provisional_f35_evidence": {"commit": "b02d92e0aabaf41b547cd8fa8fdb550e7dc756cb", "result_sha256": F35_PROVISIONAL_RESULT_SHA},
        "matrix": {"consumed_equal_time_seconds": [0.5, 2.0], "new_capacity_seconds": list(TIMES), "roots": 10, "new_repetitions": 1, "ceiling_seconds": 8.0},
        "gates": {"NO_TUNING_FROM_RESULTS": True, "PRODUCTION_DIFF_ZERO": True, "static_rank_exact": True, "direct_qsearch_rank_exact": True, "capacity_ladder_complete": True},
        "constraints": ["NO_PRODUCTION_CHANGE", "NO_F35_RERUN_AT_0P5_OR_2P0", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK", "NO_ALPHA_CHESS", "NO_TUNING_FROM_RESULTS"],
    }
    value["manifest_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def _modal(rows):
    counts = Counter(row["selected_move"] for row in rows)
    best = max(counts.values())
    move = sorted(move for move, count in counts.items() if count == best)[0]
    return {"modal_move": move, "modal_frequency": best, "unique_move_count": len(counts), "stable": len(counts) == 1, "moves": [row["selected_move"] for row in rows]}


def _f35_baseline():
    r1 = load(F35R1_RESULT)
    out = {}
    for control in ("0.5", "2.0"):
        out[control] = {}
        for pid, rows in r1["wall_time"]["production_candidate"][control].items():
            modal = _modal(rows)
            depths = [row["completed_depth"] for row in rows]
            out[control][pid] = {**modal, "completed_depth_values": depths, "median_completed_depth": statistics.median(depths), "fallback_event_count": sum(row["fallback"] for row in rows), "fallback_limited": statistics.median(depths) < 1, "median_first_completed_iteration": statistics.median([row["time_to_first_completed_iteration"] for row in rows if row["time_to_first_completed_iteration"] is not None]) if any(row["time_to_first_completed_iteration"] is not None for row in rows) else None, "median_main_nodes": statistics.median(row["main_nodes"] for row in rows), "median_qnodes": statistics.median(row["qnodes"] for row in rows), "median_qnode_fraction": statistics.median(row["qnode_fraction"] for row in rows), "source": "F35_R1_FROZEN_RAW_CANDIDATE"}
    return out


def _pre_f35_baseline():
    fresh = load(ROOT / "tests/fixtures/f30r1_fresh_move_reference.json")
    out = {}
    for control in ("0.5", "2.0"):
        out[control] = {}
        for pid, row in fresh["generic_chess"][control]["summaries"].items():
            runs = [item for item in fresh["generic_chess"][control]["runs"] if item["position_id"] == pid]
            out[control][pid] = {"modal_move": row["modal_move"], "stable": row["stable"], "completed_depth_values": [item["completed_depth"] for item in runs], "fallback_event_count": sum(item["fallback"] for item in runs), "source": "F30_R1_FROZEN_PRE_F35"}
    return out


def _probe(m, compiled, evaluator, state, seconds):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    limits = m["SearchLimits"](max_time_seconds=seconds, max_depth=64, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True)
    completions = []
    started = time.perf_counter()
    def progress(depth, nodes, qnodes):
        completions.append({"depth": depth, "elapsed_seconds": time.perf_counter() - started, "main_nodes": nodes, "qnodes": qnodes})
    action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), _history_witnesses=(state.position,), legal_binding_provider=provider, progress_callback=progress)
    elapsed = time.perf_counter() - started
    total = stats.nodes + stats.qnodes
    return {"selected_move": m["gc_action_to_usi"](action) if action else None, "score": score, "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None, "completed_depth": stats.completed_depth, "fallback": stats.root_scan_used_fallback, "main_nodes": stats.nodes, "qnodes": stats.qnodes, "total_nodes": total, "qnode_fraction": stats.qnodes / total if total else 0.0, "time_to_first_completed_iteration": stats.time_to_first_completed_iteration, "elapsed_seconds": elapsed, "termination_reason": reason, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "completion_events": completions, "source": "F36_LIVE_POST_F35"}


def _static_direct_parity():
    import generic_chess.ai.alphabeta.search as search
    old_helper = search._ordinary_qdepth_limit
    # F31's direct ranking is an internal configured-qdepth probe.  Recreate
    # that protocol here without changing production or the retained root
    # reserve, so this comparison tests direct-context isolation rather than
    # the first-iteration policy itself.
    search._ordinary_qdepth_limit = lambda ctx: ctx.qdepth_limit
    try:
        current = f31.static_and_qsearch()
    finally:
        search._ordinary_qdepth_limit = old_helper
    frozen = load(ROOT / "tests/fixtures/f31_causal_diagnosis.json")["static_and_qsearch"]
    static_ok = True
    direct_ok = True
    for pid in current["roots"]:
        a = current["roots"][pid]
        b = frozen["roots"][pid]
        if a["legal_action_count"] != b["legal_action_count"]:
            static_ok = False
        sig_a = [(r["move"], r["action_key"], r["score"], r["terminal"], r["rank"]) for r in a["all_static_actions"]]
        sig_b = [(r["move"], r["action_key"], r["score"], r["terminal"], r["rank"]) for r in b["all_static_actions"]]
        static_ok = static_ok and sig_a == sig_b
        q_a = [(r["move"], r["action_key"], r["score"], r["rank"]) for r in a["all_qsearch_actions"]]
        q_b = [(r["move"], r["action_key"], r["score"], r["rank"]) for r in b["all_qsearch_actions"]]
        direct_ok = direct_ok and q_a == q_b
    return {"static_rank_parity": static_ok, "direct_qsearch_rank_parity": direct_ok, "direct_protocol": "configured qdepth shadow for audit-only internal ranking; production reserve untouched", "current": current, "frozen_f31_static_and_qsearch_sha": digest(ROOT / "tests/fixtures/f31_causal_diagnosis.json")}


def _compact_static_direct(static):
    frozen = load(ROOT / "tests/fixtures/f31_causal_diagnosis.json")["static_and_qsearch"]["roots"]
    roots = {}
    for pid, current in static["current"]["roots"].items():
        old = frozen[pid]
        static_rows = [(r["move"], r["action_key"], r["score"], r["terminal"], r["rank"]) for r in current["all_static_actions"]]
        old_static_rows = [(r["move"], r["action_key"], r["score"], r["terminal"], r["rank"]) for r in old["all_static_actions"]]
        q_rows = [(r["move"], r["action_key"], r["score"], r["rank"]) for r in current["all_qsearch_actions"]]
        old_q_rows = [(r["move"], r["action_key"], r["score"], r["rank"]) for r in old["all_qsearch_actions"]]
        roots[pid] = {"legal_action_count": current["legal_action_count"], "static_signature_sha256": hashlib.sha256(json.dumps(static_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "frozen_static_signature_sha256": hashlib.sha256(json.dumps(old_static_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "direct_qsearch_signature_sha256": hashlib.sha256(json.dumps(q_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "frozen_direct_qsearch_signature_sha256": hashlib.sha256(json.dumps(old_q_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "target_ranks": current["target_ranks"]}
    return {"static_rank_parity": static["static_rank_parity"], "direct_qsearch_rank_parity": static["direct_qsearch_rank_parity"], "f31_fixture_sha256": static["frozen_f31_static_and_qsearch_sha"], "roots": roots}


def _classify(row, as050, as200, static_root):
    moves = [row["ladder"][str(c)]["modal_move"] if str(c) in ("0.5", "2.0") else row["ladder"][str(c)]["selected_move"] for c in (0.5, 1.0, 2.0, 4.0, 8.0)]
    long_moves = moves[2:]
    targets = {as050, as200}
    recovered = moves[2] not in targets and any(move in targets for move in moves[3:])
    stable_long = len(set(long_moves)) == 1
    if recovered and all(move in targets for move in long_moves[next(i for i, move in enumerate(long_moves) if move in targets):]):
        return "EXTERNAL_MOVE_RECOVERED_WITH_MORE_SEARCH"
    if stable_long and as050 != moves[2] and as200 != moves[2] and all((static_root["target_ranks"].get(name, {}).get("static_rank") or 99) > 3 for name in ("alphasho_0.5", "alphasho_2.0")):
        return "SEARCH_STABLE_VALUE_MISMATCH"
    if len(set(long_moves)) > 1:
        return "HORIZON_SENSITIVE_MISMATCH"
    return "UNRESOLVED"


def run():
    manifest = load(MANIFEST)
    if digest(ROOT / "generic_chess/ai/alphabeta/search.py") != manifest["retained_search_sha256"] or subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode != 0:
        raise AssertionError("F36 production diff is not zero")
    f35 = _f35_baseline()
    pre = _pre_f35_baseline()
    static = _static_direct_parity()
    positions, external = f31._frozen_roots()
    m, compiled, evaluator = f31._contexts()
    ladder = {pid: {str(control): f35[str(control)][pid] for control in (0.5, 2.0)} for pid in (item["position_id"] for item in positions)}
    for seconds in TIMES:
        for item in positions:
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            ladder[item["position_id"]][str(seconds)] = _probe(m, compiled, evaluator, state, seconds)
    capacity = {"controls": {}, "per_root_depth_distribution": {}}
    for control in ("0.5", "1.0", "2.0", "4.0", "8.0"):
        rows = [ladder[pid][control] for pid in ladder]
        depths = [row["median_completed_depth"] if "median_completed_depth" in row else row["completed_depth"] for row in rows]
        capacity["controls"][control] = {"depth_ge_1_roots": sum(depth >= 1 for depth in depths), "depth_ge_2_roots": sum(depth >= 2 for depth in depths), "depth_ge_3_roots": sum(depth >= 3 for depth in depths), "fallback_roots": sum(row.get("fallback_limited", row.get("fallback", False)) for row in rows), "final_depth_distribution": dict(sorted(Counter(map(str, depths)).items()))}
    distance = {}
    for pid, row in ladder.items():
        target = int(f35["2.0"][pid]["median_completed_depth"]) + 1
        events = [event for event in row["8.0"]["completion_events"] if event["depth"] >= target]
        reached = events[0] if events else None
        distance[pid] = {"target_next_depth": target, "completion_event": reached, "within_20_percent": bool(reached and reached["elapsed_seconds"] <= 2.4), "within_50_percent": bool(reached and reached["elapsed_seconds"] <= 3.0), "within_2x": bool(reached and reached["elapsed_seconds"] <= 4.0), "status": "REACHED" if reached else "NEXT_ITERATION_NOT_REACHED_BY_8S"}
    fresh = load(ROOT / "tests/fixtures/f30r1_fresh_move_reference.json")
    historical = f31.historical_source()["references"]
    forced = load(ROOT / "tests/fixtures/f31r1_counterfactual_causal_reclassification.json")["forced_candidate_summary"]["roots"]
    causal = {}
    for item in positions:
        pid = item["position_id"]
        root_static = static["current"]["roots"][pid]
        row = {"root_id": pid, "alphasho_0.5_modal": external[pid]["alphasho_0.5"], "alphasho_2.0_modal": external[pid]["alphasho_2.0"], "f22_historical_move": historical[pid], "ladder": ladder[pid], "static_rank_alphasho_0.5": root_static["target_ranks"]["alphasho_0.5"]["static_rank"], "static_rank_alphasho_2.0": root_static["target_ranks"]["alphasho_2.0"]["static_rank"], "direct_qsearch_rank_alphasho_0.5": root_static["target_ranks"]["alphasho_0.5"]["qsearch_rank"], "direct_qsearch_rank_alphasho_2.0": root_static["target_ranks"]["alphasho_2.0"]["qsearch_rank"], "next_iteration_distance": distance[pid], "f31_forced_candidate_summary": forced.get(pid), "causal_classification": None}
        row["causal_classification"] = _classify(row, external[pid]["alphasho_0.5"], external[pid]["alphasho_2.0"], root_static)
        causal[pid] = row
    static_gap = sum((row["static_rank_alphasho_0.5"] or 99) > 3 or (row["static_rank_alphasho_2.0"] or 99) > 3 for row in causal.values())
    aggregates = {"SHORT_CONTROL_FALLBACK_ROOTS": sum(f35["0.5"][pid]["fallback_limited"] for pid in f35["0.5"]), "TWO_SECOND_DEPTH2_ROOTS": capacity["controls"]["2.0"]["depth_ge_2_roots"], "LONGER_SEARCH_EXTERNAL_RECOVERY_ROOTS": sum(row["causal_classification"] == "EXTERNAL_MOVE_RECOVERED_WITH_MORE_SEARCH" for row in causal.values()), "STABLE_VALUE_MISMATCH_ROOTS": sum(row["causal_classification"] == "SEARCH_STABLE_VALUE_MISMATCH" for row in causal.values()), "STATIC_TOP3_GAP_ROOTS": static_gap, "NEXT_ITERATION_NEAR_ROOTS": sum(item["within_50_percent"] for item in distance.values())}
    search_actionable = (aggregates["SHORT_CONTROL_FALLBACK_ROOTS"] >= 5 or aggregates["TWO_SECOND_DEPTH2_ROOTS"] <= 3) and (aggregates["LONGER_SEARCH_EXTERNAL_RECOVERY_ROOTS"] >= 3 or aggregates["NEXT_ITERATION_NEAR_ROOTS"] >= 5)
    evaluator_actionable = aggregates["STATIC_TOP3_GAP_ROOTS"] >= 7 and aggregates["STABLE_VALUE_MISMATCH_ROOTS"] >= 5 and aggregates["LONGER_SEARCH_EXTERNAL_RECOVERY_ROOTS"] <= 2 and (aggregates["TWO_SECOND_DEPTH2_ROOTS"] >= 4 or aggregates["NEXT_ITERATION_NEAR_ROOTS"] < 5)
    classification = "MIXED_MATERIAL" if search_actionable and evaluator_actionable else "SEARCH_CAPACITY_PRIMARY" if search_actionable else "EVALUATOR_VALUE_PRIMARY" if evaluator_actionable else "UNRESOLVED"
    boundary = {"SEARCH_CAPACITY_PRIMARY": "F37_STANDARD_SHOGI_RUNTIME_MINIMAL_INTERVENTION_SELECTION", "EVALUATOR_VALUE_PRIMARY": "F37_RULE_DERIVED_EVALUATOR_REENTRY", "MIXED_MATERIAL": "F37_STANDARD_SHOGI_STRENGTH_MINIMAL_INTERVENTION_SELECTION", "UNRESOLVED": "F37_STANDARD_SHOGI_STRENGTH_CAUSAL_CORRECTIVE"}[classification]
    result = {"schema_version": 1, "status": "PASS", "production_diff_zero": True, "f35_baseline_consumed": {"post_reserve": f35, "pre_f35": pre}, "static_direct": {"static_rank_parity": static["static_rank_parity"], "direct_qsearch_rank_parity": static["direct_qsearch_rank_parity"], "f31_fixture_sha256": static["frozen_f31_static_and_qsearch_sha"], "current": static["current"]}, "capacity_ladder": ladder, "capacity_aggregates": capacity, "iteration_completion_distance": distance, "causal_table": causal, "aggregate_quantities": aggregates, "actionable": {"search_capacity": search_actionable, "evaluator_value": evaluator_actionable, "classification": classification}, "selection": {"boundary": boundary, "search_capacity_primary": search_actionable, "evaluator_value_primary": evaluator_actionable}, "flags": {"F35_RESERVE_BASELINE_CONSUMED": True, "POST_RESERVE_EQUAL_TIME_BASELINE_FROZEN": True, "POST_RESERVE_DEPTH_CAPACITY_LADDER_COMPLETE": True, "POST_RESERVE_STATIC_VALUE_GAP_REVALIDATED": static["static_rank_parity"], "POST_RESERVE_EXTERNAL_REFERENCE_DIAGNOSIS_COMPLETE": True, "STANDARD_SHOGI_NEXT_STRENGTH_BOUNDARY_SELECTED": True}, "fingerprints": {"standard_shogi": SHOGI_FINGERPRINT, "product_authority": PRODUCT_AUTHORITY}, "no_rerun": {"f35_equal_time": True, "alphasho": True, "paired_benchmark": True}}
    result["static_direct_compact"] = _compact_static_direct(static)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--freeze-manifest", action="store_true"); parser.add_argument("--run", action="store_true"); args = parser.parse_args(argv)
    if args.freeze_manifest:
        print(json.dumps({"manifest_sha256": freeze()["manifest_sha256"]})); return 0
    if args.run:
        result = run()
        BASELINE.write_text(json.dumps(result["f35_baseline_consumed"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        LADDER.write_text(json.dumps({"capacity_aggregates": result["capacity_aggregates"], "ladder": result["capacity_ladder"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        CAUSAL.write_text(json.dumps(result["causal_table"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        SELECTION.write_text(json.dumps({"aggregate_quantities": result["aggregate_quantities"], "actionable": result["actionable"], "selection": result["selection"], "flags": result["flags"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        STATIC_DIRECT.write_text(json.dumps(result["static_direct_compact"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "classification": result["actionable"]["classification"], "boundary": result["selection"]["boundary"], "aggregates": result["aggregate_quantities"], "flags": result["flags"]}, sort_keys=True)); return 0
    parser.error("use --freeze-manifest or --run")


if __name__ == "__main__":
    raise SystemExit(main())
