"""Finite SESSION-terminal payoff, explicitly distinct from eventual value."""
from scripts.partial_decision_loss import paired_margin
from generic_chess.core.terminal import TerminalStatus

UNKNOWN = (-1, 1)
QUALIFIED = {TerminalStatus.CHECKMATE, TerminalStatus.STALEMATE,
             TerminalStatus.MAX_PLY, TerminalStatus.REPETITION}


def leaf_intervals(terminal):
    if not terminal.is_terminal:
        return {'window': (0, 0), 'eventual': UNKNOWN}
    if getattr(terminal, 'unresolved', False) or terminal.status not in QUALIFIED:
        return {'window': UNKNOWN, 'eventual': UNKNOWN}
    winner = terminal.winner
    if (terminal.status is TerminalStatus.CHECKMATE and type(winner) is not int
            or winner is not None and (type(winner) is not int or winner not in (0, 1))
            or terminal.status is not TerminalStatus.CHECKMATE and winner is not None):
        raise ValueError('unqualified terminal winner')
    value = 0 if winner is None else 1 if winner == 0 else -1
    return {'window': (value, value), 'eventual': (value, value)}


def combine_replies(rows, *, owner, complete):
    if type(owner) is not int or owner not in (0, 1) or type(complete) is not bool:
        raise ValueError('explicit owner and completeness required')
    if not rows and complete:
        raise ValueError('ongoing node cannot have empty complete replies')
    result = {}
    for target in ('window', 'eventual'):
        pairs = [row[target] for row in rows]
        if any(len(p) != 2 or any(type(x) is not int for x in p)
               or not -1 <= p[0] <= p[1] <= 1 for p in pairs):
            raise ValueError('exact utility bounds required')
        if not complete:
            pairs.append(UNKNOWN)
        operation = max if owner == 0 else min
        result[target] = tuple(operation(pair[i] for pair in pairs) for i in (0, 1))
    return result


def tie_margin(intervals, candidate_ties, baseline_ties, *, owner):
    if not candidate_ties or not baseline_ties:
        raise ValueError('complete nonempty tie sets required')
    pairs = [paired_margin(intervals, a, b, owner)
             for a in candidate_ties for b in baseline_ties]
    return min(p[0] for p in pairs), max(p[1] for p in pairs)
