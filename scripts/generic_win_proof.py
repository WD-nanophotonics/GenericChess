"""Bounded rule-driven winning-strategy prototype; no material or tablebase input.

Research entry only. Board actions include quiet moves, drops, promotions and
pass. Declaration choices and no-progress rules are explicitly unsupported in
v1. A finite all-defense tree is a win witness, not a complete WDL oracle.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from time import perf_counter

from generic_chess.core.actions import Action, action_to_dict
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from generic_chess.core.position import GameState
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action

PROVEN_WIN = 'PROVEN_WIN'
UNKNOWN = 'UNKNOWN'
ALREADY_TERMINAL = 'ALREADY_TERMINAL'


@dataclass(frozen=True)
class ProofNode:
    """A tree: one OR edge, every AND edge, actual winning terminal leaves."""
    rank: int
    edges: tuple[tuple[Action, 'ProofNode'], ...] = ()
    terminal_kind: str | None = None


@dataclass(frozen=True)
class WinCertificate:
    ruleset_fingerprint: str
    root: GameState
    target: int
    tree: ProofNode


@dataclass(frozen=True)
class ProofResult:
    status: str
    certificate: WinCertificate | None
    reason: str
    nodes: int
    seconds: float
    completed_depth: int
    pushes: int = 0
    pops: int = 0
    terminal_kind: str | None = None
    winner: int | None = None
    peak_depth: int = 0


class _Interrupted(Exception):
    pass


class _Budget:
    def __init__(self, max_nodes, seconds, cancel, clock=perf_counter):
        if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes < 0:
            raise ValueError('max_nodes must be a nonnegative integer')
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('seconds must be finite and nonnegative')
        self.cap, self.seconds, self.cancel, self.clock = max_nodes, seconds, cancel, clock
        self.start = clock()
        self.nodes = 0
        self.reason = ''

    def poll(self):
        if self.cancel is not None and self.cancel():
            self.reason = 'cancelled'
        elif self.clock() - self.start >= self.seconds:
            self.reason = 'time_budget'
        if self.reason:
            raise _Interrupted(self.reason)

    def visit(self):
        self.poll()
        if self.nodes >= self.cap:
            self.reason = 'node_budget'
            raise _Interrupted(self.reason)
        self.nodes += 1

    def elapsed(self):
        return self.clock() - self.start


def _same_state(left, right):
    # Dataclass equality alone conflates bool/int aux values. Exact public
    # representation also binds full history/counts and explicit scalar types.
    return left == right and repr(left) == repr(right)


def _ordered(actions):
    return sorted(actions, key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))


def _unsupported(compiled):
    # Declarations are session choices, absent from Runtime.legal_actions().
    # Ignoring an opponent's claim would make an all-defense proof unsound.
    if getattr(compiled, 'declarations', ()):
        return 'unsupported_declarations'
    if getattr(compiled, 'no_progress_draw', None) is not None:
        return 'unsupported_no_progress_history'
    return None


def prove_win(compiled, state: GameState, *, target=None, max_nodes=4096,
              seconds=1.0, max_depth=64, cancel=None, _clock=perf_counter):
    """Find one finite forced win; UNKNOWN means neither draw nor disproved win.

    Counts every recursive visit, including repeated iterations and leaves.
    No transposition sharing: full path history remains authoritative. Deadlines
    are cooperative, polled inside legal generation and push as well as visits;
    an indivisible runtime import/terminal call can overrun, reported in seconds.
    """
    target = state.position.side_to_move if target is None else target
    if target not in (0, 1):
        raise ValueError('target must be player 0 or 1')
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 128:
        raise ValueError('max_depth must be an integer in [0, 128]')
    budget = _Budget(max_nodes, seconds, cancel, _clock)
    rt = None
    completed = 0

    def result(status, reason, tree=None, terminal=None):
        cert = None if tree is None else WinCertificate(compiled.ruleset_fingerprint, state, target, tree)
        return ProofResult(status, cert, reason, budget.nodes, budget.elapsed(), completed,
                           rt.pushes if rt else 0, rt.pops if rt else 0,
                           terminal.status.value if terminal else None,
                           terminal.winner if terminal else None, rt.peak_depth if rt else 0)

    def search(remaining):
        budget.visit()
        t = rt.terminal_status
        if t.status is not TerminalStatus.ONGOING:
            if t.winner == target:
                return True, ProofNode(0, terminal_kind=t.status.value)
            return False, None
        if remaining == 0:
            return None, None
        actions = _ordered(rt.legal_actions(checkpoint=budget.poll))
        budget.poll()
        if not actions:
            # Never infer an unreported terminal from an empty action list.
            return None, None
        is_or = rt.position.side_to_move == target
        edges = []
        unknown = False
        for action in actions:
            budget.poll()
            rt.push(action, checkpoint=budget.poll)
            try:
                value, tree = search(remaining - 1)
            finally:
                rt.pop()
            if is_or and value is True:
                return True, ProofNode(tree.rank + 1, ((action, tree),))
            if not is_or and value is False:
                return False, None
            unknown |= value is None
            if tree is not None:
                edges.append((action, tree))
        if unknown:
            return None, None
        if is_or:
            return False, None
        return True, ProofNode(1 + max(child.rank for _, child in edges), tuple(edges))

    try:
        budget.poll()
        unsupported = _unsupported(compiled)
        if unsupported:
            return result(UNKNOWN, unsupported)
        rt = SearchPathRuntime.from_state(state, compiled)
        # Public callers may supply a stale ongoing status: recompute root.
        rt.terminal_status = terminal_result(state, compiled)
        budget.poll()
        if state.terminal_status != rt.terminal_status:
            return result(UNKNOWN, 'inconsistent_root_terminal')
        if rt.terminal_status.status is not TerminalStatus.ONGOING:
            return result(ALREADY_TERMINAL, 'actual_rule_terminal', terminal=rt.terminal_status)
        for depth in range(max_depth + 1):
            value, tree = search(depth)
            budget.poll()
            completed = depth
            if value is True:
                return result(PROVEN_WIN, 'finite_all_defense_certificate', tree)
            if value is False:
                return result(UNKNOWN, 'no_forced_win_in_exhausted_tree')
        return result(UNKNOWN, 'depth_budget')
    except _Interrupted:
        return result(UNKNOWN, budget.reason)
    except IncompleteAdjudicationHistoryError:
        return result(UNKNOWN, 'incomplete_adjudication_history')
    except NotImplementedError:
        return result(UNKNOWN, 'unsupported_runtime_semantics')
    finally:
        if rt is not None:
            rt.assert_balanced()


def verify_certificate(compiled, state, certificate, *, max_nodes=65536,
                       seconds=1.0, cancel=None, _clock=perf_counter):
    """Independently enumerate every defense and replay the finite witness.

    Returns a verification receipt; timeout/unsupported/malformed is not verified.
    This verifier does not call the proof search, its ordering or its cache.
    """
    b = _Budget(max_nodes, seconds, cancel, _clock)
    rt = None
    leaves = {}
    reason = 'verified'
    valid = False

    def check(node):
        b.visit()
        if not isinstance(node, ProofNode) or type(node.rank) is not int or not 0 <= node.rank <= 128:
            return False
        t = rt.terminal_status
        if t.status is not TerminalStatus.ONGOING:
            ok = node.rank == 0 and not node.edges and node.terminal_kind == t.status.value and t.winner == certificate.target
            if ok:
                leaves[t.status.value] = leaves.get(t.status.value, 0) + 1
            return ok
        if node.rank == 0 or node.terminal_kind is not None:
            return False
        legal = set(rt.legal_actions(checkpoint=b.poll))
        actions = [a for a, _ in node.edges]
        if len(actions) != len(set(actions)) or not actions or not set(actions) <= legal:
            return False
        if rt.position.side_to_move == certificate.target:
            if len(actions) != 1:
                return False
        elif set(actions) != legal:
            return False
        for action, child in node.edges:
            if not isinstance(child, ProofNode) or child.rank >= node.rank:
                return False
            rt.push(action, checkpoint=b.poll)
            try:
                if not check(child):
                    return False
            finally:
                rt.pop()
        return node.rank == 1 + max(child.rank for _, child in node.edges)

    try:
        b.poll()
        if (not isinstance(certificate, WinCertificate)
                or not _same_state(certificate.root, state) or certificate.target not in (0, 1)
                or certificate.ruleset_fingerprint != compiled.ruleset_fingerprint):
            reason = 'root_binding_mismatch'
        elif _unsupported(compiled):
            reason = _unsupported(compiled)
        else:
            rt = SearchPathRuntime.from_state(state, compiled)
            rt.terminal_status = terminal_result(state, compiled)
            if state.terminal_status != rt.terminal_status:
                reason = 'inconsistent_root_terminal'
            else:
                valid = check(certificate.tree)
            b.poll()
            if not valid and reason == 'verified':
                reason = 'invalid_certificate'
    except _Interrupted:
        reason = b.reason
    except (NotImplementedError, TypeError, ValueError, AttributeError):
        reason = 'invalid_or_unsupported_certificate'
    finally:
        if rt is not None:
            rt.assert_balanced()
    return dict(verified=valid and reason == 'verified', reason=reason, nodes=b.nodes,
                seconds=b.elapsed(), terminal_leaves=leaves,
                pushes=rt.pushes if rt else 0, pops=rt.pops if rt else 0)


class CertificateVerificationError(ValueError):
    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__('unverified certificate: ' + receipt['reason'])


class StrategyCursor:
    """Execute one verified tree, rejecting any unexpected state/action.

    advance() observes both players' actual committed actions. The tree rank
    drops after every action, so preserving a win cannot postpone it forever.
    Public immutable transitions independently bind the complete history.
    """
    def __init__(self, compiled, certificate, *, max_nodes=65536, seconds=1.0,
                 cancel=None, _clock=perf_counter):
        receipt = verify_certificate(compiled, certificate.root, certificate,
                                     max_nodes=max_nodes, seconds=seconds,
                                     cancel=cancel, _clock=_clock)
        if not receipt['verified']:
            raise CertificateVerificationError(receipt)
        self.compiled, self.certificate = compiled, certificate
        self.state, self.node = certificate.root, certificate.tree
        self.receipt = receipt

    def choose(self, state):
        if not _same_state(state, self.state):
            raise ValueError('strategy state/history mismatch')
        if state.position.side_to_move != self.certificate.target or not self.node.edges:
            return None
        return self.node.edges[0][0]

    def advance(self, state, action):
        if not _same_state(state, self.state):
            raise ValueError('strategy state/history mismatch')
        matches = [child for a, child in self.node.edges if a == action]
        if len(matches) != 1:
            raise ValueError('action outside proved strategy')
        child_state = apply_action(state, action, self.compiled)
        self.state, self.node = child_state, matches[0]
        return child_state
