"""Experimental rule-history checking-move ordering; quiet moves remain present.

No tsume/check-only restriction, material price, extra attack query or TT. Reuse
already authoritative Core successor history.gave_check merely as a tie order,
with actual terminal result first. All owned declaration choices remain lazy.
Actual Session certificate verification is mandatory before play.
"""
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import _children, prove_session_win_batch_pn


def _checking_children(current, budget, cost, target):
    iterator = _children(current, budget, cost)
    owned = sum(d.owner == current.state.position.side_to_move for d in current.compiled.declarations)
    for _ in range(owned): yield next(iterator)
    board = list(iterator)
    own = current.state.position.side_to_move == target
    def key(row):
        index, (_, child) = row
        terminal = child.result.status is not SessionStatus.ONGOING
        decisive = terminal and ((child.result.winner == target) if own else (child.result.winner != target))
        # This hint never establishes legality or a proof. A true public move
        # appends its event; pass history correctly records gave_check=False.
        checking = len(child.state.history) == len(current.state.history) + 1 and child.state.history[-1].gave_check
        return (0 if decisive else 1 if terminal else 2 if checking else 3, index)
    for _, pair in sorted(enumerate(board), key=key):
        budget.poll()
        yield pair


def prove_session_win_check_first(session, *, target=None, **kwargs):
    target = session.state.position.side_to_move if target is None else target
    return prove_session_win_batch_pn(session, target=target,
        _children_factory=lambda s, b, c: _checking_children(s, b, c, target), **kwargs)
