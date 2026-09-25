from dataclasses import replace

from ai_fixtures import king, rook
from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleSet


def _capture_and_drop_ruleset():
    rows = [[None] * 4 for _ in range(4)]
    rows[3][0] = Piece(0, "K", "K")
    rows[0][3] = Piece(1, "K", "K")
    rows[2][1] = Piece(0, "R", "R")
    rows[2][2] = Piece(0, "R", "R")
    rows[1][2] = Piece(1, "R", "R")
    mask = (True,) * 16
    return compile_ruleset(
        RuleSet(
            board_size=4,
            piece_types=(king(), rook()),
            initial_position=tuple(tuple(row) for row in rows),
            drop_allowed={"R": (mask, mask)},
            promotion_allowed={},
            promotion_forced={},
        )
    )


def _same_type_reoccupancy_ruleset():
    rows = [[None] * 5 for _ in range(5)]
    rows[0][0] = Piece(0, "K", "K")
    rows[4][4] = Piece(1, "K", "K")
    rows[2][1] = Piece(0, "R", "R")
    rows[0][1] = Piece(0, "R", "R")
    mask = (True,) * 25
    return compile_ruleset(
        RuleSet(
            board_size=5,
            piece_types=(king(), rook()),
            initial_position=tuple(tuple(row) for row in rows),
            drop_allowed={"R": (mask, mask)},
            promotion_allowed={},
            promotion_forced={},
        )
    )


def _submit(state, compiled, action_type, source=None, target=None):
    for action in legal_actions(state, compiled):
        if not isinstance(action, action_type):
            continue
        if source is not None and action.from_square != source:
            continue
        if action.to_square != target:
            continue
        return apply_action(state, action, compiled)
    raise AssertionError(f"no legal {action_type.__name__} {source} -> {target}")


def test_same_type_piece_reoccupying_vacated_square_gets_its_own_identity():
    compiled = _same_type_reoccupancy_ruleset()
    state = initial_state(compiled)
    vacated = square_to_index(Square(1, 2), 5)
    origin_b = square_to_index(Square(1, 0), 5)
    initial = reconstruct_history_provenance(state, compiled)
    id_a = initial.frames[0].identities[vacated]
    id_b = initial.frames[0].identities[origin_b]
    assert initial.status == "verified"
    assert id_a is not None and id_b is not None and id_a != id_b

    state = _submit(state, compiled, BoardMove, Square(1, 2), Square(1, 3))
    # Let the other side make a harmless king move, then move B into A's old square.
    state = _submit(state, compiled, BoardMove, Square(4, 4), Square(3, 4))
    state = _submit(state, compiled, BoardMove, Square(1, 0), Square(1, 2))

    result = reconstruct_history_provenance(state, compiled)
    assert result.status == "verified"
    assert result.frames[1].identities[vacated] is None
    assert result.frames[-1].identities[vacated] == id_b
    assert result.frames[-1].identities[vacated] != id_a


def test_reconstruction_tracks_same_type_instances_and_capture_drop_boundary():
    compiled = _capture_and_drop_ruleset()
    state = initial_state(compiled)
    original_a = square_to_index(Square(1, 2), 4)
    original_b = square_to_index(Square(2, 2), 4)
    capture_square = square_to_index(Square(1, 1), 4)

    initial = reconstruct_history_provenance(state, compiled)
    assert initial.status == "verified"
    assert initial.frames[0].position == state.position
    id_a = initial.frames[0].identities[original_a]
    id_b = initial.frames[0].identities[original_b]
    assert id_a is not None and id_b is not None and id_a != id_b

    state = _submit(state, compiled, BoardMove, Square(1, 2), Square(1, 1))
    after_move = reconstruct_history_provenance(state, compiled)
    assert after_move.status == "verified"
    assert after_move.frames[-1].identities[capture_square] == id_a
    assert after_move.frames[-1].identities[original_b] == id_b

    state = _submit(state, compiled, BoardMove, Square(2, 1), Square(1, 1))
    after_capture = reconstruct_history_provenance(state, compiled)
    assert after_capture.status == "verified"
    id_capturer = after_capture.frames[-1].identities[capture_square]
    assert id_capturer is not None and id_capturer != id_a
    assert id_a not in after_capture.frames[-1].identities
    assert after_capture.frames[-1].identities[original_b] == id_b

    state = _submit(state, compiled, BoardMove, Square(0, 3), Square(0, 2))
    state = _submit(state, compiled, DropMove, target=Square(3, 2))
    after_drop = reconstruct_history_provenance(state, compiled)
    assert after_drop.status == "verified"
    dropped = after_drop.frames[-1].identities[square_to_index(Square(3, 2), 4)]
    assert dropped is not None
    assert dropped not in after_drop.frames[-2].identities
    assert dropped != id_a and dropped != id_capturer and dropped != id_b


def test_incomplete_or_imported_history_returns_explicit_unknown():
    compiled = _capture_and_drop_ruleset()
    state = initial_state(compiled)
    state = _submit(state, compiled, BoardMove, Square(1, 2), Square(1, 1))

    truncated = replace(state, history=state.history[1:])
    result = reconstruct_history_provenance(truncated, compiled)
    assert result.status == "unknown"
    assert result.frames == ()
    assert result.reason

    imported_position = replace(state.position, side_to_move=1)
    imported = GameState(
        position=imported_position,
        ply_count=0,
        repetition_counts=state.repetition_counts,
        terminal_status=state.terminal_status,
        history=(),
    )
    assert reconstruct_history_provenance(imported, compiled).status == "unknown"
