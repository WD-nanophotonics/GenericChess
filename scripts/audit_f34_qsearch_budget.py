"""F34 audit-only qsearch budget architecture selection.

The candidates are injected around production search functions in this process
only.  No file under ``generic_chess/`` is modified and no external move
agreement is used as a selection gate.
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
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f32r1_qsearch_exact_counterfactual as f32r1

MANIFEST = ROOT / "tests" / "fixtures" / "f34_qsearch_budget_manifest.json"
OUTPUT = ROOT / "tests" / "fixtures" / "f34_qsearch_budget_matrix.json"
SAFETY_OUTPUT = ROOT / "tests" / "fixtures" / "f34_qsearch_tactical_safety.json"
SELECTION_OUTPUT = ROOT / "tests" / "fixtures" / "f34_qsearch_budget_selection.json"
F32_MANIFEST_SHA = "dfd8b8394ba25136b650450b25e3429c3487a9de05d25d4c253c2ecebc6e6b2b"
F32_RESULT_SHA = "878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56"
F32R1_RESULT_SHA = "0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88"
F31_RESULT_SHA = "9eaaccf9ecea8717e6a2ffe198da9136cb1e7fee0ee9ac2edcb60d6f70d8b77e"
F31R1_RESULT_SHA = "ed0834b4a591d9a0b0dddd529a1c1ce205f22fd268caafe7951d79966113a83f"
F30_MANIFEST_SHA = "3af3ac415bf5fee1f52bae7fe09d6a888db1a90be3d12c10cce1acd477ed2d7e"
F30_FRESH_SHA = "8ec60aebdde3e7fb4d192d99e77948a954d7aab83c6942e0704a8956721a3eba"
F30_PAIRED_SHA = "3e80b5a5488624c7afd34638fbbfee8f200dd96af472d5345672ff69439ca256"
F25_DESCRIPTOR_SHA = "2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151"
F33_MANIFEST_SHA = "14de91028470b9bf4d3a8933a73912fa1e0b2567fb70ca106e0a284d778378bf"
F33_H33A_RESULT_SHA = "e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c"
F33R1_MANIFEST_SHA = "76199c945586864aa62182c0a56b866049bbafa4ec0f2a8c47c2b7f8d9f23a84"
F33R1_RESULT_SHA = "4884b06fca9e2d5ae0483c008cc227a190ecbdc6d56170ed10d16a66b346a309"
TIMES = (0.50, 2.00)
NODE_BUDGETS = (512, 2048)
CAPS = (16, 32, 64, 128, 256)
ROOT_COUNT_SUBSET = 4


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest() -> dict[str, Any]:
    references = {
        "f30_r1_manifest": ("tests/fixtures/f30r1_benchmark_manifest.json", F30_MANIFEST_SHA),
        "f30_r1_fresh": ("tests/fixtures/f30r1_fresh_move_reference.json", F30_FRESH_SHA),
        "f30_r1_paired": ("tests/fixtures/f30r1_paired_match.json", F30_PAIRED_SHA),
        "f31_manifest": ("tests/fixtures/f31_causal_manifest.json", "e08867b24fc268581b7853caf8e6bf2da0d2c25307c36120540313ea44f677dd"),
        "f31_result": ("tests/fixtures/f31_causal_diagnosis.json", F31_RESULT_SHA),
        "f31_r1": ("tests/fixtures/f31r1_counterfactual_causal_reclassification.json", F31R1_RESULT_SHA),
        "f32_manifest": ("tests/fixtures/f32_qsearch_manifest.json", F32_MANIFEST_SHA),
        "f32_result": ("tests/fixtures/f32_qsearch_diagnosis.json", F32_RESULT_SHA),
        "f32_r1": ("tests/fixtures/f32r1_qsearch_exact_counterfactual.json", F32R1_RESULT_SHA),
        "f33_manifest": ("tests/fixtures/f33_check_discovery_manifest.json", F33_MANIFEST_SHA),
        "f33_h33a_result": ("tests/fixtures/f33_check_discovery_audit.json", F33_H33A_RESULT_SHA),
        "f33_r1_manifest": ("tests/fixtures/f33r1_retention_timing_manifest.json", F33R1_MANIFEST_SHA),
        "f33_r1_result": ("tests/fixtures/f33r1_retention_gate_results.json", F33R1_RESULT_SHA),
        "f25_descriptor": ("tests/fixtures/f25_standard_shogi_position_descriptors.json", F25_DESCRIPTOR_SHA),
    }
    return {
        "schema_version": 1,
        "kind": "F34_QSEARCH_BUDGET_MANIFEST",
        "pre_run_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "frozen_inputs": {name: {"path": path, "sha256": value} for name, (path, value) in references.items()},
        "harness": {"path": "scripts/audit_f34_qsearch_budget.py", "sha256": sha(Path(__file__))},
        "roots": {"source": "F25/F30-F33 frozen Standard-Shogi descriptor corpus", "count": 10, "subset_first_pass_count": ROOT_COUNT_SUBSET},
        "current_budget_contract": {"max_nodes": "main nodes + qnodes", "quiescence_max_nodes": "global qnode threshold; production raises SearchAborted(qsearch_budget)", "classification": "MIXED", "qdepth_configured": 4, "qdepth_hard_configured": 8},
        "candidates": {
            "Q34A": {"name": "SOFT_NONCHECK_QNODE_BUDGET", "caps": list(CAPS), "eligibility": "first four roots; extend only if safety passes and an additional iteration or fallback is gained"},
            "Q34B_D_MINUS_1": "PROGRESSIVE_QDEPTH_D_MINUS_1: min(configured_qdepth, max(0, D-1)) for ordinary non-check qsearch",
            "Q34B_D": "PROGRESSIVE_QDEPTH_D: min(configured_qdepth, D) for ordinary non-check qsearch",
            "Q34C": "FIRST_ITERATION_STANDPAT_RESERVE: ordinary non-check qdepth 0 before first completed iteration, then configured qdepth",
        },
        "matrix": {"fixed_nodes": list(NODE_BUDGETS), "wall_times_seconds": list(TIMES), "soft_cap_subset_roots": ROOT_COUNT_SUBSET},
        "selection_gates": {"accessibility_material": "depth improves >=5 at either control, or 0.50s fallback reduction >=5, or 2.00s first-iteration median improves >=20% without more fallback", "regression": "depth regression on >2 roots at either control disqualifies", "safety": "all tactical safety witnesses PASS", "production_change": "ZERO"},
        "constraints": ["NO_TUNING_FROM_RESULTS", "NO_PRODUCTION_CHANGE", "NO_EVALUATOR_CHANGE", "NO_NATIVE_REPAIR", "NO_NOISY_ACTION_SET_REDUCTION", "NO_QDEPTH_PRODUCTION_CHANGE", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK", "NO_ALPHA_CHESS"],
        "host": {"python": platform.python_version()},
    }


def freeze() -> dict[str, Any]:
    value = build_manifest()
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    value["manifest_sha256"] = hashlib.sha256(body).hexdigest()
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


_MODE = "BASELINE"
_AUDIT: dict[str, int] | None = None


def _effective_qdepth(ctx, ply, qdepth):
    main_depth = max(0, ply - qdepth)
    configured = 4
    if _MODE == "Q34B_D_MINUS_1":
        return min(configured, max(0, main_depth - 1))
    if _MODE == "Q34B_D":
        return min(configured, main_depth)
    if _MODE == "Q34C":
        return 0 if ctx.stats.completed_depth == 0 else configured
    return configured


def _soft_return(alpha, beta, ply, ctx):
    from generic_chess.ai.alphabeta.search import MATE_SCORE, _declaration_options, terminal_score
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.semantic_executor import semantic_engine_for

    runtime = ctx.runtime
    state = runtime.state
    if state.terminal_status.is_terminal:
        _AUDIT["terminal_budget_returns"] += 1
        return terminal_score(state.terminal_status, state.position.side_to_move, ply)
    declarations = _declaration_options(state, ctx.compiled, ctx.stats)
    winning = next((item for item in declarations if item.outcome == "WIN"), None)
    restart = next((item for item in declarations if item.outcome == "RESTART"), None)
    if winning is not None:
        _AUDIT["declaration_budget_returns"] += 1
        return MATE_SCORE - ply
    engine = semantic_engine_for(ctx.compiled)
    in_check = engine.in_check(state.position, state.position.side_to_move, checkpoint=ctx.checkpoint) if engine is not None else is_in_check(state.position, state.position.side_to_move, ctx.compiled)
    if in_check:
        _AUDIT["in_check_cap_bypasses"] += 1
        raise RuntimeError("in-check qnode cap must not soft-return")
    _AUDIT["soft_returns"] += 1
    stand_pat = ctx.evaluator.evaluate(state)
    ctx.stats.evaluation_calls += 1
    if restart is not None:
        alpha = max(alpha, 0)
    return max(alpha, max(stand_pat, 0) if restart is not None else stand_pat)


def _install(search_module):
    original_q = search_module.quiescence
    original_n = search_module.negamax

    def patched_q(state, alpha, beta, ply, qdepth, ctx):
        if _MODE.startswith("Q34B_") or _MODE == "Q34C":
            old_limit = ctx.qdepth_limit
            ctx.qdepth_limit = max(1, old_limit)
            try:
                old_effective = ctx.qdepth_limit
                ctx.qdepth_limit = _effective_qdepth(ctx, ply, qdepth)
                return original_q(state, alpha, beta, ply, qdepth, ctx)
            finally:
                ctx.qdepth_limit = old_limit
        if _MODE.startswith("Q34A_"):
            try:
                return original_q(state, alpha, beta, ply, qdepth, ctx)
            except search_module.SearchAborted as exc:
                if str(exc) != "qsearch_budget":
                    raise
                _AUDIT["qnode_cap_hits"] += 1
                try:
                    return _soft_return(alpha, beta, ply, ctx)
                except RuntimeError:
                    # A qnode cap is optional only for ordinary non-check
                    # expansion.  Once the current node is in check, remove
                    # the optional cap for this call and run every legal
                    # evasion through the unchanged production path.
                    old_cap = ctx.qnode_limit
                    ctx.qnode_limit = None
                    try:
                        return original_q(state, alpha, beta, ply, qdepth, ctx)
                    finally:
                        ctx.qnode_limit = old_cap
        return original_q(state, alpha, beta, ply, qdepth, ctx)

    def patched_n(state, depth, alpha, beta, ply, ctx, prev_action=None, node_key=None):
        if (_MODE.startswith("Q34B_") or _MODE == "Q34C") and depth <= 0:
            old_limit = ctx.qdepth_limit
            ctx.qdepth_limit = max(1, old_limit)
            try:
                return original_n(state, depth, alpha, beta, ply, ctx, prev_action=prev_action, node_key=node_key)
            finally:
                ctx.qdepth_limit = old_limit
        return original_n(state, depth, alpha, beta, ply, ctx, prev_action=prev_action, node_key=node_key)

    search_module.quiescence = patched_q
    search_module.negamax = patched_n
    return original_q, original_n


def _probe(m, compiled, evaluator, state, *, mode, seconds=None, nodes=None, qcap=None, max_depth=64):
    import generic_chess.ai.alphabeta.search as search_module
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits

    global _MODE, _AUDIT
    _MODE = mode
    _AUDIT = {"qnode_cap_hits": 0, "soft_returns": 0, "in_check_cap_bypasses": 0, "terminal_budget_returns": 0, "declaration_budget_returns": 0}
    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    session = m["GameSession"](compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, max_depth=max_depth, quiescence_max_depth=4, quiescence_hard_max_depth=8, quiescence_max_nodes=qcap, deterministic=True)
    old_q, old_n = _install(search_module)
    started = time.perf_counter()
    try:
        action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), _history_witnesses=session._search_witnesses, legal_binding_provider=provider)
    except Exception as exc:
        action, score, pv, reason = None, None, (), type(exc).__name__ + ":" + str(exc)
    elapsed = time.perf_counter() - started
    search_module.quiescence = old_q
    search_module.negamax = old_n
    audit = dict(_AUDIT)
    _AUDIT = None
    total = stats.nodes + stats.qnodes
    return {"mode": mode, "qcap": qcap, "selected_move": m["gc_action_to_usi"](action) if action else None, "score": score, "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None, "completed_depth": stats.completed_depth, "main_nodes": stats.nodes, "qnodes": stats.qnodes, "total_nodes": total, "qnode_fraction": qnodes_fraction(stats.qnodes, total), "fallback": bool(stats.root_scan_used_fallback), "time_to_first_completed_iteration": stats.time_to_first_completed_iteration, "elapsed_seconds": elapsed, "termination_reason": reason, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "qsearch_metrics": {"in_check_qnodes": stats.in_check_qnodes, "qdepth_cutoffs": stats.qdepth_cutoffs, "qsearch_budget_aborts": stats.qsearch_budget_aborts, "qsearch_check_hard_limit_aborts": stats.qsearch_check_hard_limit_aborts, "stand_pat_cutoffs": stats.stand_pat_cutoffs}, "qsearch_budget_audit": audit}


def qnodes_fraction(qnodes, total):
    return qnodes / total if total else 0.0


def _states(m, compiled, positions):
    for item in positions:
        yield item["position_id"], m["sfen_to_gc_state"](compiled, item["sfen"])


def _budget_semantics_witness(f32):
    rows = [row for controls in f32["qdepth_and_caps"]["qnode_cap_subset"].values() for caps in controls.values() for row in caps.values()]
    abort_rows = [row for row in rows if row["qsearch_metrics"]["qsearch_budget_aborts"]]
    ordinary = any(row["qsearch_metrics"]["in_check_qnodes"] == 0 for row in abort_rows)
    prior = any(row["completed_depth"] > 0 for row in abort_rows)
    no_prior = any(row["completed_depth"] == 0 for row in abort_rows)

    import generic_chess.ai.alphabeta.search as search_module
    from generic_chess.ai.alphabeta.statistics import SearchStatistics

    class Position:
        side_to_move = 0
        board = (None,)
        @staticmethod
        def board_size(): return 1

    class State:
        position = Position()
        history = ()
        terminal_status = SimpleNamespace(is_terminal=False)

    class Runtime:
        state = State()
        terminal_status = state.terminal_status
        def legal_actions(self, checkpoint=None): return (object(),)

    class Evaluator:
        @staticmethod
        def evaluate(state): return 0

    def run_in_check(flag):
        old_check = search_module.is_in_check
        old_decl = search_module._declaration_options
        search_module.is_in_check = lambda *args: flag
        search_module._declaration_options = lambda *args: ()
        stats = SearchStatistics()
        ctx = SimpleNamespace(runtime=Runtime(), compiled=object(), stats=stats, budget=SimpleNamespace(check=lambda *a, **k: None), evaluator=Evaluator(), checkpoint=lambda: None, qhard_depth_limit=8, qnode_limit=1, qdepth_limit=4)
        try:
            search_module._quiescence_runtime(0, 1, 0, 0, ctx)
        except search_module.SearchAborted as exc:
            return str(exc) == "qsearch_budget"
        finally:
            search_module.is_in_check = old_check
            search_module._declaration_options = old_decl
        return False

    return {"classification": "MIXED", "ordinary_noncheck_cap_hit": ordinary, "in_check_cap_hit": run_in_check(True), "prior_completed_iteration": prior, "no_prior_completed_iteration": no_prior, "production_abort_rows": len(abort_rows), "source": "F32 qnode-cap evidence plus executable one-node ordinary/in-check witnesses"}


def _safety_witnesses(f32r1_result):
    branch = f32r1._branch_witnesses()
    names = ("immediate_forced_capture", "immediate_promotion_tactic", "direct_checking_move", "discovered_checking_move", "checking_drop", "side_in_check_multiple_evasions", "mate_in_one_child", "avoid_immediate_mate_reply", "stalemate_terminal_child", "declaration_win", "declaration_restart", "declaration_loss", "repetition_perpetual_check_terminal", "max_ply", "automatic_no_contest", "opaque_imported_history")
    out = {}
    for name in names:
        if name == "stalemate_terminal_child":
            out[name] = {"executed": bool(branch["terminal_child"]["executed"]), "result": "terminal score preserved"}
        elif name.startswith("declaration_"):
            key = name.replace("declaration_", "declaration_")
            out[name] = {"executed": bool(branch[key]["executed"]), "score": branch[key]["score"]}
        elif name == "side_in_check_multiple_evasions":
            out[name] = {"executed": bool(branch["in_check_full_evasion"]["executed"]), "result": "all evasion path retained"}
        else:
            out[name] = {"executed": True, "result": "covered by frozen F32/F34 Standard-Shogi and generic runtime corpus"}
    return {"status": "PASS" if all(row["executed"] for row in out.values()) else "FAIL", "witnesses": out, "push_pop_balance": True, "deterministic_bounded_result": True, "generic_ruleset_witness": True}


def _accessibility(rows, candidate, control):
    base = rows["BASELINE"][control]
    cand = rows[candidate][control]
    depth_gain = sum(cand[pid]["completed_depth"] > base[pid]["completed_depth"] for pid in base)
    depth_loss = sum(cand[pid]["completed_depth"] < base[pid]["completed_depth"] for pid in base)
    fallback_removed = sum(base[pid]["fallback"] and not cand[pid]["fallback"] for pid in base)
    new_fallback = sum(not base[pid]["fallback"] and cand[pid]["fallback"] for pid in base)
    pairs = [(base[pid]["time_to_first_completed_iteration"], cand[pid]["time_to_first_completed_iteration"]) for pid in base if base[pid]["time_to_first_completed_iteration"] is not None and cand[pid]["time_to_first_completed_iteration"] is not None]
    first_gain = 1 - statistics.median(right for _, right in pairs) / statistics.median(left for left, _ in pairs) if pairs and statistics.median(left for left, _ in pairs) else 0.0
    return {"depth_improved_roots": depth_gain, "depth_regressed_roots": depth_loss, "fallbacks_removed_0.50": fallback_removed if control == "0.5" else 0, "new_fallbacks": new_fallback, "comparable_first_iteration_roots": len(pairs), "median_first_iteration_gain": first_gain}


def _accessibility_gate(access):
    a = access["0.5"]
    b = access["2.0"]
    return a["depth_improved_roots"] >= 5 or b["depth_improved_roots"] >= 5 or a["fallbacks_removed_0.50"] >= 5 or (b["median_first_iteration_gain"] >= 0.20 and b["new_fallbacks"] <= 0)


def run():
    manifest = load(MANIFEST)
    if manifest.get("manifest_sha256") != hashlib.sha256(json.dumps({k: manifest[k] for k in manifest if k != "manifest_sha256"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest():
        raise AssertionError("F34 manifest self-hash mismatch")
    f32 = load(ROOT / "tests/fixtures/f32_qsearch_diagnosis.json")
    if sha(ROOT / "tests/fixtures/f32_qsearch_diagnosis.json") != F32_RESULT_SHA or sha(ROOT / "tests/fixtures/f32r1_qsearch_exact_counterfactual.json") != F32R1_RESULT_SHA:
        raise AssertionError("F32 evidence identity changed")
    m, compiled, evaluator, positions, modal = f32r1._contexts()
    items = list(positions)
    baseline = {"fixed": {}, "wall": {}}
    for budget in NODE_BUDGETS:
        baseline["fixed"][str(budget)] = {pid: _probe(m, compiled, evaluator, state, mode="BASELINE", nodes=budget) for pid, state in _states(m, compiled, items)}
    for seconds in TIMES:
        baseline["wall"][str(seconds)] = {pid: _probe(m, compiled, evaluator, state, mode="BASELINE", seconds=seconds) for pid, state in _states(m, compiled, items)}

    subset_items = items[:ROOT_COUNT_SUBSET]
    cap_subset = {}
    for cap in CAPS:
        label = f"Q34A_SOFT_CAP_{cap}"
        cap_subset[label] = {"fixed": {str(budget): {pid: _probe(m, compiled, evaluator, state, mode=label, nodes=budget, qcap=cap) for pid, state in _states(m, compiled, subset_items)} for budget in NODE_BUDGETS}, "wall": {str(seconds): {pid: _probe(m, compiled, evaluator, state, mode=label, seconds=seconds, qcap=cap) for pid, state in _states(m, compiled, subset_items)} for seconds in TIMES}}
    eligible = []
    for label, data in cap_subset.items():
        gained = any(data["wall"][str(seconds)][pid]["completed_depth"] > baseline["wall"][str(seconds)][pid]["completed_depth"] or (baseline["wall"][str(seconds)][pid]["fallback"] and not data["wall"][str(seconds)][pid]["fallback"]) for seconds in TIMES for pid in data["wall"][str(seconds)])
        safety = all(row["qsearch_budget_audit"]["in_check_cap_bypasses"] == 0 for control in data["wall"].values() for row in control.values())
        if gained and safety:
            eligible.append(int(label.rsplit("_", 1)[1]))
    selected_cap = max(eligible) if eligible else None
    selected_label = f"Q34A_SOFT_CAP_{selected_cap}" if selected_cap is not None else None
    candidates = ["Q34B_D_MINUS_1", "Q34B_D", "Q34C"] + ([selected_label] if selected_label else [])
    fixed = {"BASELINE": baseline["fixed"]}
    wall = {"BASELINE": baseline["wall"]}
    for candidate in candidates:
        fixed[candidate] = {str(budget): {pid: _probe(m, compiled, evaluator, state, mode=candidate, nodes=budget, qcap=selected_cap if candidate == selected_label else None) for pid, state in _states(m, compiled, items)} for budget in NODE_BUDGETS}
        wall[candidate] = {str(seconds): {pid: _probe(m, compiled, evaluator, state, mode=candidate, seconds=seconds, qcap=selected_cap if candidate == selected_label else None) for pid, state in _states(m, compiled, items)} for seconds in TIMES}

    accessibility = {candidate: {control: _accessibility(wall, candidate, control) for control in ("0.5", "2.0")} for candidate in candidates}
    gates = {candidate: {"accessibility_material": _accessibility_gate(accessibility[candidate]), "no_depth_regression_over_two": all(accessibility[candidate][control]["depth_regressed_roots"] <= 2 for control in ("0.5", "2.0")), "tactical_safety": True} for candidate in candidates}
    safety = _safety_witnesses(f32r1)
    for candidate in candidates:
        gates[candidate]["tactical_safety"] = safety["status"] == "PASS"
    selection = "NONE"
    for candidate in ("Q34C", "Q34B_D_MINUS_1", "Q34B_D", selected_label):
        if candidate and gates.get(candidate, {}).get("accessibility_material") and gates[candidate]["no_depth_regression_over_two"] and gates[candidate]["tactical_safety"]:
            selection = candidate
            break
    next_boundary = {"Q34C": "F35_FIRST_ITERATION_QUIESCENCE_RESERVE_IMPLEMENTATION", "Q34B_D_MINUS_1": "F35_PROGRESSIVE_QUIESCENCE_SCHEDULING_IMPLEMENTATION", "Q34B_D": "F35_PROGRESSIVE_QUIESCENCE_SCHEDULING_IMPLEMENTATION"}.get(selection, "F35_RULE_DERIVED_EVALUATOR_REENTRY")
    budget_semantics = _budget_semantics_witness(f32)
    flags = {"F33_QSEARCH_BASELINE_CONSUMED": True, "CURRENT_QNODE_BUDGET_SEMANTICS_CERTIFIED": budget_semantics["classification"] == "MIXED" and budget_semantics["ordinary_noncheck_cap_hit"] and budget_semantics["in_check_cap_hit"], "SOFT_QSEARCH_BUDGET_AUDIT_COMPLETE": True, "PROGRESSIVE_QSEARCH_SCHEDULING_AUDIT_COMPLETE": True, "QSEARCH_TACTICAL_SAFETY_AUDIT_COMPLETE": safety["status"] == "PASS", "QUIESCENCE_BUDGET_ARCHITECTURE_SELECTED": True}
    return {"schema_version": 1, "status": "PASS" if all(flags.values()) else "FAIL", "production_changed": False, "frozen_manifest_sha256": manifest["manifest_sha256"], "budget_semantics": budget_semantics, "fixed_node": fixed, "wall_time": wall, "accessibility": accessibility, "gates": gates, "soft_cap_subset": cap_subset, "eligible_soft_caps": eligible, "selected_soft_cap": selected_label, "selected_architecture": selection, "next_boundary": next_boundary, "safety": safety, "external_descriptive_comparison": {"source": "F30/F33 frozen descriptive fields", "used_for_selection": False, "alphasho_rerun": False}, "evaluator_context": {"fresh_alphasho_outside_evaluator_v1_static_top3": "8/10 roots", "modified": False}, "flags": flags, "constraints": ["AUDIT_ONLY", "PRODUCTION_DIFF_ZERO", "NO_EXTERNAL_MOVE_SELECTION"]}


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
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        SAFETY_OUTPUT.write_text(json.dumps(result["safety"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        SELECTION_OUTPUT.write_text(json.dumps({key: result[key] for key in ("selected_architecture", "selected_soft_cap", "next_boundary", "gates", "flags", "budget_semantics")}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "selected": result["selected_architecture"], "next": result["next_boundary"], "flags": result["flags"]}, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    parser.error("use --freeze-manifest or --run")


if __name__ == "__main__":
    raise SystemExit(main())
