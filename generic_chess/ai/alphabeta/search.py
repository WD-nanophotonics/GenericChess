"""Negamax alpha-beta with iterative deepening, TT, ordering, quiescence."""

from __future__ import annotations

import time
from dataclasses import dataclass
from itertools import chain

from ...core.actions import Action
from ...core.attacks import is_in_check
from ...core.keys import position_key, semantic_position_key
from ...core.lazy_transitions import (
    iter_legal_successor_handles,
    legal_successor_handles,
    materialize_legal_successor,
)
from ...core.movegen import legal_actions
from ...core.position import GameState
from ...core.terminal import TerminalStatus
from ...core.transition import legal_successors
from ...core.semantic_executor import semantic_engine_for
from ..cancellation import CancellationToken
from ..evaluation.config import MATE_SCORE, MATE_THRESHOLD
from ..evaluation.evaluator import Evaluator
from ..limits import SearchLimits
from ..audit_instrumentation import AuditMetric, AuditRecorder, NullAuditRecorder
from .ordering import MoveOrderer, StagedMovePicker
from .quiescence import classify_noisy
from .statistics import SearchStatistics
from .transposition import BoundType, TranspositionTable, score_from_tt, score_to_tt
from .tuning import SearchTuning


INF = 10**12


class SearchAborted(Exception):
    """Internal control flow for budget/cancellation only."""


@dataclass(frozen=True, slots=True)
class SearchResult:
    score: int
    best_action: Action | None
    pv: tuple[Action, ...]


class _Budget:
    def __init__(
        self,
        limits: SearchLimits,
        cancel_token: CancellationToken | None,
    ) -> None:
        self._max_nodes = limits.max_nodes
        self._max_time = limits.max_time_seconds
        self._cancel = cancel_token
        self._deadline = (
            time.monotonic() + limits.max_time_seconds
            if limits.max_time_seconds is not None
            else None
        )
        # Interactive controls must be observed promptly.  Node-only searches
        # retain the historical coarse interval so deterministic node-budget
        # behavior does not pay the wall-clock polling cost.
        self._interactive = cancel_token is not None or self._deadline is not None
        self._check_interval = 1 if self._interactive else 128

    def check(self, stats: SearchStatistics, *, force: bool = False) -> None:
        total = stats.nodes + stats.qnodes
        if self._max_nodes is not None and total >= self._max_nodes:
            raise SearchAborted("node_limit")
        if not self._interactive:
            if total % self._check_interval != 0:
                return
            return
        if not force and total % self._check_interval != 0:
            return
        if self._cancel is not None and self._cancel.is_cancelled():
            raise SearchAborted("cancelled")
        if self._deadline is not None and time.monotonic() >= self._deadline:
            raise SearchAborted("time_limit")

    def check_iteration(self, stats: SearchStatistics) -> None:
        if self._cancel is not None and self._cancel.is_cancelled():
            raise SearchAborted("cancelled")
        total = stats.nodes + stats.qnodes
        if self._max_nodes is not None and total >= self._max_nodes:
            raise SearchAborted("node_limit")
        if self._deadline is not None and time.monotonic() >= self._deadline:
            raise SearchAborted("time_limit")


class _Context:
    __slots__ = (
        "compiled",
        "evaluator",
        "tt",
        "stats",
        "budget",
        "orderer",
        "tuning",
        "recorder",
        "use_tt",
        "use_ordering",
        "qdepth_limit",
        "qhard_depth_limit",
        "qnode_limit",
    )

    def __init__(
        self,
        compiled,
        evaluator: Evaluator,
        tt: TranspositionTable,
        stats: SearchStatistics,
        budget: _Budget,
        tuning: SearchTuning,
        use_tt: bool,
        use_ordering: bool,
        qdepth_limit: int,
        qhard_depth_limit: int,
        qnode_limit: int | None,
        recorder: AuditRecorder | None = None,
    ) -> None:
        self.compiled = compiled
        self.evaluator = evaluator
        self.tt = tt
        self.stats = stats
        self.budget = budget
        self.orderer = MoveOrderer()
        self.tuning = tuning
        self.recorder = recorder or NullAuditRecorder()
        self.use_tt = use_tt
        self.use_ordering = use_ordering
        self.qdepth_limit = qdepth_limit
        self.qhard_depth_limit = qhard_depth_limit
        self.qnode_limit = qnode_limit

    def checkpoint(self) -> None:
        """Cooperative callback passed into Core semantic work units."""
        self.budget.check(self.stats, force=True)


def terminal_score(result, side_to_move: int, ply: int) -> int:
    if result.status in (TerminalStatus.STALEMATE, TerminalStatus.REPETITION, TerminalStatus.MAX_PLY):
        return 0
    if result.winner == side_to_move:
        return MATE_SCORE - ply
    return -MATE_SCORE + ply


def _position_identity_key(state: GameState, compiled) -> str:
    support = getattr(compiled, "support", None)
    if support is not None:
        return semantic_position_key(
            state.position, support, compiled.ir.aux_slots
        )
    return position_key(state.position, compiled)


def history_adjudication_context(state: GameState, compiled) -> tuple:
    """Return a bounded identity for history-dependent terminal semantics.

    The continuous-check policy is currently conservatively excluded from TT
    reuse in ``negamax``.  Keeping this canonical, bounded context in the key
    makes the identity explicit for callers and prevents a future cache user
    from silently treating equal positions/counts as equivalent histories.
    """
    if getattr(compiled, "repetition_policy", "draw") != "continuous_check_loss":
        return ()
    history = state.history
    if not history:
        return (None, 0, ())
    current_key = history[-1].position_key
    occurrences = [
        index for index, record in enumerate(history)
        if record.position_key == current_key
    ]
    limit = max(1, int(getattr(compiled, "repetition_limit", 4)))
    start = occurrences[-min(limit, len(occurrences))] if occurrences else max(0, len(history) - 1)
    cycle = history[start + 1 :]
    actor_summary = tuple(
        (actor, sum(record.actor == actor for record in cycle),
         sum(record.actor == actor and record.gave_check for record in cycle))
        for actor in (0, 1)
    )
    return (current_key, len(occurrences), actor_summary)


def _tt_key(state: GameState, compiled) -> tuple:
    base = (
        compiled.ruleset_fingerprint,
        _position_identity_key(state, compiled),
        state.repetition_counts,
    )
    context = history_adjudication_context(state, compiled)
    return base if not context else base + (context,)


def negamax(
    state: GameState,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    ctx: _Context,
    prev_action: Action | None = None,
    node_key: str | None = None,
) -> SearchResult:
    ctx.stats.nodes += 1
    ctx.budget.check(ctx.stats)

    terminal = state.terminal_status
    if terminal.is_terminal:
        return SearchResult(
            terminal_score(terminal, state.position.side_to_move, ply), None, ()
        )
    if depth <= 0:
        if ctx.qdepth_limit > 0:
            with ctx.recorder.time_block(AuditMetric.QUIESCENCE):
                score = quiescence(state, alpha, beta, ply, 0, ctx)
        else:
            with ctx.recorder.time_block(AuditMetric.EVALUATION):
                score = ctx.evaluator.evaluate(state)
        ctx.budget.check(ctx.stats, force=True)
        return SearchResult(score, None, ())

    if ctx.tuning.use_mate_distance_pruning:
        alpha = max(alpha, -MATE_SCORE + ply)
        beta = min(beta, MATE_SCORE - ply - 1)
        if alpha >= beta:
            ctx.stats.mate_pruning_cutoffs += 1
            return SearchResult(alpha, None, ())

    tt_compatible = (
        ctx.use_tt
        and getattr(ctx.compiled, "repetition_policy", "draw") != "continuous_check_loss"
    )
    if node_key is not None:
        ctx.stats.position_key_cache_hits += 1
        key = (
            ctx.compiled.ruleset_fingerprint,
            node_key,
            state.repetition_counts,
        )
        context = history_adjudication_context(state, ctx.compiled)
        if context:
            key = key + (context,)
    else:
        ctx.stats.position_keys_computed += 1
        with ctx.recorder.time_block(AuditMetric.TT_KEY):
            key = _tt_key(state, ctx.compiled)
    entry = None
    if tt_compatible:
        ctx.stats.tt_probes += 1
        with ctx.recorder.time_block(AuditMetric.TT_PROBE_STORE):
            entry = ctx.tt.probe(key)
        if entry is not None:
            ctx.stats.tt_hits += 1
            if entry.depth >= depth:
                with ctx.recorder.time_block(AuditMetric.TT_PROBE_STORE):
                    score = score_from_tt(entry.score, ply)
                    if entry.bound is BoundType.EXACT:
                        return SearchResult(score, entry.best_action, ())
                    if entry.bound is BoundType.LOWER:
                        alpha = max(alpha, score)
                    else:
                        beta = min(beta, score)
                    if alpha >= beta:
                        ctx.stats.tt_cutoffs += 1
                        return SearchResult(score, entry.best_action, ())

    lazy = False
    child_by_action = {}
    handle_by_action = {}
    started = time.monotonic()
    with ctx.recorder.time_block(AuditMetric.MOVE_GEN):
        streaming_handles = (
            ctx.tuning.use_lazy_successors
            or semantic_engine_for(ctx.compiled) is not None
        )
        if streaming_handles:
            handle_iter = iter_legal_successor_handles(
                state, ctx.compiled, checkpoint=ctx.checkpoint
            )
            handles = []
            for handle in handle_iter:
                handles.append(handle)
                ctx.stats.legal_actions_generated += 1
                ctx.stats.successor_handles_created += 1
                ctx.checkpoint()
            actions = [handle.action for handle in handles]
            handle_by_action = {handle.action: handle for handle in handles}
            lazy = True
        else:
            successors = legal_successors(state, ctx.compiled)
            actions = [action for action, _ in successors]
            child_by_action = dict(successors)
    ctx.stats.legal_generation_calls += 1
    ctx.stats.legal_generation_seconds += time.monotonic() - started
    ctx.budget.check(ctx.stats, force=True)
    if not actions:
        # Core should have flagged the position terminal; fall back to eval.
        with ctx.recorder.time_block(AuditMetric.EVALUATION):
            return SearchResult(ctx.evaluator.evaluate(state), None, ())
    if ctx.use_ordering:
        started = time.monotonic()
        with ctx.recorder.time_block(AuditMetric.ORDERING):
            if ctx.tuning.use_staged_move_picker:
                ordered_actions = StagedMovePicker(
                    state,
                    actions,
                    ctx.evaluator,
                    depth,
                    entry.best_action if entry else None,
                    prev_action,
                    ctx.orderer,
                    ctx.tuning,
                    ctx.stats,
                )
            else:
                ordered_actions = ctx.orderer.order(
                    state,
                    actions,
                    ctx.evaluator,
                    depth,
                    entry.best_action if entry else None,
                    prev_action,
                    ctx.tuning,
                )
        ctx.budget.check(ctx.stats, force=True)
        ctx.stats.ordering_calls += 1
        ctx.stats.ordered_moves += len(actions)
        ctx.stats.ordering_seconds += time.monotonic() - started
    else:
        ordered_actions = sorted(actions, key=str)

    original_alpha = alpha
    best = -INF
    best_action: Action | None = None
    best_pv: tuple[Action, ...] = ()

    for move_index, action in enumerate(ordered_actions):
        if lazy:
            handle = handle_by_action[action]
            child, child_key = materialize_legal_successor(
                state, handle, ctx.compiled, checkpoint=ctx.checkpoint
            )
            ctx.budget.check(ctx.stats, force=True)
            ctx.stats.successors_materialized += 1
            ctx.stats.successors_searched += 1
            ctx.stats.terminal_results_computed += 1
            ctx.stats.position_keys_computed += 1
        else:
            child = child_by_action[action]
            child_key = None
            ctx.budget.check(ctx.stats, force=True)
        if ctx.tuning.use_pvs and move_index > 0:
            ctx.stats.pvs_null_window_searches += 1
            null_score = -negamax(
                child,
                depth - 1,
                -alpha - 1,
                -alpha,
                ply + 1,
                ctx,
                prev_action=action,
                node_key=child_key,
            ).score
            if alpha < null_score < beta:
                ctx.stats.pvs_researches += 1
                child_result = negamax(
                    child,
                    depth - 1,
                    -beta,
                    -alpha,
                    ply + 1,
                    ctx,
                    prev_action=action,
                    node_key=child_key,
                )
                score = -child_result.score
            else:
                score = null_score
                child_result = SearchResult(null_score, None, ())
        else:
            child_result = negamax(
                child,
                depth - 1,
                -beta,
                -alpha,
                ply + 1,
                ctx,
                prev_action=action,
                node_key=child_key,
            )
            score = -child_result.score
        if score > best:
            best = score
            best_action = action
            best_pv = (action,) + child_result.pv
        if score > alpha:
            alpha = score
        if alpha >= beta:
            ctx.stats.beta_cutoffs += 1
            if ctx.use_ordering:
                ctx.orderer.record_killer(depth, action)
                ctx.orderer.record_history(
                    state.position.side_to_move, action, ctx.tuning
                )
                if prev_action is not None and ctx.tuning.use_countermove:
                    ctx.orderer.record_countermove(prev_action, action)
            break

    if tt_compatible:
        with ctx.recorder.time_block(AuditMetric.TT_PROBE_STORE):
            if best <= original_alpha:
                bound = BoundType.UPPER
            elif best >= beta:
                bound = BoundType.LOWER
            else:
                bound = BoundType.EXACT
            ctx.tt.store(key, depth, score_to_tt(best, ply), bound, best_action)
    return SearchResult(best, best_action, best_pv)


def quiescence(
    state: GameState,
    alpha: int,
    beta: int,
    ply: int,
    qdepth: int,
    ctx: _Context,
) -> int:
    ctx.stats.qnodes += 1
    ctx.budget.check(ctx.stats)

    terminal = state.terminal_status
    if terminal.is_terminal:
        return terminal_score(terminal, state.position.side_to_move, ply)

    side = state.position.side_to_move
    semantic_engine = semantic_engine_for(ctx.compiled)
    in_check = (
        semantic_engine.in_check(
            state.position, side, checkpoint=ctx.checkpoint
        )
        if semantic_engine is not None
        else is_in_check(state.position, side, ctx.compiled)
    )
    if in_check:
        # In-check nodes cannot stand pat: extend over every legal evasion.
        ctx.stats.in_check_qnodes += 1
        if qdepth >= ctx.qhard_depth_limit:
            ctx.stats.qsearch_check_hard_limit_aborts += 1
            raise SearchAborted("qsearch_check_hard_limit")
        if ctx.qnode_limit is not None and ctx.stats.qnodes >= ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts += 1
            raise SearchAborted("qsearch_budget")
        started = time.monotonic()
        if semantic_engine is not None:
            handle_by_action = {}
            for handle in iter_legal_successor_handles(
                state, ctx.compiled, checkpoint=ctx.checkpoint
            ):
                handle_by_action[handle.action] = handle
                ctx.checkpoint()
            ordered_actions = sorted(handle_by_action, key=str)
            successors = None
        else:
            successors = legal_successors(state, ctx.compiled)
            ordered_actions = None
        ctx.stats.legal_generation_calls += 1
        ctx.stats.legal_generation_seconds += time.monotonic() - started
        ctx.budget.check(ctx.stats, force=True)
        if semantic_engine is not None and not handle_by_action:
            # A non-terminal, in-check state with no evasions is a Core
            # invariant violation; never fall back to static evaluation.
            raise SearchAborted("qsearch_check_no_evasions")
        if semantic_engine is None and not successors:
            # A non-terminal, in-check state with no evasions is a Core
            # invariant violation; never fall back to static evaluation.
            raise SearchAborted("qsearch_check_no_evasions")
        ordered = (
            ((action, handle_by_action[action]) for action in ordered_actions)
            if semantic_engine is not None
            else ((action, child) for action, child in sorted(successors, key=lambda pair: str(pair[0])))
        )
        for action, child_or_handle in ordered:
            child = (
                materialize_legal_successor(
                    state, child_or_handle, ctx.compiled,
                    checkpoint=ctx.checkpoint,
                )[0]
                if semantic_engine is not None
                else child_or_handle
            )
            score = -quiescence(child, -beta, -alpha, ply + 1, qdepth + 1, ctx)
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
        return stand_pat
    if stand_pat > alpha:
        alpha = stand_pat
    if qdepth >= ctx.qdepth_limit:
        ctx.stats.qdepth_cutoffs += 1
        return alpha
    if ctx.qnode_limit is not None and ctx.stats.qnodes >= ctx.qnode_limit:
        ctx.stats.qsearch_budget_aborts += 1
        raise SearchAborted("qsearch_budget")

    started = time.monotonic()
    if semantic_engine is not None:
        handle_by_action = {}
        for handle in iter_legal_successor_handles(
            state, ctx.compiled, checkpoint=ctx.checkpoint
        ):
            handle_by_action[handle.action] = handle
            ctx.checkpoint()
        successors = None
    else:
        successors = legal_successors(state, ctx.compiled)
    ctx.stats.legal_generation_calls += 1
    ctx.stats.legal_generation_seconds += time.monotonic() - started
    ctx.budget.check(ctx.stats, force=True)
    if semantic_engine is not None:
        ordered = (
            (action, handle_by_action[action])
            for action in sorted(handle_by_action, key=str)
        )
    else:
        noisy = classify_noisy(state, successors, ctx.compiled, ctx.stats)
        ctx.budget.check(ctx.stats, force=True)
        ordered = sorted(
            (pair for pair in successors if pair[0] in noisy),
            key=lambda pair: str(pair[0]),
        )
    for action, child_or_handle in ordered:
        child = (
            materialize_legal_successor(
                state, child_or_handle, ctx.compiled,
                checkpoint=ctx.checkpoint,
            )[0]
            if semantic_engine is not None
            else child_or_handle
        )
        if semantic_engine is not None:
            noisy_one = classify_noisy(
                state, ((action, child),), ctx.compiled, ctx.stats
            )
            ctx.budget.check(ctx.stats, force=True)
            if not noisy_one:
                continue
        score = -quiescence(child, -beta, -alpha, ply + 1, qdepth + 1, ctx)
        if score >= beta:
            return score
        if score > alpha:
            alpha = score
    return alpha


def reference_minimax(
    state: GameState,
    depth: int,
    evaluator: Evaluator,
    compiled,
    ply: int = 0,
) -> tuple[int, Action | None]:
    """No TT / ordering / quiescence reference search for equivalence tests."""
    terminal = state.terminal_status
    if terminal.is_terminal:
        return terminal_score(terminal, state.position.side_to_move, ply), None
    if depth <= 0:
        return evaluator.evaluate(state), None
    successors = sorted(legal_successors(state, compiled), key=lambda pair: str(pair[0]))
    best = -INF
    best_action: Action | None = None
    for action, child in successors:
        score, _ = reference_minimax(child, depth - 1, evaluator, compiled, ply + 1)
        score = -score
        if score > best:
            best = score
            best_action = action
    return best, best_action


def root_tactical_scan(
    state: GameState,
    compiled,
    evaluator: Evaluator,
    ctx: _Context,
    handles=None,
) -> tuple[Action | None, Action | None]:
    """Cheap root scan: immediate mate first, else best fast-eval root action.

    Returns ``(immediate_win_action, best_action_by_eval)``.  Every root
    successor is examined at least once so a very short budget still produces
    a sensible fallback instead of the first canonical action.
    """
    best_action: Action | None = None
    best_score = -INF
    started = time.monotonic()
    if handles is None:
        with ctx.recorder.time_block(AuditMetric.MOVE_GEN):
            successors = legal_successors(state, compiled)
        ctx.budget.check(ctx.stats, force=True)
        stream = iter(successors)
    else:
        stream = handles
    for item in stream:
        ctx.budget.check(ctx.stats, force=True)
        if handles is None:
            action, child = item
        else:
            action = item.action
            child, _child_key = materialize_legal_successor(
                state, item, compiled, checkpoint=ctx.checkpoint
            )
        ctx.stats.nodes += 1
        ctx.stats.root_scan_nodes += 1
        if (
            child.terminal_status.status is TerminalStatus.CHECKMATE
            and child.terminal_status.winner == state.position.side_to_move
        ):
            ctx.stats.root_scan_seconds += time.monotonic() - started
            return action, best_action
        ctx.stats.evaluation_calls += 1
        with ctx.recorder.time_block(AuditMetric.EVALUATION):
            score = -evaluator.evaluate(child)
        ctx.budget.check(ctx.stats, force=True)
        if score > best_score:
            best_score = score
            best_action = action
        ctx.budget.check(ctx.stats)
    ctx.stats.root_scan_seconds += time.monotonic() - started
    return None, best_action


def _aspiration_iteration(
    state: GameState,
    depth: int,
    prev_score: int,
    ctx: _Context,
) -> SearchResult:
    """One depth with an aspiration window around the previous iteration score."""
    delta = ctx.tuning.aspiration_delta
    alpha = max(-INF, prev_score - delta)
    beta = min(INF, prev_score + delta)
    failures = 0
    while True:
        result = negamax(state, depth, alpha, beta, 0, ctx)
        if result.score <= alpha:
            ctx.stats.aspiration_fail_low += 1
            ctx.stats.aspiration_researches += 1
            failures += 1
            if failures >= 2:
                alpha, beta = -INF, INF
            else:
                delta *= 2
                alpha = max(-INF, result.score - delta)
                beta = min(INF, beta)
        elif result.score >= beta:
            ctx.stats.aspiration_fail_high += 1
            ctx.stats.aspiration_researches += 1
            failures += 1
            if failures >= 2:
                alpha, beta = -INF, INF
            else:
                delta *= 2
                alpha = max(-INF, alpha)
                beta = min(INF, result.score + delta)
        else:
            return result


def run_root_search(
    state: GameState,
    compiled,
    evaluator: Evaluator,
    tt: TranspositionTable,
    limits: SearchLimits,
    cancel_token: CancellationToken | None,
    stats: SearchStatistics,
    *,
    use_tt: bool,
    use_ordering: bool,
    tuning: SearchTuning = SearchTuning(),
    recorder: AuditRecorder | None = None,
    progress_callback=None,
) -> tuple[Action | None, int, tuple[Action, ...], str]:
    """Iterative deepening; returns (action, score, pv, termination_reason)."""
    started = time.monotonic()
    terminal = state.terminal_status
    if terminal.is_terminal:
        stats.termination_reason = "terminal_position"
        return (
            None,
            terminal_score(terminal, state.position.side_to_move, 0),
            (),
            stats.termination_reason,
        )
    budget = _Budget(limits, cancel_token)
    tt.new_generation()
    ctx = _Context(
        compiled,
        evaluator,
        tt,
        stats,
        budget,
        tuning,
        use_tt,
        use_ordering,
        limits.quiescence_max_depth,
        limits.quiescence_hard_max_depth,
        limits.quiescence_max_nodes,
        recorder,
    )

    root_first_action: Action | None = None
    root_handles = None
    actions: list[Action] | None = None
    if semantic_engine_for(compiled) is not None:
        root_stream = iter_legal_successor_handles(
            state, compiled, checkpoint=ctx.checkpoint
        )
        try:
            first_handle = next(root_stream)
        except StopIteration:
            stats.termination_reason = "terminal_position"
            return None, 0, (), stats.termination_reason
        except SearchAborted:
            stats.termination_reason = "NO_LEGAL_FALLBACK_BEFORE_DEADLINE"
            return None, 0, (), stats.termination_reason
        root_first_action = first_handle.action
        stats.time_to_first_legal_action = time.monotonic() - started
        root_handles = chain((first_handle,), root_stream)
        try:
            budget.check(stats, force=True)
        except SearchAborted as exc:
            stats.root_scan_used_fallback = True
            stats.termination_reason = str(exc)
            return root_first_action, 0, (), stats.termination_reason
    else:
        actions = legal_actions(state, compiled)
        if not actions:
            stats.termination_reason = "terminal_position"
            return None, 0, (), stats.termination_reason
        try:
            budget.check(stats, force=True)
        except SearchAborted as exc:
            stats.root_scan_used_fallback = True
            stats.termination_reason = str(exc)
            return sorted(actions, key=str)[0], 0, (), stats.termination_reason

    immediate_win: Action | None = None
    scan_best: Action | None = None
    if tuning.use_root_tactical:
        try:
            immediate_win, scan_best = root_tactical_scan(
                state, compiled, evaluator, ctx, handles=root_handles
            )
        except SearchAborted as exc:
            stats.root_scan_used_fallback = True
            stats.termination_reason = str(exc)
            fallback = root_first_action
            if fallback is None:
                fallback = sorted(actions, key=str)[0]
            return fallback, 0, (), stats.termination_reason
    if immediate_win is not None:
        stats.termination_reason = "root_immediate_win"
        return immediate_win, MATE_SCORE - 1, (immediate_win,), stats.termination_reason

    max_depth = limits.max_depth if limits.max_depth is not None else 64
    best: SearchResult | None = None
    abort_reason: str | None = None
    for depth in range(1, max_depth + 1):
        try:
            budget.check_iteration(stats)
        except SearchAborted as exc:
            abort_reason = str(exc)
            break
        prev_score = best.score if best is not None else None
        try:
            if (
                tuning.use_aspiration
                and depth >= tuning.aspiration_start_depth
                and prev_score is not None
                and abs(prev_score) < MATE_THRESHOLD
            ):
                best = _aspiration_iteration(state, depth, prev_score, ctx)
            else:
                best = negamax(state, depth, -INF, INF, 0, ctx)
        except SearchAborted as exc:
            abort_reason = str(exc)
            break
        stats.completed_depth = depth
        stats.selective_depth = depth
        stats.time_to_first_completed_iteration = time.monotonic() - started
        if progress_callback is not None:
            progress_callback(depth, stats.nodes, stats.qnodes)

    if best is not None:
        stats.termination_reason = "completed_depth" if abort_reason is None else abort_reason
        return best.best_action, best.score, best.pv, stats.termination_reason

    # No full iteration completed: prefer the root scan's best action.
    if tuning.use_root_tactical and scan_best is not None:
        stats.root_scan_used_fallback = True
        stats.termination_reason = "fallback"
        return scan_best, 0, (), stats.termination_reason
    fallback = root_first_action
    if fallback is None:
        fallback = sorted(actions, key=str)[0]
    stats.root_scan_used_fallback = True
    stats.termination_reason = "fallback"
    return fallback, 0, (), stats.termination_reason
