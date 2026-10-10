import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.actions import action_is_board, action_source_square, action_target_square
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import HistoryRecord
from generic_chess.core.semantic_executor import semantic_action_for, semantic_engine_for
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import (
    _compile_geometry_carrier,
    compile_ruleset_for_execution,
    compile_semantic_ruleset,
)
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset
from test_xiangqi_static_setup_fixture import _build_incomplete_static_xiangqi_setup_fixture


@pytest.mark.parametrize(
    "builder,serialized_sha,fingerprint,ir_sha",
    (
        (
            build_western_chess_ruleset,
            "cc57ed9bc3fc8d4381b2b65f733556f641a91ea0f8a285a785741374d9daf978",
            "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
            "9c56a182d005eb01149b3c6d8211cec5db22350c0f8c87d7a510a1943bbcbf00",
        ),
        (
            lambda: replace(build_standard_shogi_ruleset(), stalemate_result="draw"),
            "e00bdd7078e353babe0346b9292543e127b5f4230bf1b703a23b56d679663d13",
            "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
            "dba7039afb4c33a7f49028de14e23ec3e9fb3b2c04136ff6c15f2ab76bb179a4",
        ),
        (
            cannon_ruleset,
            "4a0bb3433c5d5825d620500ae5653356ea6a4866a2d4692f3fa64d1d0f905627",
            "816540704484bf2f964e47ce24970687961c4f31f535548408ea15f2a4db2c35",
            "9b35a423f13da6e5583436bcb05cac251bda8768b195a745f28bc5fadf50f5cb",
        ),
    ),
)
def test_default_capture_disposition_preserves_square_hashes(
    builder, serialized_sha, fingerprint, ir_sha
):
    rules = builder()
    assert rules.capture_disposition == "capture_to_hand"
    assert "capture_disposition" not in ruleset_to_dict(rules)
    assert hashlib.sha256(serialize_ruleset(rules).encode()).hexdigest() == serialized_sha
    assert compute_fingerprint(rules) == fingerprint
    assert hashlib.sha256(
        compile_semantic_ruleset(rules).ir.serialized().encode()
    ).hexdigest() == ir_sha


def test_nondefault_capture_disposition_roundtrips_and_invalid_values_fail_closed():
    rules = _build_incomplete_static_xiangqi_setup_fixture()
    assert rules.capture_disposition == "remove_from_game"
    serialized = ruleset_to_dict(rules)
    assert serialized["capture_disposition"] == "remove_from_game"
    restored = ruleset_from_dict(serialized)
    assert restored == rules
    assert restored.capture_disposition == "remove_from_game"
    assert serialize_ruleset(restored) == serialize_ruleset(rules)
    assert compute_fingerprint(restored) != compute_fingerprint(
        replace(restored, capture_disposition="capture_to_hand")
    )

    invalid_data = dict(serialized, capture_disposition="discard_somehow")
    with pytest.raises(RuleValidationError, match="CAPTURE_DISPOSITION_INVALID"):
        ruleset_from_dict(invalid_data)

    invalid_rules = replace(rules, capture_disposition="discard_somehow")
    with pytest.raises(RuleValidationError, match="CAPTURE_DISPOSITION_INVALID"):
        _compile_geometry_carrier(invalid_rules)


@pytest.mark.parametrize(
    "builder,pieces,source,target,victim,hand_piece",
    (
        (
            build_western_chess_ruleset,
            (
                (0, "K", "K", False, Square(4, 0)),
                (1, "K", "K", False, Square(4, 7)),
                (0, "R", "R", False, Square(0, 0)),
                (1, "P", "P", False, Square(0, 1)),
            ),
            Square(0, 0), Square(0, 1), Piece(1, "P", "P"), None,
        ),
        (
            build_standard_shogi_ruleset,
            (
                (0, "K", "K", False, Square(0, 0)),
                (1, "K", "K", False, Square(8, 8)),
                (0, "R", "R", False, Square(4, 4)),
                (1, "P", "TP", True, Square(4, 5)),
            ),
            Square(4, 4), Square(4, 5), Piece(1, "P", "TP", promoted=True), "P",
        ),
        (
            build_xiangqi_diagnostic_ruleset,
            (
                (0, "G", "G", False, Square(4, 0)),
                (1, "G", "G", False, Square(4, 9)),
                (0, "S", "S", False, Square(4, 5)),  # blocks facing Generals
                (0, "R", "R", False, Square(0, 4)),
                (1, "S", "S", False, Square(0, 5)),
            ),
            Square(0, 4), Square(0, 5), Piece(1, "S", "S"), None,
        ),
    ),
    ids=("western-remove", "shogi-demote-to-hand", "xiangqi-remove"),
)
def test_capture_disposition_matches_public_core_and_semantic_executor(
    builder, pieces, source, target, victim, hand_piece
):
    ruleset = builder()
    compiled = compile_ruleset_for_execution(ruleset)
    engine = semantic_engine_for(compiled)
    assert engine is not None

    state = initial_state(compiled)
    board = [None] * len(state.position.board)
    for owner, base, current, promoted, square in pieces:
        index = square_to_index(square, state.position.board_shape)
        assert board[index] is None
        board[index] = Piece(owner, base, current, promoted=promoted)
    position = replace(state.position, board=tuple(board), side_to_move=0)
    start_key = repetition_identity_key(position, compiled)
    history = (HistoryRecord(start_key, -1, "", False),)
    state = replace(
        state,
        position=position,
        ply_count=0,
        repetition_counts=((start_key, 1),),
        terminal_status=engine.terminal_result(position, 0, ((start_key, 1),), history),
        history=history,
    )

    matches = [
        action
        for action in legal_actions(state, compiled)
        if action_is_board(action)
        and action_source_square(action) == source
        and action_target_square(action) == target
    ]
    assert len(matches) == 1, matches
    action = matches[0]

    semantic_binding = semantic_action_for(engine, state.position, action)
    semantic_after = engine.apply(state.position, semantic_binding)
    public_after = apply_action(state, action, compiled)
    public_position = public_after.position

    source_index = square_to_index(source, public_position.board_shape)
    target_index = square_to_index(target, public_position.board_shape)
    moving_piece = position.board[source_index]
    assert moving_piece is not None and moving_piece.owner == 0
    assert position.board[target_index] == victim
    assert public_position.board[source_index] is None
    assert public_position.board[target_index] == moving_piece
    assert victim not in public_position.board
    assert public_position.side_to_move == 1
    assert public_after.ply_count == 1

    if hand_piece is None:
        assert public_position.hands == position.hands
    else:
        assert public_position.hands[0].count(hand_piece) == 1
        assert public_position.hands[1].count(hand_piece) == 0
        assert all(hand.count(victim.current_type_id) == 0 for hand in public_position.hands)

    assert public_position == semantic_after
    assert repetition_identity_key(public_position, compiled) == repetition_identity_key(
        semantic_after, compiled
    )
    assert dict(public_after.repetition_counts)[
        repetition_identity_key(public_position, compiled)
    ] == 1
    assert public_after.history[-1].position_key == repetition_identity_key(
        semantic_after, compiled
    )
