"""Exact small Chess transposition witness for history-weighted contexts."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from scripts.audit_f24f_western_chess_perft import standard_engine


def square_index(square):
    return square.rank * 8 + square.file


def play(state, compiled, source, target):
    matches = [action for action in legal_actions(state, compiled)
               if square_index(action.from_square) == source
               and square_index(action.to_square) == target]
    assert len(matches) == 1, (source, target, len(matches))
    return apply_action(state, matches[0], compiled)


def audit():
    compiled, _ = standard_engine()
    # Four commute-order histories; the last history has a distinct final board.
    routes = (
        ((6, 21), (62, 45), (1, 18), (57, 42)),
        ((1, 18), (62, 45), (6, 21), (57, 42)),
        ((6, 21), (57, 42), (1, 18), (62, 45)),
        ((1, 18), (57, 42), (6, 21), (62, 45)),
        ((6, 21), (62, 45), (1, 18), (48, 40)),
    )
    finals = []
    for route in routes:
        state = initial_state(compiled)
        for source, target in route:
            state = play(state, compiled, source, target)
        finals.append(state)
    first = finals[0].position
    assert all(state.position == first for state in finals[:4])
    assert finals[4].position != first
    assert all(state.ply_count == 4 for state in finals)
    unique_positions = []
    for state in finals:
        if not any(state.position == position for position in unique_positions):
            unique_positions.append(state.position)
    return {
        "histories": len(routes),
        "shared_position_histories": 4,
        "distinct_positions": len(unique_positions),
        "history_uniform_shared_mass": "4/5",
        "position_uniform_shared_mass": "1/2",
        "shared_position_same_ply": True,
        "shared_position_same_auxiliary": all(
            state.position.aux_state == first.aux_state for state in finals[:4]
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
