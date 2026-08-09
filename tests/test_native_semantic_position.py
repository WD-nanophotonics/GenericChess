from __future__ import annotations

import pytest

from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import pack_position, position_key, snapshot
from generic_chess.core.keys import semantic_position_key
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.rules.compiler import compile_semantic_ruleset
from rule_semantics_ir_fixtures import castling_ruleset


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_semantic_position_roundtrip_preserves_aux_and_piece_identity():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    squares = semantic.support.board_size ** 2
    board = [None] * squares
    king = native_rules.type_ids.index("K")
    board[0] = [king, king, 0, 0]
    payload = {
        "side": 0,
        "ply": 7,
        "board": board,
        "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
        "aux_state": ((("king_right"), -1), 1),
    }
    # The public adapter accepts canonical (key, value) pairs.
    slot_id = semantic.ir.aux_slots[0].slot_id
    payload["aux_state"] = (((slot_id, 0), 1),)
    position = pack_position(native_rules, payload)
    observed = snapshot(native_rules, position)
    assert observed["side"] == 0
    assert observed["ply"] == 7
    assert observed["board"][0] == (king, king, 0, 0)
    assert ((slot_id, 0), 1) in observed["aux_state"]


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_position_key_matches_python_contract():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    squares = semantic.support.board_size ** 2
    king = native_rules.type_ids.index("K")
    board = [None] * squares
    board[0] = [king, king, 0, 0]
    slot_id = semantic.ir.aux_slots[0].slot_id
    payload = {
        "side": 1,
        "ply": 7,
        "board": board,
        "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
        "aux_state": (((slot_id, 0), 1),),
    }
    native_position = pack_position(native_rules, payload)
    python_board = [None] * squares
    python_board[0] = Piece(0, "K", "K", False)
    python_position = Position(
        tuple(python_board),
        (Hands.empty(), Hands.empty()),
        1,
        semantic.support.ruleset_fingerprint,
        (((slot_id, 0), 1),),
    )
    assert position_key(native_rules, native_position) == semantic_position_key(
        python_position, semantic.support, semantic.ir.aux_slots
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_history_roundtrip_and_repetition_count():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    squares = semantic.support.board_size ** 2
    payload = {
        "side": 0,
        "ply": 2,
        "board": [None] * squares,
        "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
        "history": ((1, 2), (3, 4), (1, 2)),
        "aux_state": (),
    }
    observed = snapshot(native_rules, pack_position(native_rules, payload))
    assert observed["history"] == ((1, 2), (3, 4), (1, 2))
    assert observed["history_occurrences"] == 2
