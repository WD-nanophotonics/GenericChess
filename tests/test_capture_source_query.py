from dataclasses import replace

import pytest

from generic_chess.core.capture_sources import query_capture_sources
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import (
    compile_ruleset_for_execution,
    compile_semantic_ruleset,
)
from generic_chess.rules.schema import RuleActionEffect, RuleSquareRef
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from ai_fixtures import build_4x4_rooks
from rule_semantics_ir_fixtures import cannon_ruleset


def _position(compiled, pieces, side=0):
    position = initial_state(compiled).position
    board = [None] * len(position.board)
    shape = position.board_shape
    for square, piece in pieces:
        index = square_to_index(square, shape)
        assert board[index] is None
        board[index] = piece
    return replace(position, board=tuple(board), side_to_move=side)


@pytest.fixture(scope="module")
def xiangqi():
    compiled = compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset())
    return compiled, SemanticEngine(compiled)


def _xiangqi_cannon_position(compiled, screens):
    pieces = [
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(4, 9), Piece(1, "G", "G")),
        (Square(0, 4), Piece(0, "C", "C")),
        (Square(4, 4), Piece(1, "S", "S")),
    ]
    pieces.extend((Square(file, 4), Piece(1, "S", "S")) for file in screens)
    return _position(compiled, pieces)


def test_xiangqi_cannon_capture_query_respects_zero_one_two_screens(xiangqi):
    compiled, engine = xiangqi
    target = Square(4, 4)
    source = Square(0, 4)
    cases = (((), False), ((2,), True), ((2, 3), False))
    for screens, expected in cases:
        position = _xiangqi_cannon_position(compiled, screens)
        result = query_capture_sources(position, target, 0, compiled)
        target_index = square_to_index(target, position.board_shape)
        assert (source in result.pseudo_attack_sources) is expected
        assert (source in result.pseudo_capture_sources) is expected
        assert engine.is_square_attacked(position, target_index, 0) is expected
        assert (source in result.legal_capture_sources) is expected

        off_turn = query_capture_sources(
            replace(position, side_to_move=1), target, 0, compiled
        )
        assert off_turn.pseudo_capture_sources == result.pseudo_capture_sources
        assert off_turn.legal_capture_sources is None


def test_xiangqi_horse_source_query_respects_blocked_leg(xiangqi):
    compiled, engine = xiangqi
    source = Square(1, 2)
    target = Square(3, 3)
    kings_and_horse = [
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(4, 9), Piece(1, "G", "G")),
        (Square(4, 5), Piece(1, "S", "S")),  # keep the Generals from facing
        (source, Piece(0, "H", "H")),
        (target, Piece(1, "S", "S")),
    ]
    for blocked, expected in ((False, True), (True, False)):
        pieces = list(kings_and_horse)
        if blocked:
            pieces.append((Square(2, 2), Piece(1, "S", "S")))
        position = _position(compiled, pieces)
        result = query_capture_sources(position, target, 0, compiled)
        target_index = square_to_index(target, position.board_shape)
        assert (source in result.pseudo_attack_sources) is expected
        assert (source in result.pseudo_capture_sources) is expected
        assert engine.is_square_attacked(position, target_index, 0) is expected
        assert (source in result.legal_capture_sources) is expected
        off_turn = query_capture_sources(
            replace(position, side_to_move=1), target, 0, compiled
        )
        assert off_turn.pseudo_capture_sources == result.pseudo_capture_sources
        assert off_turn.legal_capture_sources is None


def test_western_chess_distinguishes_pinned_pseudoattacker_from_legal_capture():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = SemanticEngine(compiled)
    source = Square(4, 1)  # white rook, pinned on the king's file
    target = Square(6, 1)  # two files away; not also attacked by the white King
    position = _position(
        compiled,
        [
            (Square(4, 0), Piece(0, "K", "K")),
            (Square(7, 7), Piece(1, "K", "K")),
            (source, Piece(0, "R", "R")),
            (Square(4, 7), Piece(1, "R", "R")),
            (target, Piece(1, "P", "P")),
        ],
    )

    result = query_capture_sources(position, target, 0, compiled)
    target_index = square_to_index(target, position.board_shape)
    assert result.pseudo_attack_sources == (source,)
    assert result.pseudo_capture_sources == (source,)
    assert result.legal_capture_sources == ()
    assert engine.is_square_attacked(position, target_index, 0) is True


def test_legacy_capture_source_uses_existing_geometry_and_legal_move_authority():
    compiled = build_4x4_rooks()
    source = Square(1, 1)
    target = Square(1, 2)
    position = _position(
        compiled,
        [
            (Square(0, 0), Piece(0, "K", "K")),
            (Square(3, 3), Piece(1, "K", "K")),
            (source, Piece(0, "R", "R")),
            (target, Piece(1, "R", "R")),
        ],
    )
    result = query_capture_sources(position, target, 0, compiled)
    assert result.pseudo_attack_sources == (source,)
    assert result.pseudo_capture_sources == (source,)
    assert result.legal_capture_sources == (source,)

    not_moving = replace(position, side_to_move=1)
    hypothetical = query_capture_sources(not_moving, target, 0, compiled)
    assert hypothetical.pseudo_attack_sources == (source,)
    assert hypothetical.pseudo_capture_sources == (source,)
    assert hypothetical.legal_capture_sources is None


def test_capture_query_requires_an_occupied_enemy_target(xiangqi):
    compiled, _engine = xiangqi
    position = _xiangqi_cannon_position(compiled, (2,))
    with pytest.raises(ValueError, match="opponent"):
        query_capture_sources(position, Square(0, 4), 0, compiled)
    with pytest.raises(ValueError, match="outside"):
        query_capture_sources(position, Square(9, 4), 0, compiled)


def test_enemy_target_action_without_target_removal_is_not_reported_as_capture():
    ruleset = cannon_ruleset()
    actions = tuple(
        replace(
            action,
            effects=(
                RuleActionEffect(
                    "move",
                    from_ref=RuleSquareRef(kind="source"),
                    to_ref=RuleSquareRef(kind="fixed", square=(0, 1)),
                ),
            ),
        )
        if action.name == "cannon_capture"
        else action
        for action in ruleset.semantic_actions
    )
    compiled = compile_semantic_ruleset(replace(ruleset, semantic_actions=actions))
    engine = SemanticEngine(compiled)
    source = Square(0, 0)
    target = Square(2, 0)
    position = _position(
        compiled,
        [
            (Square(7, 7), Piece(0, "K", "K")),
            (Square(1, 0), Piece(1, "K", "K")),  # one screen
            (target, Piece(1, "C", "C")),
            (source, Piece(0, "C", "C")),
        ],
    )

    result = query_capture_sources(position, target, 0, compiled)
    assert result.pseudo_attack_sources == (source,)
    assert result.pseudo_capture_sources == ()
    assert result.legal_capture_sources == ()

    source_index = square_to_index(source, position.board_shape)
    target_index = square_to_index(target, position.board_shape)
    action = next(
        candidate
        for candidate in engine.iter_legal_actions(position)
        if candidate.source == source_index and candidate.target == target_index
    )
    after = engine.apply(position, action)
    assert after.board[target_index] == Piece(1, "C", "C")
    assert after.board[square_to_index(Square(0, 1), position.board_shape)] == Piece(
        0, "C", "C"
    )
