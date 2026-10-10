"""One shared-budget iterative caller for finite root diagnostics.

No player or production-search replacement. Board adapters own full terminal,
legality, history and evaluation semantics. The timer includes root preparation;
PV legality validation is separately timed and included in total caller time.
A slow adapter call can overrun a soft deadline; this is explicitly observable.
Only fully completed root iterations replace the returned decision. The first
legal root action is the common fallback if no iteration completes.
"""
from time import perf_counter
from scripts.root_bound_diagnostic import root_search


def iterative_root_search(board, *, seconds, node_limit, max_depth=12):
    start = perf_counter()
    terminal = board.terminal(0)
    if terminal is not None:
        return dict(move=None, action=None, score=terminal, pv_labels=[],
                    completed_depth=0, exit_cause='terminal_position',
                    work={}, iterations=[], used_fallback=False,
                    preparation_seconds=perf_counter()-start,
                    search_seconds=0., validation_seconds=0.,
                    caller_seconds=perf_counter()-start, root_restored=board.restored())
    frontier = board.actions()
    if not frontier:
        raise ValueError('nonterminal diagnostic root has no legal action')
    first = frontier[0]
    keys = {move: label for label, move in frontier}
    preparation = perf_counter()-start
    total, iterations, completed = {}, [], None
    for depth in range(1, max_depth+1):
        result = root_search(board, depth, mode='verified',
            canonical_key=keys.__getitem__, node_limit=node_limit-total.get('nodes',0),
            seconds=seconds-(perf_counter()-start))
        for key, value in result['work'].items():
            total[key] = total.get(key,0)+value
        iterations.append(result)
        if not result['completed_depth']:
            break
        completed = result
    search_finished = perf_counter()
    action = completed['action'] if completed else first[1]
    pv = completed['pv'] if completed else (action,)
    labels = []
    pushed = 0
    try:
        for move in pv:
            frontier = {m: label for label, m in board.actions()}
            if move not in frontier:
                raise AssertionError('diagnostic PV contains illegal action')
            labels.append(frontier[move])
            board.push(move)
            pushed += 1
    finally:
        for _ in range(pushed):
            board.pop()
    end = perf_counter()
    if not board.restored() or total.get('nodes',0)>node_limit:
        raise AssertionError('diagnostic root/cap invariant')
    return dict(move=completed['move'] if completed else first[0], action=action,
                score=completed['score'] if completed else None, pv_labels=labels,
                completed_depth=completed['completed_depth'] if completed else 0,
                used_fallback=completed is None,
                exit_cause=iterations[-1]['exit_cause'] if iterations else 'depth_limit',
                work=total, iterations=iterations, preparation_seconds=preparation,
                search_seconds=search_finished-start-preparation,
                validation_seconds=end-search_finished, caller_seconds=end-start,
                budgeted_seconds=search_finished-start, cap_seconds=seconds,
                cap_nodes=node_limit, root_restored=True)
