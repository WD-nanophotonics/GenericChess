"""Research-only capture-complete adapter for native Chess child pairs."""
from generic_chess.ai.alphabeta.quiescence import classify_noisy


def opponent_removal(state, child):
    """Requires a legal native Chess edge; not an arbitrary semantic rule."""
    opponent = 1-state.position.side_to_move
    before = sum(p is not None and p.owner == opponent for p in state.position.board)
    after = sum(p is not None and p.owner == opponent for p in child.position.board)
    return before > after


def native_chess_noisy(state, successors, compiled, stats=None):
    result = []
    for action, child in successors:
        if opponent_removal(state, child):
            result.append(action)
            if stats is not None: stats.capture_qactions += 1
        else:
            result.extend(classify_noisy(state, [(action, child)], compiled, stats))
    return result
