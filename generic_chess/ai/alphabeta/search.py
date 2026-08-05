"""Negamax alpha-beta with iterative deepening, TT, ordering, quiescence."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ...core.actions import Action
from ...core.keys import position_key
from ...core.movegen import legal_actions
from ...core.position import GameState
from ...core.terminal import TerminalStatus
from ...core.transition import apply_action
from ..cancellation import CancellationToken
from ..evaluation.config import MATE_SCORE
from ..evaluation.evaluator import Evaluator
from ..limits import SearchLimits
from .ordering import MoveOrderer
from .quiescence import classify_noisy
from .statistics import SearchStatistics
from .transposition import BoundType, TranspositionTable, score_from_tt, score_to_tt


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
        self._check_interval = 1024

    def check(self, stats: SearchStatistics) -> None:
        if self._max_nodes is not None and stats.nodes >= self._max_nodes:
            raise SearchAborted("node_limit")
        if self._cancel is None and self._deadline is None:
            return
        if stats.nodes % self._check_interval != 0:
            return
        if self._cancel is not None and self._cancel.is_cancelled():
            raise SearchAborted("cancelled")
        if self._deadline is not None and time.monotonic() >= self._deadline:
            raise SearchAborted("time_limit")

    def check_iteration(self, stats: SearchStatistics) -> None:
        if self._cancel is not None and self._cancel.is_cancelled():
            raise SearchAborted("cancelled")
        if self._max_nodes is not None and stats.nodes >= self._max_nodes:
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
        "use_tt",
        "use_ordering",
        "qdepth_limit",
        "qnode_limit",
    )

    def __init__(
        self,
        compiled,
        evaluator: Evaluator,
        tt: TranspositionTable,
        stats: SearchStatistics,
        budget: _Budget,
        use_tt: bool,
        use_ordering: bool,
        qdepth_limit: int,
        qnode_limit: int | None,
    ) -> None:
        self.compiled = compiled
        self.evaluator = evaluator
        self.tt = tt
        self.stats = stats
        self.budget = budget
        self.orderer = MoveOrderer()
        self.use_tt = use_tt
        self.use_ordering = use_ordering
        self.qdepth_limit = qdepth_limit
        self.qnode_limit = qnode_limit


def terminal_score(result, side_to_move: int, ply: int) -> int:
    if result.status in (TerminalStatus.STALEMATE, TerminalStatus.REPETITION, TerminalStatus.MAX_PLY):
        return 0
    if result.winner == side_to_move:
        return MATE_SCORE - ply
    return -MATE_SCORE + ply


def _tt_key(state: GameState, compiled) -> tuple:
    return (
        compiled.ruleset_fingerprint,
        position_key(state.position, compiled),
        state.repetition_counts,
    )


def negamax(
    state: GameState,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    ctx: _Context,
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
            score = quiescence(state, alpha, beta, ply, 0, ctx)
        else:
            score = ctx.evaluator.evaluate(state)
        return SearchResult(score, None, ())

    key = _tt_key(state, ctx.compiled)
    entry = None
    if ctx.use_tt:
        ctx.stats.tt_probes += 1
        entry = ctx.tt.probe(key, depth)
        if entry is not None:
            ctx.stats.tt_hits += 1
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

    actions = legal_actions(state, ctx.compiled)
    if not actions:
        # Core should have flagged the position terminal; fall back to eval.
        return SearchResult(ctx.evaluator.evaluate(state), None, ())

    if ctx.use_ordering:
        ordered = ctx.orderer.order(
            state, actions, ctx.evaluator, depth, entry.best_action if entry else None
        )
    else:
        ordered = sorted(actions, key=str)

    original_alpha = alpha
    best = -INF
    best_action: Action | None = None
    best_pv: tuple[Action, ...] = ()

    for action in ordered:
        child = apply_action(state, action, ctx.compiled)
        child_result = negamax(child, depth - 1, -beta, -alpha, ply + 1, ctx)
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
                ctx.orderer.record_history(state.position.side_to_move, action)
            break

    if ctx.use_tt:
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
    stand_pat = ctx.evaluator.evaluate(state)
    if stand_pat >= beta:
        return stand_pat
    if stand_pat > alpha:
        alpha = stand_pat
    if qdepth >= ctx.qdepth_limit:
        return alpha
    if ctx.qnode_limit is not None and ctx.stats.qnodes >= ctx.qnode_limit:
        return alpha

    actions = legal_actions(state, ctx.compiled)
    noisy = classify_noisy(state, actions)
    ordered = sorted(noisy, key=str)
    for action in ordered:
        child = apply_action(state, action, ctx.compiled)
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
    actions = sorted(legal_actions(state, compiled), key=str)
    best = -INF
    best_action: Action | None = None
    for action in actions:
        child = apply_action(state, action, compiled)
        score, _ = reference_minimax(child, depth - 1, evaluator, compiled, ply + 1)
        score = -score
        if score > best:
            best = score
            best_action = action
    return best, best_action


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
) -> tuple[Action | None, int, tuple[Action, ...], str]:
    """Iterative deepening; returns (action, score, pv, termination_reason)."""
    terminal = state.terminal_status
    if terminal.is_terminal:
        stats.termination_reason = "terminal_position"
        return (
            None,
            terminal_score(terminal, state.position.side_to_move, 0),
            (),
            stats.termination_reason,
        )
    actions = legal_actions(state, compiled)
    if not actions:
        stats.termination_reason = "terminal_position"
        return None, 0, (), stats.termination_reason

    tt.new_generation()
    budget = _Budget(limits, cancel_token)
    ctx = _Context(
        compiled,
        evaluator,
        tt,
        stats,
        budget,
        use_tt,
        use_ordering,
        limits.quiescence_max_depth,
        limits.quiescence_max_nodes,
    )
    max_depth = limits.max_depth if limits.max_depth is not None else 64
    best: SearchResult | None = None
    abort_reason: str | None = None
    for depth in range(1, max_depth + 1):
        try:
            budget.check_iteration(stats)
        except SearchAborted as exc:
            abort_reason = str(exc)
            break
        try:
            best = negamax(state, depth, -INF, INF, 0, ctx)
        except SearchAborted as exc:
            abort_reason = str(exc)
            break
        stats.completed_depth = depth
        stats.selective_depth = depth

    if best is not None:
        stats.termination_reason = "completed_depth" if abort_reason is None else abort_reason
        return best.best_action, best.score, best.pv, stats.termination_reason

    # No full iteration completed: deterministic safe fallback.
    fallback = sorted(actions, key=str)[0]
    stats.termination_reason = "fallback"
    return fallback, 0, (), stats.termination_reason
