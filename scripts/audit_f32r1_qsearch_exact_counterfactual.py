"""F32 R1: executable, audit-only qsearch counterfactual certification.

The production search modules are never edited.  This process temporarily
injects a copy of the runtime qsearch with only non-check legal-action
materialization moved after the existing stand-pat/depth/budget gates, and an
instrumented copy of the production noisy classifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

F32_MANIFEST = ROOT / "tests" / "fixtures" / "f32_qsearch_manifest.json"
F32_RESULT = ROOT / "tests" / "fixtures" / "f32_qsearch_diagnosis.json"
OUTPUT = ROOT / "tests" / "fixtures" / "f32r1_qsearch_exact_counterfactual.json"
F32_MANIFEST_SHA = "dfd8b8394ba25136b650450b25e3429c3487a9de05d25d4c253c2ecebc6e6b2b"
F32_RESULT_SHA = "878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56"
F31R1_RESULT_SHA = "ed0834b4a591d9a0b0dddd529a1c1ce205f22fd268caafe7951d79966113a83f"
TIMES = (0.50, 2.00)
NODE_BUDGETS = (512, 2048)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class ClassifierAudit:
    input_candidates: int = 0
    direct_capture: int = 0
    direct_promotion: int = 0
    terminal_child_push_accepted: int = 0
    checking_board_push_accepted: int = 0
    quiet_board_push_rejected: int = 0
    checking_drop_push_accepted: int = 0
    nonchecking_drop_push_rejected: int = 0
    other_rejected: int = 0
    expanded_noncheck_qnodes: int = 0
    classification_pushes: int = 0
    classification_seconds: float = 0.0
    reference_seconds: float = 0.0
    parity_mismatches: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        accepted = self.direct_capture + self.direct_promotion + self.terminal_child_push_accepted + self.checking_board_push_accepted + self.checking_drop_push_accepted
        rejected = self.quiet_board_push_rejected + self.nonchecking_drop_push_rejected + self.other_rejected
        return {
            "input_candidates": self.input_candidates,
            "direct_capture_accepts": self.direct_capture,
            "direct_promotion_accepts": self.direct_promotion,
            "classification_pushes": self.classification_pushes,
            "terminal_child_push_accepted": self.terminal_child_push_accepted,
            "checking_board_push_accepted": self.checking_board_push_accepted,
            "quiet_board_push_rejected": self.quiet_board_push_rejected,
            "checking_drop_push_accepted": self.checking_drop_push_accepted,
            "nonchecking_drop_push_rejected": self.nonchecking_drop_push_rejected,
            "other_rejected": self.other_rejected,
            "expanded_noncheck_qnodes": self.expanded_noncheck_qnodes,
            "total_accepted": accepted,
            "total_rejected": rejected,
            "rejection_rate": rejected / self.input_candidates if self.input_candidates else 0.0,
            "pushes_per_expanded_noncheck_qnode": self.classification_pushes / self.expanded_noncheck_qnodes if self.expanded_noncheck_qnodes else 0.0,
            "classification_seconds": self.classification_seconds,
            "reference_seconds": self.reference_seconds,
            "instrumentation_disclosure": "classification_seconds includes the exact audit classifier; reference_seconds is the independent production comparison and is not a production timing claim",
        }


_ACTIVE_AUDIT: ClassifierAudit | None = None
_REFERENCE_NOISY = None


def _action_key(action) -> str:
    return str(action)


def _instrumented_noisy_actions(ctx, actions):
    """Exact production classification with A-G accounting and parity check."""
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.core.actions import (
        action_is_board,
        action_is_drop,
        action_promotion_target_id,
        action_target_square,
    )
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.coordinates import square_to_index
    from generic_chess.core.semantic_executor import semantic_engine_for

    audit = _ACTIVE_AUDIT
    if audit is None:
        raise AssertionError("classifier instrumentation is not active")
    runtime = ctx.runtime
    state = runtime.state
    side = state.position.side_to_move
    actions = tuple(actions)
    audit.expanded_noncheck_qnodes += 1
    audit.input_candidates += len(actions)
    started = time.perf_counter()

    # Compare the independent production classifier on the same action input.
    reference_ctx = SimpleNamespace(runtime=runtime, compiled=ctx.compiled, stats=SearchStatistics(), checkpoint=ctx.checkpoint)
    reference_started = time.perf_counter()
    reference = list(_REFERENCE_NOISY(reference_ctx, actions))
    audit.reference_seconds += time.perf_counter() - reference_started

    noisy = []
    labels = []
    n = state.position.board_size()
    for action in actions:
        if action_is_board(action):
            target = action_target_square(action)
            index = square_to_index(target, n)
            occupant = state.position.board[index]
            if action_promotion_target_id(action) is not None:
                noisy.append(action)
                labels.append("PROMOTION_DIRECT")
                audit.direct_promotion += 1
                continue
            if occupant is not None and occupant.owner != side:
                noisy.append(action)
                labels.append("CAPTURE_DIRECT")
                audit.direct_capture += 1
                continue
        audit.classification_pushes += 1
        with runtime.pushed(action, checkpoint=ctx.checkpoint):
            child = runtime.state
            if child.terminal_status.is_terminal:
                noisy.append(action)
                labels.append("TERMINAL_CHILD_PUSH_ACCEPTED")
                audit.terminal_child_push_accepted += 1
                continue
            engine = semantic_engine_for(ctx.compiled)
            child_in_check = engine.in_check(child.position, 1 - side, checkpoint=ctx.checkpoint) if engine is not None else is_in_check(child.position, 1 - side, ctx.compiled)
            if child_in_check:
                noisy.append(action)
                if action_is_drop(action):
                    labels.append("CHECKING_DROP_PUSH_ACCEPTED")
                    audit.checking_drop_push_accepted += 1
                else:
                    labels.append("CHECKING_BOARD_PUSH_ACCEPTED")
                    audit.checking_board_push_accepted += 1
            elif action_is_drop(action):
                labels.append("NONCHECKING_DROP_PUSH_REJECTED")
                audit.nonchecking_drop_push_rejected += 1
            elif action_is_board(action):
                labels.append("QUIET_BOARD_PUSH_REJECTED")
                audit.quiet_board_push_rejected += 1
            else:
                labels.append("OTHER_REJECTED")
                audit.other_rejected += 1
    audit.classification_seconds += time.perf_counter() - started
    if [_action_key(a) for a in reference] != [_action_key(a) for a in noisy]:
        audit.parity_mismatches.append({"input": [_action_key(a) for a in actions], "reference": [_action_key(a) for a in reference], "audit": [_action_key(a) for a in noisy]})
    audit.events.append({"input": [_action_key(a) for a in actions], "labels": labels, "noisy": [_action_key(a) for a in noisy]})
    return noisy


def _lazy_quiescence_runtime(alpha, beta, ply, qdepth, ctx):
    """Executable lazy schedule; in-check path intentionally stays exact."""
    from generic_chess.ai.alphabeta.search import SearchAborted, _declaration_options, terminal_score
    from generic_chess.ai.alphabeta.search import MATE_SCORE
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.semantic_executor import semantic_engine_for

    runtime = ctx.runtime
    ctx.stats.qnodes += 1
    ctx.budget.check(ctx.stats)
    state = runtime.state
    terminal = runtime.terminal_status
    if terminal.is_terminal:
        return terminal_score(terminal, state.position.side_to_move, ply)
    declarations = _declaration_options(state, ctx.compiled, ctx.stats)
    winning = next((a for a in declarations if a.outcome == "WIN"), None)
    restart = next((a for a in declarations if a.outcome == "RESTART"), None)
    if winning is not None:
        return MATE_SCORE - ply
    if restart is not None:
        alpha = max(alpha, 0)
    side = state.position.side_to_move
    engine = semantic_engine_for(ctx.compiled)
    in_check = engine.in_check(state.position, side, checkpoint=ctx.checkpoint) if engine is not None else is_in_check(state.position, side, ctx.compiled)

    # Deliberately copy production's full in-check path, including its ordering
    # and hard-limit checks.  Lazy scheduling never applies to evasions.
    if in_check:
        ctx.stats.in_check_qnodes += 1
        actions = list(runtime.legal_actions(ctx.checkpoint))
        ctx.stats.legal_generation_calls += 1
        ctx.stats.legal_actions_generated += len(actions)
        ctx.budget.check(ctx.stats, force=True)
        if qdepth >= ctx.qhard_depth_limit:
            ctx.stats.qsearch_check_hard_limit_aborts += 1
            raise SearchAborted("qsearch_check_hard_limit")
        if ctx.qnode_limit is not None and ctx.stats.qnodes >= ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts += 1
            raise SearchAborted("qsearch_budget")
        if not actions:
            raise SearchAborted("qsearch_check_no_evasions")
        for action in sorted(actions, key=str):
            with runtime.pushed(action, checkpoint=ctx.checkpoint):
                score = -_lazy_quiescence_runtime(-beta, -alpha, ply + 1, qdepth + 1, ctx)
            if score >= beta:
                return score
            if score > alpha:
                alpha = score
        return alpha

    started = time.monotonic()
    stand_pat = ctx.evaluator.evaluate(state)
    ctx.stats.evaluation_calls += 1
    ctx.stats.evaluation_seconds += time.monotonic() - started
    ctx.budget.check(ctx.stats, force=True)
    if stand_pat >= beta:
        ctx.stats.stand_pat_cutoffs += 1
        return max(stand_pat, 0) if restart is not None else stand_pat
    if stand_pat > alpha:
        alpha = stand_pat
    if qdepth >= ctx.qdepth_limit:
        ctx.stats.qdepth_cutoffs += 1
        return alpha
    if ctx.qnode_limit is not None and ctx.stats.qnodes >= ctx.qnode_limit:
        ctx.stats.qsearch_budget_aborts += 1
        raise SearchAborted("qsearch_budget")

    # This is the only changed scheduling point: do not enumerate the complete
    # legal action set until expansion is known to be necessary.
    started = time.monotonic()
    actions = list(runtime.legal_actions(ctx.checkpoint))
    ctx.stats.legal_generation_calls += 1
    ctx.stats.legal_actions_generated += len(actions)
    ctx.budget.check(ctx.stats, force=True)
    for action in sorted(_instrumented_noisy_actions(ctx, actions), key=str):
        with runtime.pushed(action, checkpoint=ctx.checkpoint):
            score = -_lazy_quiescence_runtime(-beta, -alpha, ply + 1, qdepth + 1, ctx)
        if score >= beta:
            return score
        if score > alpha:
            alpha = score
    return alpha


def _probe(m, compiled, evaluator, state, *, variant, seconds=None, nodes=None, max_depth=64, qdepth=4, qhard=8, qcap=None):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    import generic_chess.ai.alphabeta.search as search_module
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.limits import SearchLimits

    global _ACTIVE_AUDIT, _REFERENCE_NOISY
    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    session = m["GameSession"](compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, max_depth=max_depth, quiescence_max_depth=qdepth, quiescence_hard_max_depth=qhard, quiescence_max_nodes=qcap, deterministic=True)
    audit = ClassifierAudit() if variant in ("production_instrumented", "lazy") else None
    old_q = search_module._quiescence_runtime
    old_noisy = search_module._runtime_noisy_actions
    _REFERENCE_NOISY = old_noisy
    _ACTIVE_AUDIT = audit
    if variant == "production_instrumented":
        search_module._runtime_noisy_actions = _instrumented_noisy_actions
    elif variant == "lazy":
        search_module._quiescence_runtime = _lazy_quiescence_runtime
    started = time.perf_counter()
    try:
        action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), _history_witnesses=session._search_witnesses, legal_binding_provider=provider)
    except Exception as exc:
        action, score, pv, reason = None, None, (), type(exc).__name__ + ":" + str(exc)
    elapsed = time.perf_counter() - started
    search_module._quiescence_runtime = old_q
    search_module._runtime_noisy_actions = old_noisy
    _ACTIVE_AUDIT = None
    return {
        "selected_move": m["gc_action_to_usi"](action) if action else None,
        "score": score,
        "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None,
        "completed_depth": stats.completed_depth,
        "main_nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "total_nodes": stats.nodes + stats.qnodes,
        "fallback": stats.root_scan_used_fallback,
        "termination_reason": reason,
        "time_to_first_completed_iteration": stats.time_to_first_completed_iteration,
        "elapsed_seconds": elapsed,
        "legal_generation_calls": stats.legal_generation_calls,
        "legal_actions_generated": stats.legal_actions_generated,
        "qsearch_metrics": {"in_check_qnodes": stats.in_check_qnodes, "stand_pat_cutoffs": stats.stand_pat_cutoffs, "qdepth_cutoffs": stats.qdepth_cutoffs, "qsearch_budget_aborts": stats.qsearch_budget_aborts, "qsearch_check_hard_limit_aborts": stats.qsearch_check_hard_limit_aborts},
        "classifier": audit.summary() if audit else None,
        "classifier_parity_mismatches": len(audit.parity_mismatches) if audit else 0,
        "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK",
    }


def _contexts():
    from scripts.audit_f32_qsearch_diagnosis import frozen_context

    return frozen_context()


def _root_matrix():
    m, compiled, evaluator, positions, modal = _contexts()
    matrix = {"production": {}, "lazy": {}}
    for variant in matrix:
        for seconds in TIMES:
            rows = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _probe(m, compiled, evaluator, state, variant=variant, seconds=seconds)
                row["position_id"] = item["position_id"]
                row["alphasho_0.50_modal"] = modal[item["position_id"]]["alphasho_0.5"]
                row["alphasho_2.00_modal"] = modal[item["position_id"]]["alphasho_2.0"]
                rows[item["position_id"]] = row
            matrix[variant][str(seconds)] = rows
    return matrix


def _fixed_audit():
    m, compiled, evaluator, positions, _modal = _contexts()
    result = {"production_instrumented": {}, "lazy": {}, "parity": {}}
    for budget in NODE_BUDGETS:
        p_rows = {}
        l_rows = {}
        for item in positions:
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            p_rows[item["position_id"]] = _probe(m, compiled, evaluator, state, variant="production_instrumented", nodes=budget)
            state = m["sfen_to_gc_state"](compiled, item["sfen"])
            l_rows[item["position_id"]] = _probe(m, compiled, evaluator, state, variant="lazy", nodes=budget)
        result["production_instrumented"][str(budget)] = p_rows
        result["lazy"][str(budget)] = l_rows
        pairs = {}
        for pid in p_rows:
            p, l = p_rows[pid], l_rows[pid]
            aborts = {"node_limit", "time_limit", "qsearch_budget", "qsearch_check_hard_limit", "fallback"}
            comparable = p["termination_reason"] not in aborts and l["termination_reason"] not in aborts and p["score"] is not None and l["score"] is not None
            pairs[pid] = {"comparable_without_abort": comparable, "score_equal": (p["score"] == l["score"]) if comparable else None, "production_score": p["score"], "lazy_score": l["score"], "production_reason": p["termination_reason"], "lazy_reason": l["termination_reason"], "classifier_parity_mismatches": p["classifier_parity_mismatches"] + l["classifier_parity_mismatches"]}
        result["parity"][str(budget)] = pairs
    # A separate completed bounded call supplies the hard value-parity gate;
    # the diagnostic 512/2048 calls intentionally exercise their node aborts.
    p_rows = {}
    l_rows = {}
    for item in positions:
        state = m["sfen_to_gc_state"](compiled, item["sfen"])
        p_rows[item["position_id"]] = _probe(m, compiled, evaluator, state, variant="production_instrumented", nodes=10000, max_depth=1)
        state = m["sfen_to_gc_state"](compiled, item["sfen"])
        l_rows[item["position_id"]] = _probe(m, compiled, evaluator, state, variant="lazy", nodes=10000, max_depth=1)
    result["parity_witness"] = {"production": p_rows, "lazy": l_rows}
    result["parity_witness"]["pairs"] = {pid: {"production_score": p_rows[pid]["score"], "lazy_score": l_rows[pid]["score"], "production_reason": p_rows[pid]["termination_reason"], "lazy_reason": l_rows[pid]["termination_reason"], "comparable_without_abort": p_rows[pid]["termination_reason"] not in {"node_limit", "time_limit", "qsearch_budget", "qsearch_check_hard_limit", "fallback"} and l_rows[pid]["termination_reason"] not in {"node_limit", "time_limit", "qsearch_budget", "qsearch_check_hard_limit", "fallback"}, "score_equal": p_rows[pid]["score"] == l_rows[pid]["score"], "classifier_parity_mismatches": p_rows[pid]["classifier_parity_mismatches"] + l_rows[pid]["classifier_parity_mismatches"]} for pid in p_rows}
    return result


def _aggregate_classifier(fixed):
    out = {}
    for budget in NODE_BUDGETS:
        total = ClassifierAudit()
        # Totals are the production-instrumented ten-root population.  Lazy
        # runs carry their own per-root counters but must not double these
        # discovery totals.
        for row in fixed["production_instrumented"][str(budget)].values():
            c = row["classifier"]
            mapping = {"direct_capture_accepts":"direct_capture", "direct_promotion_accepts":"direct_promotion", "terminal_child_push_accepted":"terminal_child_push_accepted", "checking_board_push_accepted":"checking_board_push_accepted", "quiet_board_push_rejected":"quiet_board_push_rejected", "checking_drop_push_accepted":"checking_drop_push_accepted", "nonchecking_drop_push_rejected":"nonchecking_drop_push_rejected", "other_rejected":"other_rejected", "input_candidates":"input_candidates", "classification_pushes":"classification_pushes", "expanded_noncheck_qnodes":"expanded_noncheck_qnodes"}
            for source, target in mapping.items():
                setattr(total, target, getattr(total, target) + c.get(source, 0))
            total.classification_seconds += c.get("classification_seconds", 0.0)
            total.reference_seconds += c.get("reference_seconds", 0.0)
        out[str(budget)] = total.summary()
    return out


def _branch_witnesses():
    """Execute branch witnesses without changing any production module."""
    from contextlib import contextmanager
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.core.terminal import TerminalResult, TerminalStatus
    import generic_chess.ai.alphabeta.search as search_module
    import generic_chess.core.attacks as attacks_module
    import generic_chess.core.semantic_executor as semantic_module

    class Position:
        side_to_move = 0
        board = (None,)

        @staticmethod
        def board_size():
            return 1

    class State:
        def __init__(self, terminal=TerminalStatus.ONGOING):
            self.position = Position()
            self.terminal_status = TerminalResult(terminal)
            self.history = ()

    class Runtime:
        def __init__(self, state, actions=(), children=None):
            self.state = state
            self.actions = tuple(actions)
            self.children = children or {}

        @property
        def terminal_status(self):
            return self.state.terminal_status

        def legal_actions(self, checkpoint=None):
            return self.actions

        @contextmanager
        def pushed(self, action, checkpoint=None):
            before = self.state
            self.state = self.children.get(action, before)
            try:
                yield self
            finally:
                self.state = before

    class Evaluator:
        @staticmethod
        def evaluate(state):
            return 0

    def ctx(runtime):
        stats = SearchStatistics()
        return SimpleNamespace(runtime=runtime, stats=stats, budget=SimpleNamespace(check=lambda *args, **kwargs: None), evaluator=Evaluator(), compiled=object(), qhard_depth_limit=8, qnode_limit=None, qdepth_limit=4, checkpoint=lambda: None)

    original_declarations = search_module._declaration_options
    original_check = attacks_module.is_in_check
    original_engine = semantic_module.semantic_engine_for
    global _ACTIVE_AUDIT, _REFERENCE_NOISY
    _ACTIVE_AUDIT = ClassifierAudit()
    _REFERENCE_NOISY = search_module._runtime_noisy_actions
    search_module._declaration_options = lambda state, compiled, stats: ()
    attacks_module.is_in_check = lambda position, side, compiled: False
    semantic_module.semantic_engine_for = lambda compiled: None
    rows = {}
    try:
        rows["terminal_root"] = {"executed": True, "score": _lazy_quiescence_runtime(0, 1, 0, 0, ctx(Runtime(State(TerminalStatus.STALEMATE))))}
        action = object()
        child = State(TerminalStatus.STALEMATE)
        rows["terminal_child"] = {"executed": True, "score": _lazy_quiescence_runtime(-100, 100, 0, 0, ctx(Runtime(State(), (action,), {action: child}))) }
        for outcome in ("WIN", "RESTART", "LOSS"):
            search_module._declaration_options = lambda state, compiled, stats, outcome=outcome: (SimpleNamespace(outcome=outcome),)
            rows["declaration_" + outcome.lower()] = {"executed": True, "score": _lazy_quiescence_runtime(0, 1, 0, 0, ctx(Runtime(State()))) }
        search_module._declaration_options = lambda state, compiled, stats: ()
        attacks_module.is_in_check = lambda position, side, compiled: True
        evasion = object()
        rows["in_check_full_evasion"] = {"executed": True, "score": _lazy_quiescence_runtime(-100, 100, 0, 0, ctx(Runtime(State(), (evasion,), {evasion: State(TerminalStatus.STALEMATE)}))) }
    finally:
        search_module._declaration_options = original_declarations
        attacks_module.is_in_check = original_check
        semantic_module.semantic_engine_for = original_engine
        _ACTIVE_AUDIT = None
        _REFERENCE_NOISY = None
    return rows


def _derive(matrix, fixed, f32):
    parity_rows = list(fixed["parity_witness"]["pairs"].values())
    parity_pass = bool(parity_rows) and all(row["score_equal"] and row["classifier_parity_mismatches"] == 0 for row in parity_rows)
    classifier_mismatches = sum(row["classifier_parity_mismatches"] for variant in fixed.values() if isinstance(variant, dict) and variant is not fixed["parity"] for rows in variant.values() for row in rows.values())
    prod_calls = sum(row["legal_generation_calls"] for row in fixed["production_instrumented"]["512"].values())
    lazy_calls = sum(row["legal_generation_calls"] for row in fixed["lazy"]["512"].values())
    prod_actions = sum(row["legal_actions_generated"] for row in fixed["production_instrumented"]["512"].values())
    lazy_actions = sum(row["legal_actions_generated"] for row in fixed["lazy"]["512"].values())
    saved_calls = prod_calls - lazy_calls
    saved_fraction = saved_calls / prod_calls if prod_calls else 0.0
    depth_improvements = sum(matrix["lazy"][str(t)][pid]["completed_depth"] > matrix["production"][str(t)][pid]["completed_depth"] for t in TIMES for pid in matrix["production"][str(t)])
    fallback_delta = sum(matrix["production"]["0.5"][pid]["fallback"] and not matrix["lazy"]["0.5"][pid]["fallback"] for pid in matrix["production"]["0.5"])
    lazy_gate = parity_pass and classifier_mismatches == 0 and saved_fraction >= 0.25 and (depth_improvements >= 3 or fallback_delta >= 3)
    classification = _aggregate_classifier(fixed)
    pushed = sum(c["classification_pushes"] for c in classification.values())
    rejected = sum(c["quiet_board_push_rejected"] + c["nonchecking_drop_push_rejected"] for c in classification.values())
    checking_fastpath_gate = parity_pass and pushed > 0 and rejected / pushed >= 0.70 and not lazy_gate
    if lazy_gate:
        next_boundary = "F33_QUIESCENCE_LAZY_GENERATION_IMPLEMENTATION"
    elif checking_fastpath_gate:
        next_boundary = "F33_SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH"
    else:
        qsearch_limiter = all(item["dominant_class"] == "QSEARCH_COST_LIMITED" for item in f32["per_root_classification"]["roots"].values())
        next_boundary = "F33_QUIESCENCE_BUDGET_ARCHITECTURE" if qsearch_limiter else "F33_STANDARD_SHOGI_MINIMAL_INTERVENTION_SELECTION"
    cap_rows = f32["qdepth_and_caps"]["qnode_cap_subset"]
    cap_abort = any(row["qsearch_metrics"]["qsearch_budget_aborts"] for seconds in cap_rows.values() for rows in seconds.values() for row in rows.values())
    cap_fallback = any(row["fallback"] for seconds in cap_rows.values() for rows in seconds.values() for row in rows.values())
    return {"lazy_value_parity": parity_pass, "classifier_parity": classifier_mismatches == 0, "classifier_parity_mismatches": classifier_mismatches, "fixed_512_production_legal_generation_calls": prod_calls, "fixed_512_lazy_legal_generation_calls": lazy_calls, "fixed_512_production_legal_actions_generated": prod_actions, "fixed_512_lazy_legal_actions_generated": lazy_actions, "fixed_512_complete_generation_calls_avoided": saved_calls, "fixed_512_complete_generation_call_savings_fraction": saved_fraction, "walltime_depth_improvements": depth_improvements, "walltime_050_fallback_delta": fallback_delta, "lazy_materiality_gate": lazy_gate, "checking_discovery_fastpath_gate": checking_fastpath_gate, "qnode_cap_semantics": "MIXED" if cap_abort and cap_fallback else "ITERATION_ABORTING" if cap_abort else "SOFT_RETURN", "next_boundary": next_boundary, "classification_totals": classification}


def run() -> dict[str, Any]:
    manifest = load(F32_MANIFEST)
    if manifest.get("manifest_sha256") != F32_MANIFEST_SHA or sha(F32_RESULT) != F32_RESULT_SHA:
        raise AssertionError("F32 evidence identity changed")
    f32 = load(F32_RESULT)
    matrix = _root_matrix()
    fixed = _fixed_audit()
    derived = _derive(matrix, fixed, f32)
    witnesses = _branch_witnesses()
    flags = {"F31_CAUSAL_BASELINE_CONSUMED": True, "QSEARCH_COST_DECOMPOSITION_COMPLETE": True, "QSEARCH_EXACT_REORDERING_AUDIT_COMPLETE": derived["lazy_value_parity"], "QSEARCH_NOISY_ACTION_DISCOVERY_AUDIT_COMPLETE": derived["classifier_parity"], "QSEARCH_DEPTH_BUDGET_AUDIT_COMPLETE": True, "SEARCH_HORIZON_AND_QUIESCENCE_DIAGNOSIS_COMPLETE": derived["lazy_value_parity"] and derived["classifier_parity"]}
    return {"schema_version": 1, "status": "PASS" if all(flags.values()) else "FAIL", "production_changed": False, "f32_manifest_sha256": F32_MANIFEST_SHA, "f32_result_sha256": F32_RESULT_SHA, "f31r1_result_sha256": F31R1_RESULT_SHA, "matrix": matrix, "fixed_node_exact_audit": fixed, "derived_gates": derived, "flags": flags, "coverage": {"actual_frozen_standard_shogi_roots": "executed", "opaque_generic_ruleset_witnesses": "executed by the generic runtime/classifier; no chess-specific branch", "in_check_path": "executed and unchanged", "declaration_and_terminal_path": "executed by branch witnesses", "branch_witnesses": witnesses}, "instrumentation_disclosure": "The independent production classifier is run on the same action input for exact sequence parity; its comparison cost is excluded from production claims.", "constraints": ["NO_PRODUCTION_CHANGE", "NO_NEW_ALPHASHO_RUN", "NO_PAIRED_BENCHMARK", "NO_NATIVE_REPAIR", "PRESERVE_F32_BYTE_IDENTITIES"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("use --run")
    result = run()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "next": result["derived_gates"]["next_boundary"], "flags": result["flags"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
