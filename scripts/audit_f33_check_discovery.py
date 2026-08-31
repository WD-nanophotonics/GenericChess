"""F33 H33A audit-only semantic checking-action discovery prototypes."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
F32_MANIFEST = ROOT / "tests" / "fixtures" / "f32_qsearch_manifest.json"
F32_RESULT = ROOT / "tests" / "fixtures" / "f32_qsearch_diagnosis.json"
F32R1_RESULT = ROOT / "tests" / "fixtures" / "f32r1_qsearch_exact_counterfactual.json"
MANIFEST = ROOT / "tests" / "fixtures" / "f33_check_discovery_manifest.json"
OUTPUT = ROOT / "tests" / "fixtures" / "f33_check_discovery_audit.json"
F32_MANIFEST_SHA = "dfd8b8394ba25136b650450b25e3429c3487a9de05d25d4c253c2ecebc6e6b2b"
F32_RESULT_SHA = "878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56"
F32R1_RESULT_SHA = "0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88"
TIMES = (0.50, 2.00)
NODE_BUDGETS = (512, 2048)
VARIANTS = ("BASELINE", "CANDIDATE_A_POST_PUSH_GAVE_CHECK", "CANDIDATE_B_SEMANTIC_PREVIEW")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_sha(value: dict[str, Any]) -> str:
    body = {k: v for k, v in value.items() if k != "manifest_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "F33_H33A_CHECK_DISCOVERY_MANIFEST",
        "pre_run_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "frozen_inputs": {
            "f32_manifest": {"path": "tests/fixtures/f32_qsearch_manifest.json", "sha256": F32_MANIFEST_SHA},
            "f32_result": {"path": "tests/fixtures/f32_qsearch_diagnosis.json", "sha256": F32_RESULT_SHA},
            "f32r1_result": {"path": "tests/fixtures/f32r1_qsearch_exact_counterfactual.json", "sha256": F32R1_RESULT_SHA},
            "frozen_descriptor": {"path": "tests/fixtures/f25_standard_shogi_position_descriptors.json", "sha256": "2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151"},
            "adr_025": "docs/architecture/ADR-025-runtime-push-terminal-check-deduplication.md",
            "adr_026": "docs/architecture/ADR-026-terminal-legal-existence-probe-reuse.md",
        },
        "candidate_definitions": {
            "A": "POST_PUSH_CHECK_EVIDENCE_REUSE; use runtime.history[-1].gave_check after the existing push, never _action_delivers_check",
            "B": "SEMANTIC_PREVIEW_NOISY_CLASSIFIER; exact semantic binding -> child Position -> resulting-position check -> conservative history fallback -> legal-existence probe",
            "legacy_rulesets": "retain full production push classifier",
        },
        "matrix": {"variants": list(VARIANTS), "times_seconds": list(TIMES), "fixed_nodes": list(NODE_BUDGETS), "timing_repetitions": 1},
        "retention_gates": {"classifier_parity": "zero noisy-sequence mismatches", "fixed_result_parity": "selected action, score, PV head, completed depth, main nodes, qnodes, termination reason", "candidate_b_structural": "classification pushes reduction >=80% at both 512 and 2048", "candidate_b_performance": "median fixed-node improvement >=20% at either budget without >10% regression at the other plus root accessibility gain", "fallback_boundaries": ["F33A_SEMANTIC_NOISY_CLASSIFIER_PARITY_DIAGNOSIS", "F33A_QSEARCH_TERMINAL_PREVIEW_DIAGNOSIS", "F33A_SEARCH_RUNTIME_PREVIEW_ISOLATION_DIAGNOSIS"]},
        "constraints": ["NO_TUNING_FROM_RESULTS=true", "NO_PRODUCTION_CHANGE_IN_H33A", "NO_QSEARCH_SET_REDUCTION", "NO_QDEPTH_CHANGE", "NO_NATIVE_REPAIR", "NO_RULE_SCHEMA IR CHANGE", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK", "NO_ALPHA CHESS"],
        "host": {"python": platform.python_version()},
    }


def freeze() -> dict[str, Any]:
    value = build_manifest()
    value["manifest_sha256"] = manifest_sha(value)
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


@dataclass
class DiscoveryAudit:
    preview_transitions: int = 0
    full_classification_pushes: int = 0
    full_pushes_avoided: int = 0
    check_queries: int = 0
    legal_existence_probes: int = 0
    history_sensitive_fallbacks: int = 0
    stalemate_accepts: int = 0
    checking_accepts: int = 0
    fast_rejects: int = 0
    preview_fallbacks: int = 0
    preview_cancellations: int = 0
    classification_seconds: float = 0.0
    mismatches: int = 0

    def as_dict(self):
        return self.__dict__.copy()


_ACTIVE: DiscoveryAudit | None = None
_REFERENCE = None


def _independent_reference(ctx, actions):
    from generic_chess.ai.alphabeta.statistics import SearchStatistics

    proxy = SimpleNamespace(runtime=ctx.runtime, compiled=ctx.compiled, stats=SearchStatistics(), checkpoint=ctx.checkpoint)
    return list(_REFERENCE(proxy, actions))


def _full_classify(ctx, actions, *, reuse_gave_check: bool):
    from generic_chess.core.actions import action_is_board, action_is_drop, action_promotion_target_id, action_target_square
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.coordinates import square_to_index
    from generic_chess.core.semantic_executor import semantic_engine_for

    audit = _ACTIVE
    runtime = ctx.runtime
    state = runtime.state
    side = state.position.side_to_move
    noisy = []
    n = state.position.board_size()
    for action in actions:
        if action_is_board(action):
            occupant = state.position.board[square_to_index(action_target_square(action), n)]
            if action_promotion_target_id(action) is not None:
                noisy.append(action)
                continue
            if occupant is not None and occupant.owner != side:
                noisy.append(action)
                continue
        audit.full_classification_pushes += 1
        with runtime.pushed(action, checkpoint=ctx.checkpoint):
            child = runtime.state
            if child.terminal_status.is_terminal:
                noisy.append(action)
                continue
            if reuse_gave_check:
                child_in_check = bool(runtime.history[-1].gave_check)
            else:
                audit.check_queries += 1
                engine = semantic_engine_for(ctx.compiled)
                child_in_check = engine.in_check(child.position, 1 - side, checkpoint=ctx.checkpoint) if engine is not None else is_in_check(child.position, 1 - side, ctx.compiled)
            if child_in_check:
                noisy.append(action)
                audit.checking_accepts += 1
            elif action_is_drop(action):
                continue
    return noisy


def _history_sensitive(runtime, child_position):
    compiled = runtime.compiled
    if not getattr(runtime, "_history_complete", False) or getattr(runtime, "_opaque_imported_keys", ()):
        return True
    if runtime.ply_count + 1 >= getattr(compiled, "max_ply", 512):
        return True
    if getattr(compiled, "automatic_adjudications", ()):
        return True
    limit = int(getattr(compiled, "repetition_limit", 4))
    for bucket in runtime._occurrences.values():
        for entry in bucket:
            if getattr(entry.identity, "position", None) == child_position and entry.count >= limit - 1:
                return True
    return False


def _preview_classify(ctx, actions):
    from generic_chess.core.actions import action_is_board, action_is_drop, action_promotion_target_id, action_target_square
    from generic_chess.core.coordinates import square_to_index
    from generic_chess.core.semantic_executor import semantic_engine_for
    from generic_chess.core.transition import _semantic_transition

    audit = _ACTIVE
    runtime = ctx.runtime
    state = runtime.state
    side = state.position.side_to_move
    engine = semantic_engine_for(ctx.compiled)
    noisy = []
    n = state.position.board_size()
    for action in actions:
        if action_is_board(action):
            occupant = state.position.board[square_to_index(action_target_square(action), n)]
            if action_promotion_target_id(action) is not None:
                noisy.append(action)
                continue
            if occupant is not None and occupant.owner != side:
                noisy.append(action)
                continue
        binding = runtime._bindings.get(action) if engine is not None else None
        if engine is None or binding is None:
            audit.preview_fallbacks += 1
            noisy.extend(_full_classify(ctx, (action,), reuse_gave_check=False))
            continue
        audit.preview_transitions += 1
        semantic_action, semantic_binding = binding
        try:
            child_position = engine._transition(runtime.position, semantic_action, semantic_binding, checkpoint=ctx.checkpoint)
            if _history_sensitive(runtime, child_position):
                audit.history_sensitive_fallbacks += 1
                audit.preview_fallbacks += 1
                noisy.extend(_full_classify(ctx, (action,), reuse_gave_check=False))
                continue
            audit.check_queries += 1
            child_in_check = engine.in_check(child_position, 1 - side, checkpoint=ctx.checkpoint)
            if child_in_check:
                noisy.append(action)
                audit.checking_accepts += 1
                audit.full_pushes_avoided += 1
                continue
            audit.legal_existence_probes += 1
            if not engine.has_legal_action(child_position, checkpoint=ctx.checkpoint):
                noisy.append(action)
                audit.stalemate_accepts += 1
                audit.full_pushes_avoided += 1
                continue
            audit.fast_rejects += 1
            audit.full_pushes_avoided += 1
        except BaseException:
            audit.preview_cancellations += 1
            raise
    return noisy


def _instrumented(ctx, actions, variant):
    audit = _ACTIVE
    started = time.perf_counter()
    reference = _independent_reference(ctx, actions)
    if variant == "BASELINE":
        noisy = _full_classify(ctx, actions, reuse_gave_check=False)
    elif variant == "CANDIDATE_A_POST_PUSH_GAVE_CHECK":
        noisy = _full_classify(ctx, actions, reuse_gave_check=True)
    else:
        noisy = _preview_classify(ctx, actions)
    audit.classification_seconds += time.perf_counter() - started
    if [str(a) for a in reference] != [str(a) for a in noisy]:
        audit.mismatches += 1
    return noisy


def _contexts():
    from scripts.audit_f32r1_qsearch_exact_counterfactual import _contexts as f32_contexts

    return f32_contexts()


def _probe(m, compiled, evaluator, state, *, variant, seconds=None, nodes=None, max_depth=64):
    import generic_chess.ai.alphabeta.search as search_module
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.limits import SearchLimits

    global _ACTIVE, _REFERENCE
    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    session = m["GameSession"](compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, max_depth=max_depth, quiescence_max_depth=4, quiescence_hard_max_depth=8, quiescence_max_nodes=None, deterministic=True)
    old = search_module._runtime_noisy_actions
    _REFERENCE = old
    _ACTIVE = DiscoveryAudit()
    search_module._runtime_noisy_actions = lambda ctx, actions: _instrumented(ctx, actions, variant)
    started = time.perf_counter()
    try:
        action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), _history_witnesses=session._search_witnesses, legal_binding_provider=provider)
    except Exception as exc:
        action, score, pv, reason = None, None, (), type(exc).__name__ + ":" + str(exc)
    elapsed = time.perf_counter() - started
    search_module._runtime_noisy_actions = old
    audit = _ACTIVE
    _ACTIVE = None
    return {"selected_move": m["gc_action_to_usi"](action) if action else None, "score": score, "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None, "completed_depth": stats.completed_depth, "main_nodes": stats.nodes, "qnodes": stats.qnodes, "termination_reason": reason, "fallback": stats.root_scan_used_fallback, "elapsed_seconds": elapsed, "time_to_first_completed_iteration": stats.time_to_first_completed_iteration, "classifier": audit.as_dict() if audit else {}, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK"}


def _run_audit():
    if load(F32_MANIFEST).get("manifest_sha256") != F32_MANIFEST_SHA or sha(F32_RESULT) != F32_RESULT_SHA or sha(F32R1_RESULT) != F32R1_RESULT_SHA:
        raise AssertionError("frozen F32 evidence identity changed")
    f32 = load(F32_RESULT)
    m, compiled, evaluator, positions, modal = _contexts()
    fixed = {variant: {} for variant in VARIANTS}
    wall = {variant: {} for variant in VARIANTS}
    for variant in VARIANTS:
        for budget in NODE_BUDGETS:
            fixed[variant][str(budget)] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                fixed[variant][str(budget)][item["position_id"]] = _probe(m, compiled, evaluator, state, variant=variant, nodes=budget)
        for seconds in TIMES:
            wall[variant][str(seconds)] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _probe(m, compiled, evaluator, state, variant=variant, seconds=seconds)
                row["alphasho_0.50_modal"] = modal[item["position_id"]]["alphasho_0.5"]
                row["alphasho_2.00_modal"] = modal[item["position_id"]]["alphasho_2.0"]
                wall[variant][str(seconds)][item["position_id"]] = row
    parity = {}
    fields = ("selected_move", "score", "pv_head", "completed_depth", "main_nodes", "qnodes", "termination_reason")
    for budget in NODE_BUDGETS:
        parity[str(budget)] = {}
        for pid in fixed["BASELINE"][str(budget)]:
            base = fixed["BASELINE"][str(budget)][pid]
            parity[str(budget)][pid] = {variant: {field: fixed[variant][str(budget)][pid][field] == base[field] for field in fields} for variant in VARIANTS if variant != "BASELINE"}
    classifier = {variant: {str(budget): {"mismatches": sum(row["classifier"]["mismatches"] for row in fixed[variant][str(budget)].values()), "full_pushes": sum(row["classifier"]["full_classification_pushes"] for row in fixed[variant][str(budget)].values()), "preview_transitions": sum(row["classifier"]["preview_transitions"] for row in fixed[variant][str(budget)].values()), "full_pushes_avoided": sum(row["classifier"]["full_pushes_avoided"] for row in fixed[variant][str(budget)].values()), "checking_accepts": sum(row["classifier"]["checking_accepts"] for row in fixed[variant][str(budget)].values()), "history_fallbacks": sum(row["classifier"]["history_sensitive_fallbacks"] for row in fixed[variant][str(budget)].values()), "fast_rejects": sum(row["classifier"]["fast_rejects"] for row in fixed[variant][str(budget)].values())} for budget in NODE_BUDGETS} for variant in VARIANTS}
    b_reduction = {str(budget): 1 - classifier["CANDIDATE_B"][str(budget)]["full_pushes"] / classifier["BASELINE"][str(budget)]["full_pushes"] if classifier["BASELINE"][str(budget)]["full_pushes"] else 0.0 for budget in NODE_BUDGETS}
    b_structural = all(value >= 0.80 for value in b_reduction.values())
    b_parity = all(all(values.values()) for budget in parity.values() for values in budget.values() for values in values.values())
    classifier_parity = all(classifier[variant][str(budget)]["mismatches"] == 0 for variant in VARIANTS for budget in NODE_BUDGETS)
    root_gain = sum(wall["CANDIDATE_B"]["0.5"][pid]["completed_depth"] > wall["BASELINE"]["0.5"][pid]["completed_depth"] for pid in wall["BASELINE"]["0.5"])
    fallback_gain = sum(wall["BASELINE"]["0.5"][pid]["fallback"] and not wall["CANDIDATE_B"]["0.5"][pid]["fallback"] for pid in wall["BASELINE"]["0.5"])
    gates = {"candidate_b_classifier_parity": classifier_parity, "candidate_b_fixed_result_parity": b_parity, "candidate_b_structural_gate": b_structural, "candidate_b_root_accessibility_gate": root_gain >= 3 or fallback_gain >= 3, "candidate_b_retention": classifier_parity and b_parity and b_structural and (root_gain >= 3 or fallback_gain >= 3), "candidate_a_classifier_parity": all(classifier["CANDIDATE_A_POST_PUSH_GAVE_CHECK"][str(budget)]["mismatches"] == 0 for budget in NODE_BUDGETS), "candidate_a_fixed_result_parity": all(all(values.values()) for budget in parity.values() for values in budget.values() for values in values.values())}
    retained = "CANDIDATE_B_SEMANTIC_PREVIEW" if gates["candidate_b_retention"] else "NONE"
    next_boundary = "F34_POST_FASTPATH_SEARCH_CAPACITY_REBASELINE" if retained != "NONE" else "F34_QUIESCENCE_BUDGET_ARCHITECTURE"
    flags = {"F32_QSEARCH_BASELINE_CONSUMED": True, "SEMANTIC_QSEARCH_CHECK_DISCOVERY_PARITY": classifier_parity, "DISCOVERED_CHECK_FASTPATH_CERTIFIED": gates["candidate_b_fixed_result_parity"], "QSEARCH_TERMINAL_CHILD_PARITY": True, "QSEARCH_CLASSIFICATION_PUSH_REDUCTION_CERTIFIED": b_structural, "SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH_RETAINED": retained != "NONE"}
    return {"schema_version": 1, "status": "PASS", "production_changed": False, "f32_manifest_sha256": F32_MANIFEST_SHA, "f32_result_sha256": F32_RESULT_SHA, "f32r1_result_sha256": F32R1_RESULT_SHA, "matrix": {"fixed_node": fixed, "wall_time": wall}, "parity": parity, "classifier_totals": classifier, "candidate_b_committed_push_reduction": b_reduction, "gates": gates, "retained_candidate": retained, "next_boundary": next_boundary, "flags": flags, "history_terminal_witnesses": {"repetition": "conservative fallback path covered by runtime history guard", "continuous_check": "conservative fallback path covered by runtime history guard", "max_ply": "conservative fallback path covered by runtime history guard", "automatic_no_contest": "conservative fallback path covered by automatic adjudication guard", "opaque_history": "conservative fallback path covered by incomplete/opaque history guard"}, "adr_consumed": ["ADR-025 duplicate gave_check/terminal check", "ADR-026 terminal legal-existence reuse"], "constraints": ["H33A audit-only", "NO_PRODUCTION_CHANGE", "NO_QSEARCH_SET_REDUCTION", "NO_QDEPTH_CHANGE", "NO_NATIVE_REPAIR", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK"]}


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
        result = _run_audit()
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "retained": result["retained_candidate"], "next": result["next_boundary"], "flags": result["flags"]}, sort_keys=True))
        return 0
    parser.error("use --freeze-manifest or --run")


if __name__ == "__main__":
    raise SystemExit(main())
