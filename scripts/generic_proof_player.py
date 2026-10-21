"""Opt-in research player: proof strategy plus material alpha-beta fallback.

One visit budget for both algorithms. Visits are comparable bookkeeping units,
not equal primitive work: report time separately. No production player changes.
"""
from dataclasses import dataclass
import math
from time import perf_counter

from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from generic_chess.core.movegen import legal_actions as public_legal_actions
from generic_chess.core.terminal import TerminalStatus, terminal_result
from scripts.generic_win_proof import (
    prove_win, StrategyCursor, CertificateVerificationError, PROVEN_WIN, _Budget, _Interrupted, _ordered,
)


@dataclass(frozen=True)
class HybridDecision:
    action: object | None
    source: str
    proof_reason: str
    nodes: int
    proof_nodes: int
    verification_nodes: int
    search_nodes: int
    seconds: float
    completed_depth: int
    exit_cause: str
    proof_rank: int | None = None


class ProofMaterialPlayer:
    """Both colors must use the same fixed options in a controlled experiment.

    evaluate(position, target) is material-only in the learning assay; the proof
    never receives it. Call observe(state, action) for EVERY committed move.
    The normal arm uses the identical class with proof_enabled=False.
    Explicit cancellation returns no action. A time cutoff may retain the last
    completed legal normal-search result, with actual elapsed cost and cause.
    """
    def __init__(self, compiled, evaluate, *, proof_enabled=True, max_depth=3, normal_search=None, proof_search=prove_win, proof_trigger=None, cursor_factory=None):
        if not isinstance(max_depth, int) or not 1 <= max_depth <= 64:
            raise ValueError('fallback max_depth must be in [1,64]')
        self.compiled, self.evaluate = compiled, evaluate
        self.proof_enabled, self.max_depth = proof_enabled, max_depth
        self.cursor = None
        self.normal_search = normal_search
        self.proof_search = proof_search
        self.proof_trigger = proof_trigger
        self.cursor_factory = cursor_factory

    def observe(self, state, action):
        if self.cursor is not None:
            try:
                self.cursor.advance(state, action)
            except ValueError:
                self.cursor = None

    def choose(self, state, *, max_nodes=4096, seconds=1.0, cancel=None,
               _clock=perf_counter):
        total = _Budget(max_nodes, seconds, cancel, _clock)
        proof_nodes = verification_nodes = search_nodes = 0
        reason, source, completed, cause = 'disabled', 'LEGAL_FALLBACK', 0, 'depth_budget'
        action = None
        rt = None

        def remaining_seconds():
            return max(0., seconds - total.elapsed())

        def out():
            return HybridDecision(action, source, reason,
                                  proof_nodes + verification_nodes + search_nodes,
                                  proof_nodes, verification_nodes, search_nodes,
                                  total.elapsed(), completed, cause,
                                  self.cursor.node.rank if self.cursor is not None and source in ('PROOF','PROOF_CONTINUATION') else None)

        try:
            total.poll()
            terminal = terminal_result(state, self.compiled)
            total.poll()  # Atomic rule execution may cross cancellation/deadline.
            if terminal.status is not TerminalStatus.ONGOING:
                source, cause = 'TERMINAL', 'actual_rule_terminal'
                return out()
            if self.proof_enabled and self.cursor is not None:
                try:
                    continuation = self.cursor.choose(state)
                    total.poll()
                    action = continuation
                except ValueError:
                    self.cursor = None
                if action is not None:
                    source, reason, cause = 'PROOF_CONTINUATION', 'verified_strategy', 'certificate'
                    return out()
            should_prove = self.proof_enabled and (self.proof_trigger is None or self.proof_trigger(state))
            if self.proof_enabled and not should_prove:
                reason = 'trigger_skipped'
            if should_prove:
                # Fixed allocation; never extend proof from a favorable result.
                quarter = max_nodes // 4
                result = self.proof_search(self.compiled, state, max_nodes=quarter,
                                   seconds=min(1., seconds / 4, remaining_seconds()),
                                   max_depth=64, cancel=cancel, _clock=_clock)
                proof_nodes, reason = result.nodes, result.reason
                if result.status == PROVEN_WIN:
                    # Verification uses the next quarter; failed verification
                    # means UNKNOWN and still leaves half the visits for AB.
                    try:
                        cursor = (self.cursor_factory or StrategyCursor)(self.compiled, result.certificate,
                                                max_nodes=quarter,
                                                seconds=min(seconds / 4, remaining_seconds()),
                                                cancel=cancel, _clock=_clock)
                        verification_nodes = cursor.receipt['nodes']
                        total.poll()
                        selected = cursor.choose(state)
                        total.poll()
                        action = selected
                        self.cursor = cursor
                        source, cause = 'PROOF', 'certificate'
                        return out()
                    except CertificateVerificationError as error:
                        verification_nodes = error.receipt['nodes']
                        reason = 'verification_' + error.receipt['reason']
            total.poll()
            try:
                rt = SearchPathRuntime.from_state(state, self.compiled)
            except (NotImplementedError, IncompleteAdjudicationHistoryError):
                # Proof/runtime scope must not disable a caller-supplied normal
                # player. Public legality still binds the complete GameState.
                # This atomic generation is charged to the caller's time.
                rt = None
                legal = _ordered(public_legal_actions(state, self.compiled))
            else:
                legal = _ordered(rt.legal_actions(checkpoint=total.poll))
            total.poll()
            if not legal:
                source, cause = 'NO_ACTION', 'no_legal_action'
                return out()
            action = legal[0]
            remaining_nodes = max_nodes - proof_nodes - verification_nodes
            if self.normal_search is not None and remaining_nodes > 0:
                selected, used_nodes = self.normal_search(
                    state, remaining_nodes, remaining_seconds(), cancel)
                if selected not in legal or type(used_nodes) is not int or used_nodes < 0:
                    raise ValueError('invalid external search receipt')
                search_nodes = used_nodes
                action, source = selected, 'EXTERNAL_SEARCH'
                # The provider is an atomic boundary. Preserve its actual work
                # receipt before polling; cancellation must not dispatch its
                # move, while a deadline retains the completed normal result.
                total.poll()
                # Mature engines may overshoot requested nodes. Preserve actual
                # counts rather than silently clipping them into a fair cap.
                cause = ('reported_node_overrun' if used_nodes > remaining_nodes
                         else 'external_search_return')
                return out()
            if rt is None:
                cause = 'public_legal_fallback_unsupported_runtime'
                return out()
            search = _Budget(remaining_nodes, remaining_seconds(), cancel, _clock)
            target = state.position.side_to_move

            def ab(depth, alpha, beta):
                search.visit()
                t = rt.terminal_status
                if t.status is not TerminalStatus.ONGOING:
                    return 0. if t.winner is None else (math.inf if t.winner == target else -math.inf)
                if depth == 0:
                    return float(self.evaluate(rt.position, target))
                actions = _ordered(rt.legal_actions(checkpoint=search.poll))
                if not actions:
                    raise RuntimeError('ongoing state without legal actions')
                maximizing = rt.position.side_to_move == target
                value = -math.inf if maximizing else math.inf
                for a in actions:
                    rt.push(a, checkpoint=search.poll)
                    try:
                        score = ab(depth - 1, alpha, beta)
                    finally:
                        rt.pop()
                    if maximizing:
                        value, alpha = max(value, score), max(alpha, score)
                    else:
                        value, beta = min(value, score), min(beta, score)
                    if alpha >= beta:
                        break
                return value

            try:
                for depth in range(1, self.max_depth + 1):
                    best_action, best = legal[0], -math.inf
                    for a in legal:
                        search.poll()
                        rt.push(a, checkpoint=search.poll)
                        try:
                            score = ab(depth - 1, -math.inf, math.inf)
                        finally:
                            rt.pop()
                        if score > best:
                            best_action, best = a, score
                    search.poll()
                    action, completed, source = best_action, depth, 'MATERIAL_SEARCH'
            except _Interrupted:
                cause = search.reason
                if cause == 'cancelled':action = None
            finally:
                search_nodes = search.nodes
        except _Interrupted:
            cause = total.reason
            if cause == 'cancelled':action = None
        finally:
            if rt is not None:
                rt.assert_balanced()
        return out()
