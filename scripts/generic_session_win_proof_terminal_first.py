"""Opt-in actual terminal-successor ordering; no material/check heuristic.

Claims preserve their lazy id order. Already eager board successors are ordered
by actual modeled terminal result, favorable for the mover in the target-win
query first, then other terminal results, then ongoing successors. Every board
record is constructed before ordering, so eager work and elapsed time remain
important; fewer visited nodes alone is not an equal-work speedup.
The model is untrusted until the real GameSession certificate verifier passes.
"""
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import _children, prove_session_win_batch_pn


def _terminal_children(current, budget, cost, target):
    iterator = _children(current, budget, cost)
    # Do not consume the board generator before a decisive claim is considered.
    owned = sum(d.owner == current.state.position.side_to_move for d in current.compiled.declarations)
    for _ in range(owned):
        yield next(iterator)
    board = list(iterator)
    own = current.state.position.side_to_move == target
    def key(row):
        index, (_, child) = row
        terminal = child.result.status is not SessionStatus.ONGOING
        decisive = terminal and ((child.result.winner == target) if own else (child.result.winner != target))
        return (0 if decisive else 1 if terminal else 2, index)
    for _, pair in sorted(enumerate(board), key=key):
        budget.poll()
        yield pair


def prove_session_win_terminal_first(session, *, target=None, **kwargs):
    target = session.state.position.side_to_move if target is None else target
    return prove_session_win_batch_pn(session, target=target,
        _children_factory=lambda s, b, c: _terminal_children(s, b, c, target), **kwargs)
