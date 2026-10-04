"""Bounded goal intervals, independent of search evaluators and material prices."""
from dataclasses import asdict, dataclass
from math import isfinite
from time import monotonic

from generic_chess.core.movegen import iter_legal_actions
from generic_chess.core.declarations import DeclarationAssessment, assess_declaration, available_declarations
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action


UNKNOWN = (-1, 1)


@dataclass(frozen=True)
class _ClaimLeaf:
    assessment: DeclarationAssessment


@dataclass(frozen=True)
class _ClaimResult:
    winner: int | None
    status: str = 'declaration'
    is_terminal: bool = True
    unresolved: bool = False


class PublicGame:
    def __init__(self, compiled):
        self.compiled = compiled

    def terminal(self, state):
        if isinstance(state, _ClaimLeaf):
            assessment = state.assessment
            if assessment.outcome not in ('WIN', 'DRAW', 'RESTART'):
                raise ValueError('unqualified declaration outcome')
            return _ClaimResult(assessment.actor if assessment.outcome == 'WIN' else None,
                                unresolved=assessment.outcome == 'RESTART')
        fresh = terminal_result(state, self.compiled)
        if fresh != state.terminal_status:
            raise ValueError('stale cached terminal status')
        return fresh

    def owner(self, state):
        return state.position.side_to_move

    def actions(self, state, checkpoint):
        checkpoint()
        declarations = available_declarations(state, self.compiled)
        checkpoint()
        yield from declarations
        yield from iter_legal_actions(state, self.compiled, checkpoint=checkpoint)

    def is_materialization(self, action):
        return not isinstance(action, DeclarationAssessment)

    def successor(self, state, action):
        if isinstance(action, DeclarationAssessment):
            fresh = assess_declaration(state, self.compiled, action.declaration_id)
            if fresh != action or action.actor != state.position.side_to_move:
                raise ValueError('stale declaration assessment')
            return _ClaimLeaf(fresh)
        return apply_action(state, action, self.compiled)


@dataclass
class Observation:
    interval: tuple = UNKNOWN
    visits: int = 0
    transitions: int = 0
    public_materializations: int = 0
    unknown_leaves: int = 0
    depth_cutoffs: int = 0
    range_shortcuts: int = 0
    interrupted_nodes: int = 0
    stop_reasons: tuple = ()
    elapsed_seconds: float = 0


class _TimeLimit(Exception):
    pass


def observe(root, game, *, depth, max_transitions=64, max_visits=256,
            seconds=5, censored_statuses=(), clock=monotonic):
    """Return sound owner-zero bounds; no completeness claim from a cutoff.

    The adapter must enumerate every legal action and provide authoritative
    terminal status. Censoring only widens labels; it cannot establish a new
    game's continuation semantics. The time cap is cooperative, not preemptive.
    """
    if any(type(x) is not int or x < 0 for x in (depth, max_transitions, max_visits)):
        raise ValueError('nonnegative integer limits required')
    if not isfinite(seconds) or seconds < 0:
        raise ValueError('finite nonnegative seconds required')
    censored = frozenset(censored_statuses)
    if any(not isinstance(s, TerminalStatus) or s is TerminalStatus.ONGOING for s in censored):
        raise ValueError('censor only explicit terminal statuses')
    started = clock()
    stats = Observation()
    reasons = set()

    def checkpoint():
        if clock() - started >= seconds:
            reasons.add('time')
            raise _TimeLimit()

    def unknown():
        stats.unknown_leaves += 1
        return UNKNOWN

    def visit(state, remaining):
        checkpoint()
        if stats.visits >= max_visits:
            reasons.add('visits')
            return unknown()
        stats.visits += 1
        terminal = game.terminal(state)
        checkpoint()
        if terminal.is_terminal:
            if (terminal.status in censored or terminal.status is TerminalStatus.NO_CONTEST
                    or getattr(terminal, 'unresolved', False)):
                return unknown()
            if terminal.winner not in (None, 0, 1):
                raise ValueError('invalid terminal winner')
            value = 0 if terminal.winner is None else 1 if terminal.winner == 0 else -1
            return (value, value)
        if remaining == 0:
            stats.depth_cutoffs += 1
            return unknown()
        owner = game.owner(state)
        if owner not in (0, 1):
            raise ValueError('two-player owner required')
        children = []
        exhausted = False
        try:
            for action in game.actions(state, checkpoint):
                checkpoint()
                if stats.transitions >= max_transitions:
                    reasons.add('transitions')
                    break
                if stats.visits >= max_visits:
                    reasons.add('visits')
                    break
                stats.transitions += 1
                if getattr(game, 'is_materialization', lambda action: False)(action):
                    stats.public_materializations += 1
                child = game.successor(state, action)
                children.append(visit(child, remaining-1))
                # Range dominance justifies an exact label without all actions.
                if owner == 0 and children[-1][0] == 1 or owner == 1 and children[-1][1] == -1:
                    stats.range_shortcuts += 1
                    return (1, 1) if owner == 0 else (-1, -1)
            else:
                exhausted = True
        except _TimeLimit:
            pass
        if not exhausted:
            stats.interrupted_nodes += 1
            children.append(unknown())
        if not children:
            raise ValueError('ongoing empty legal action set')
        combine = max if owner == 0 else min
        return (combine(pair[0] for pair in children), combine(pair[1] for pair in children))

    try:
        stats.interval = visit(root, depth)
    except _TimeLimit:
        stats.interval = unknown()
    stats.stop_reasons = tuple(sorted(reasons))
    stats.elapsed_seconds = clock() - started
    return asdict(stats)
