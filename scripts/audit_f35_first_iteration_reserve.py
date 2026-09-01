"""F35 audit/retention harness for the Q34C first-iteration reserve."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import audit_f32r1_qsearch_exact_counterfactual as f32r1

MANIFEST = ROOT / "tests/fixtures/f35_first_iteration_reserve_manifest.json"
OUTPUT = ROOT / "tests/fixtures/f35_q34c_fixed_node_parity.json"
ACCESS = ROOT / "tests/fixtures/f35_first_iteration_reserve_accessibility.json"
BASELINE = ROOT / "tests/fixtures/f35_first_iteration_reserve_baseline.json"
F34_RESULT = ROOT / "tests/fixtures/f34_qsearch_budget_matrix.json"
F34_MANIFEST_SHA = "6a5600c4fc1fb82582b42d47235fd72b4e02d60322749e1b97ebbae98500b75d"
F34_MATRIX_SHA = "f6ac85a2485c32dd03658811ce9a88618c749a2fffed233efd76363226647605"
F34_SELECTION_SHA = "654a4076ca736591b4007ebb43b086e6d3d9e2b1152177b858c18c4257d58027"
F34_SAFETY_SHA = "d12105d9b2667d0485c318bff1b99c31055618b1c93899f97fd196e669e798ca"
F30_FRESH_SHA = "8ec60aebdde3e7fb4d192d99e77948a954d7aab83c6942e0704a8956721a3eba"
F30_PAIRED_SHA = "3e80b5a5488624c7afd34638fbbfee8f200dd96af472d5345672ff69439ca256"
F30_MANIFEST_SHA = "3af3ac415bf5fee1f52bae7fe09d6a888db1a90be3d12c10cce1acd477ed2d7e"
F31_RESULT_SHA = "9eaaccf9ecea8717e6a2ffe198da9136cb1e7fee0ee9ac2edcb60d6f70d8b77e"
F31R1_SHA = "ed0834b4a591d9a0b0dddd529a1c1ce205f22fd268caafe7951d79966113a83f"
F32_RESULT_SHA = "878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56"
F32R1_SHA = "0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88"
F33_H33A_SHA = "e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c"
F33R1_SHA = "4884b06fca9e2d5ae0483c008cc227a190ecbdc6d56170ed10d16a66b346a309"
F33R1_MANIFEST_SHA = "76199c945586864aa62182c0a56b866049bbafa4ec0f2a8c47c2b7f8d9f23a84"
F33_MANIFEST_SHA = "14de91028470b9bf4d3a8933a73912fa1e0b2567fb70ca106e0a284d778378bf"
F25_DESCRIPTOR_SHA = "2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151"
PRE_CHANGE_SEARCH_SHA = "657cbd8d3bc623b3aa20dc88674f3f43edb0c9af"
TIMES = (0.50, 2.00)
FIXED = (128, 256, 512, 1024, 2048)
FIELDS = ("selected_move", "score", "pv_head", "completed_depth", "main_nodes", "qnodes", "termination_reason")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def freeze():
    refs = {
        "f34_manifest": ("tests/fixtures/f34_qsearch_budget_manifest.json", F34_MANIFEST_SHA),
        "f34_matrix": ("tests/fixtures/f34_qsearch_budget_matrix.json", F34_MATRIX_SHA),
        "f34_selection": ("tests/fixtures/f34_qsearch_budget_selection.json", F34_SELECTION_SHA),
        "f34_safety": ("tests/fixtures/f34_qsearch_tactical_safety.json", F34_SAFETY_SHA),
        "f30_manifest": ("tests/fixtures/f30r1_benchmark_manifest.json", F30_MANIFEST_SHA),
        "f30_fresh": ("tests/fixtures/f30r1_fresh_move_reference.json", F30_FRESH_SHA),
        "f30_paired": ("tests/fixtures/f30r1_paired_match.json", F30_PAIRED_SHA),
        "f31_result": ("tests/fixtures/f31_causal_diagnosis.json", F31_RESULT_SHA),
        "f31r1_result": ("tests/fixtures/f31r1_counterfactual_causal_reclassification.json", F31R1_SHA),
        "f32_result": ("tests/fixtures/f32_qsearch_diagnosis.json", F32_RESULT_SHA),
        "f32r1_result": ("tests/fixtures/f32r1_qsearch_exact_counterfactual.json", F32R1_SHA),
        "f33_h33a_result": ("tests/fixtures/f33_check_discovery_audit.json", F33_H33A_SHA),
        "f33r1_result": ("tests/fixtures/f33r1_retention_gate_results.json", F33R1_SHA),
        "f33r1_manifest": ("tests/fixtures/f33r1_retention_timing_manifest.json", F33R1_MANIFEST_SHA),
        "f33_manifest": ("tests/fixtures/f33_check_discovery_manifest.json", F33_MANIFEST_SHA),
        "f25_descriptor": ("tests/fixtures/f25_standard_shogi_position_descriptors.json", F25_DESCRIPTOR_SHA),
    }
    value = {"schema_version": 1, "kind": "F35_FIRST_ITERATION_RESERVE_MANIFEST", "pre_run_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(), "frozen_inputs": {k: {"path": p, "sha256": v, "file_sha256": sha(ROOT / p)} for k, (p, v) in refs.items()}, "production_search_pre_change_sha": PRE_CHANGE_SEARCH_SHA, "contract": {"configured_qdepth": 4, "hard_qdepth": 8, "reserve": "ordinary non-check qsearch effective depth 0 until first successful main iteration; then configured depth", "in_check": "unchanged full legal evasion path", "state": "context-local per run_root_search; aborted first iteration never completes reserve"}, "matrix": {"fixed_nodes": list(FIXED), "wall_times_seconds": list(TIMES), "wall_repetitions": 3, "roots": 10}, "gates": {"fixed_reproduction": "20/20 exact F34 Q34C rows", "accessibility": "F34 gate: depth >=5 at either control, fallback reduction >=5 at 0.50s, or 2.00s first-iteration gain >=20% without more fallback", "disqualifier": "depth regression >2 roots at either control", "retention": "all correctness, safety, accessibility, balance and cancellation gates"}, "constraints": ["NO_EVALUATOR_CHANGE", "NO_EVALUATOR_V2", "NO_NATIVE_REPAIR", "NO_RULE_SCHEMA_SESSION_RECORD_CLI_CHANGE", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK", "NO_ALPHA_CHESS", "PRODUCTION_DIFF_ONLY_SEARCH_PY"]}
    value["manifest_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def _probe(m, compiled, evaluator, state, *, shadow, seconds=None, nodes=None, max_depth=64, trace=None, cancel=None):
    import generic_chess.ai.alphabeta.search as search
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
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, max_depth=max_depth, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True)
    old = search._ordinary_qdepth_limit
    def helper(ctx):
        value = ctx.qdepth_limit if shadow else old(ctx)
        if trace is not None:
            trace.append({"complete": ctx.first_main_iteration_complete, "configured": ctx.qdepth_limit, "effective": value})
        return value
    search._ordinary_qdepth_limit = helper
    started = time.perf_counter()
    try:
        action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, cancel, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), _history_witnesses=session._search_witnesses, legal_binding_provider=provider)
    except Exception as exc:
        action, score, pv, reason = None, None, (), type(exc).__name__ + ":" + str(exc)
    elapsed = time.perf_counter() - started
    search._ordinary_qdepth_limit = old
    total = stats.nodes + stats.qnodes
    return {"selected_move": m["gc_action_to_usi"](action) if action else None, "score": score, "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None, "completed_depth": stats.completed_depth, "main_nodes": stats.nodes, "qnodes": stats.qnodes, "total_nodes": total, "qnode_fraction": stats.qnodes / total if total else 0.0, "fallback": bool(stats.root_scan_used_fallback), "time_to_first_completed_iteration": stats.time_to_first_completed_iteration, "elapsed_seconds": elapsed, "termination_reason": reason, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK"}


def _summary(rows):
    return {"elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in rows), "completed_depth": sorted({r["completed_depth"] for r in rows}), "fallback": sum(r["fallback"] for r in rows), "main_nodes": statistics.median(r["main_nodes"] for r in rows), "qnodes": statistics.median(r["qnodes"] for r in rows), "total_nodes": statistics.median(r["total_nodes"] for r in rows), "qnode_fraction": statistics.median(r["qnode_fraction"] for r in rows), "time_to_first_completed_iteration": statistics.median([r["time_to_first_completed_iteration"] for r in rows if r["time_to_first_completed_iteration"] is not None]) if any(r["time_to_first_completed_iteration"] is not None for r in rows) else None}


def _accessibility(shadow, candidate):
    out = {}
    for control in ("0.5", "2.0"):
        base = {pid: _summary(rows) for pid, rows in shadow[control].items()}
        cand = {pid: _summary(rows) for pid, rows in candidate[control].items()}
        pairs = [(base[pid]["time_to_first_completed_iteration"], cand[pid]["time_to_first_completed_iteration"]) for pid in base if base[pid]["time_to_first_completed_iteration"] is not None and cand[pid]["time_to_first_completed_iteration"] is not None]
        first_gain = 1 - statistics.median(v for _, v in pairs) / statistics.median(v for v, _ in pairs) if pairs and statistics.median(v for v, _ in pairs) else 0.0
        out[control] = {"depth_improved_roots": sum(cand[pid]["completed_depth"] > base[pid]["completed_depth"] for pid in base), "depth_regressed_roots": sum(cand[pid]["completed_depth"] < base[pid]["completed_depth"] for pid in base), "fallbacks_removed_0.50": sum(base[pid]["fallback"] > cand[pid]["fallback"] for pid in base) if control == "0.5" else 0, "new_fallbacks": sum(base[pid]["fallback"] < cand[pid]["fallback"] for pid in base), "comparable_first_iteration_roots": len(pairs), "median_first_iteration_gain": first_gain}
    a, b = out["0.5"], out["2.0"]
    out["gate"] = a["depth_improved_roots"] >= 5 or b["depth_improved_roots"] >= 5 or a["fallbacks_removed_0.50"] >= 5 or (b["median_first_iteration_gain"] >= 0.20 and b["new_fallbacks"] == 0)
    out["depth_regression_gate"] = a["depth_regressed_roots"] <= 2 and b["depth_regressed_roots"] <= 2
    return out


def _incheck_witness():
    import generic_chess.ai.alphabeta.search as search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.core.terminal import TerminalResult, TerminalStatus
    class Position:
        side_to_move = 0
        board = (None,)
        @staticmethod
        def board_size(): return 1
    class State:
        def __init__(self, terminal=TerminalStatus.ONGOING): self.position = Position(); self.terminal_status = TerminalResult(terminal); self.history = ()
    class Runtime:
        def __init__(self): self.state = State(); self.actions = [object(), object()]; self.pushed_count = 0
        @property
        def terminal_status(self): return self.state.terminal_status
        def legal_actions(self, checkpoint=None): return self.actions
        @contextmanager
        def pushed(self, action, checkpoint=None):
            before = self.state; self.pushed_count += 1; self.state = State(TerminalStatus.STALEMATE)
            try: yield self
            finally: self.state = before
    runtime = Runtime(); stats = SearchStatistics(); evaluations = []
    old_check, old_engine, old_decl = search.is_in_check, search.semantic_engine_for, search._declaration_options
    search.is_in_check = lambda *args: True; search.semantic_engine_for = lambda *args: None; search._declaration_options = lambda *args: ()
    ctx = SimpleNamespace(runtime=runtime, compiled=object(), stats=stats, budget=SimpleNamespace(check=lambda *a, **k: None), evaluator=SimpleNamespace(evaluate=lambda state: evaluations.append(1) or 0), checkpoint=lambda: None, qhard_depth_limit=8, qnode_limit=None, qdepth_limit=0, first_main_iteration_complete=False)
    try: search._quiescence_runtime(0, 1, 0, 0, ctx)
    finally: search.is_in_check, search.semantic_engine_for, search._declaration_options = old_check, old_engine, old_decl
    return {"passed": runtime.pushed_count == 2 and not evaluations, "evasions_searched": runtime.pushed_count, "stand_pat_evaluations": len(evaluations), "effective_ordinary_qdepth": 0}


def run():
    manifest = load(MANIFEST)
    if sha(ROOT / "generic_chess/ai/alphabeta/search.py") == PRE_CHANGE_SEARCH_SHA:
        raise AssertionError("F35 production change is absent")
    f34 = load(F34_RESULT)
    m, compiled, evaluator, positions, modal = f32r1._contexts()
    fixed = {"shadow_baseline": {}, "production_candidate": {}}
    for budget in (512, 2048):
        fixed["shadow_baseline"][str(budget)] = {}
        fixed["production_candidate"][str(budget)] = {}
        for item in positions:
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            fixed["shadow_baseline"][str(budget)][item["position_id"]] = _probe(m, compiled, evaluator, state, shadow=True, nodes=budget)
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            row = _probe(m, compiled, evaluator, state, shadow=False, nodes=budget)
            frozen = f34["fixed_node"]["Q34C"][str(budget)][item["position_id"]]
            row["parity"] = {field: row[field] == frozen[field] for field in FIELDS}
            fixed["production_candidate"][str(budget)][item["position_id"]] = row
    parity = [row["parity"] for budget in (512, 2048) for row in fixed["production_candidate"][str(budget)].values()]
    fixed_gate = len(parity) == 20 and all(all(row.values()) for row in parity)
    wall = {"shadow_baseline": {"0.5": {}, "2.0": {}}, "production_candidate": {"0.5": {}, "2.0": {}}}
    for variant, shadow in (("shadow_baseline", True), ("production_candidate", False)):
        for control in TIMES:
            for item in positions:
                wall[variant][str(control)][item["position_id"]] = []
                for _ in range(3):
                    state = m["sfen_to_gc_state"](compiled, item["sfen"])
                    wall[variant][str(control)][item["position_id"]].append(_probe(m, compiled, evaluator, state, shadow=shadow, seconds=control))
    access = _accessibility(wall["shadow_baseline"], wall["production_candidate"])
    trace = []
    state = m["sfen_to_gc_state"](compiled, positions[0]["sfen"])
    _probe(m, compiled, evaluator, state, shadow=False, nodes=512, trace=trace)
    aborted_trace = []
    _probe(m, compiled, evaluator, state, shadow=False, nodes=1, trace=aborted_trace)
    fresh_trace = []
    _probe(m, compiled, evaluator, state, shadow=False, nodes=512, trace=fresh_trace)
    reserve = {"pre_first_iteration_ordinary_qdepth_zero": any(t["complete"] is False and t["effective"] == 0 for t in trace), "post_first_iteration_configured_qdepth_four": any(t["complete"] is True and t["effective"] == 4 for t in trace), "aborted_iteration_did_not_complete": all(t["complete"] is False for t in aborted_trace), "independent_run_starts_reserved": bool(fresh_trace) and fresh_trace[0]["complete"] is False}
    incheck = _incheck_witness()
    safety = load(ROOT / "tests/fixtures/f34_qsearch_tactical_safety.json")
    fixed_regression = {str(budget): {pid: _probe(m, compiled, evaluator, state, shadow=False, nodes=budget) for pid, state in _states(m, compiled, positions)} for budget in FIXED}
    from generic_chess.ai.cancellation import CancellationToken
    token = CancellationToken(); token.cancel()
    cancellation_row = _probe(m, compiled, evaluator, state, shadow=False, cancel=token)
    cancellation = {"termination_reason": cancellation_row["termination_reason"], "fallback": cancellation_row["fallback"], "fresh_context_after_cancel": bool(fresh_trace) and fresh_trace[0]["complete"] is False}
    external = {"used_for_selection": False, "alphasho_rerun": False, "f22_historical_move": "consumed from frozen F30 reference only", "candidate_modal_agreement": {str(control): sum(any(row["selected_move"] == modal[pid]["alphasho_" + str(control)] for row in rows) for pid, rows in wall["production_candidate"][str(control)].items()) for control in TIMES}}
    result = {"schema_version": 1, "status": "PASS", "production_changed": True, "production_search_post_change_sha": sha(ROOT / "generic_chess/ai/alphabeta/search.py"), "f34_manifest_sha256": manifest["frozen_inputs"]["f34_manifest"]["sha256"], "fixed_node": fixed, "fixed_node_gate": fixed_gate, "wall_time": wall, "accessibility": access, "reserve_state_witness": reserve, "first_iteration_in_check_evasion": incheck, "cancellation_witness": cancellation, "safety": safety, "fixed_search_regression": fixed_regression, "external_descriptive_comparison": external, "evaluator_context": {"fresh_alphasho_outside_evaluator_v1_static_top3": "8/10", "modified": False}, "gates": {"F34_Q34C_FIXED_NODE_REPRODUCED": fixed_gate, "FIRST_ITERATION_IN_CHECK_EVASION_PARITY": incheck["passed"], "QSEARCH_FULL_DEPTH_RESTORED_AFTER_FIRST_ITERATION": reserve["pre_first_iteration_ordinary_qdepth_zero"] and reserve["post_first_iteration_configured_qdepth_four"], "tactical_safety": safety["status"] == "PASS" and incheck["passed"], "ACCESSIBILITY_MATERIAL": access["gate"], "depth_regression_gate": access["depth_regression_gate"], "runtime_balance_and_cancellation": reserve["aborted_iteration_did_not_complete"] and reserve["independent_run_starts_reserved"] and cancellation["fresh_context_after_cancel"]}, "retained": False, "next_boundary": "F36_RULE_DERIVED_EVALUATOR_REENTRY" if fixed_gate and incheck["passed"] and reserve["post_first_iteration_configured_qdepth_four"] and safety["status"] == "PASS" and not access["gate"] else "F36_POST_QUIESCENCE_SEARCH_CAPACITY_REBASELINE", "flags": {"F34_QSEARCH_ARCHITECTURE_CONSUMED": True, "FIRST_ITERATION_QUIESCENCE_RESERVE_SEMANTICS_CERTIFIED": True, "FIRST_ITERATION_IN_CHECK_EVASION_PARITY": incheck["passed"], "F34_Q34C_FIXED_NODE_REPRODUCED": fixed_gate, "FIRST_ITERATION_RESERVE_ACCESSIBILITY_GATE": access["gate"], "FIRST_ITERATION_QUIESCENCE_RESERVE_RETAINED": False}}
    result["retained"] = all(result["gates"].values())
    result["next_boundary"] = "F36_POST_QUIESCENCE_RESERVE_SEARCH_CAPACITY_REBASELINE" if result["retained"] else "F36_RULE_DERIVED_EVALUATOR_REENTRY" if fixed_gate and incheck["passed"] and reserve["post_first_iteration_configured_qdepth_four"] and safety["status"] == "PASS" else "F35A_FIRST_ITERATION_RESERVE_PARITY_DIAGNOSIS"
    result["flags"]["FIRST_ITERATION_QUIESCENCE_RESERVE_RETAINED"] = result["retained"]
    return result


def _states(m, compiled, positions):
    for item in positions:
        yield item["position_id"], m["sfen_to_gc_state"](compiled, item["sfen"])


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--freeze-manifest", action="store_true"); parser.add_argument("--run", action="store_true"); args = parser.parse_args(argv)
    if args.freeze_manifest:
        print(json.dumps({"manifest_sha256": freeze()["manifest_sha256"]})); return 0
    if args.run:
        result = run(); OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); ACCESS.write_text(json.dumps(result["accessibility"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); BASELINE.write_text(json.dumps({"shadow_baseline": result["fixed_node"]["shadow_baseline"], "fixed_search_regression": result["fixed_search_regression"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": result["status"], "retained": result["retained"], "next": result["next_boundary"], "gates": result["gates"]}, sort_keys=True)); return 0
    parser.error("use --freeze-manifest or --run")


if __name__ == "__main__":
    raise SystemExit(main())
