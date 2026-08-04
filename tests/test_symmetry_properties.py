"""180-degree rotation symmetry: rotating the board and swapping sides."""

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square, index_to_square, rotate_square
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Position, Hands
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game


def rotate_position(position: Position, n: int) -> Position:
    """Rotate the whole position 180 degrees and swap the players."""
    board = [None] * (n * n)
    for idx, piece in enumerate(position.board):
        if piece is None:
            continue
        sq = index_to_square(idx, n)
        rsq = rotate_square(sq, n)
        board[rsq.rank * n + rsq.file] = Piece(
            owner=1 - piece.owner,
            base_type_id=piece.base_type_id,
            current_type_id=piece.current_type_id,
            promoted=piece.promoted,
        )
    return Position(
        board=tuple(board),
        hands=(position.hands[1], position.hands[0]),
        side_to_move=1 - position.side_to_move,
        ruleset_fingerprint=position.ruleset_fingerprint,
    )


def rotate_action(action, n: int):
    if isinstance(action, BoardMove):
        return BoardMove(
            rotate_square(action.from_square, n),
            rotate_square(action.to_square, n),
            action.promotion_target_id,
        )
    return DropMove(action.base_type_id, rotate_square(action.to_square, n))


def _generated():
    return generate_game(GeneratorConfig(seed=123))


def test_initial_position_is_180_degree_symmetric():
    game = _generated()
    compiled = game.compiled_ruleset
    n = compiled.board_size
    rotated = rotate_position(compiled.initial_position, n)
    for idx, piece in enumerate(rotated.board):
        if piece is None:
            assert compiled.initial_position.board[idx] is None
        else:
            other = compiled.initial_position.board[idx]
            assert other is not None
            assert piece.owner == other.owner
            assert piece.base_type_id == other.base_type_id
            assert piece.current_type_id == other.current_type_id
            assert piece.promoted == other.promoted


def test_legal_action_sets_rotate_correspondingly():
    game = _generated()
    compiled = game.compiled_ruleset
    n = compiled.board_size
    pos = compiled.initial_position
    actions = legal_actions_from_position(pos, compiled)
    rotated_pos = rotate_position(pos, n)
    rotated_actions = legal_actions_from_position(rotated_pos, compiled)
    expected = {rotate_action(a, n) for a in actions}
    assert expected == set(rotated_actions)


def test_symmetry_holds_after_random_plies():
    import random

    game = _generated()
    compiled = game.compiled_ruleset
    n = compiled.board_size
    rng = random.Random(99)
    state = initial_state(compiled)
    for _ in range(20):
        actions = legal_actions_from_position(state.position, compiled)
        if not actions:
            break
        state = apply_action(state, rng.choice(actions), compiled)
        rotated = rotate_position(state.position, n)
        expected = {rotate_action(a, n) for a in legal_actions_from_position(state.position, compiled)}
        assert expected == set(legal_actions_from_position(rotated, compiled))
