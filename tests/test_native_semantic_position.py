from __future__ import annotations

import pytest

from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    candidate_actions,
    history_occurrences,
    make_checked,
    make_unmake_roundtrip,
    perft,
    pack_position,
    position_key,
    snapshot,
    unpack_action,
)
from generic_chess import _native_core
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
    position = pack_position(native_rules, payload)
    assert history_occurrences(position, 1, 2) == 2
    assert history_occurrences(position, 9, 9) == 0


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_sha256_known_answers():
    assert _native_core.sha256_hex(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert _native_core.sha256_hex(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_action_identity_roundtrip_and_reserved_bits():
    fields = {
        "to": 7,
        "from": 2,
        "promotion": 255,
        "base": 3,
        "kind": 2,
        "pattern": 12,
        "geometry": 1023,
        "actor_current": 5,
    }
    packed = _native_core.semantic_action_pack(fields)
    assert _native_core.semantic_action_unpack(packed) == fields
    assert _native_core.semantic_action_pack({**fields, "pattern": 13}) != packed
    with pytest.raises(ValueError):
        _native_core.semantic_action_unpack((packed & ~(0xF << 32)) | (1 << 32))
    with pytest.raises(ValueError):
        _native_core.semantic_action_pack({**fields, "kind": 0})


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_position_rejects_forged_base_current_identity():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    king = native_rules.type_ids.index("K")
    forged = {
        "side": 0,
        "ply": 0,
        "board": [[king, (king + 1) % len(native_rules.type_ids), 0, 0]]
        + [None] * (semantic.support.board_size ** 2 - 1),
        "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
        "aux_state": (),
    }
    with pytest.raises(ValueError):
        pack_position(native_rules, forged)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_candidate_actions_preserve_exact_identity_fields():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    king = native_rules.type_ids.index("K")
    payload = {
        "side": 0,
        "ply": 0,
        "board": [[king, king, 0, 0]] + [None] * (semantic.support.board_size ** 2 - 1),
        "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
        "aux_state": (),
    }
    actions = candidate_actions(native_rules, pack_position(native_rules, payload))
    assert actions
    decoded = [unpack_action(action) for action in actions]
    assert all(item["kind"] == 2 for item in decoded)
    assert all(item["from"] == 0 and item["base"] == king for item in decoded)
    assert len({(item["pattern"], item["geometry"]) for item in decoded}) >= 1


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_checked_make_matches_python_simple_semantic_child():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    king = native_rules.type_ids.index("K")
    payload = {
        "side": 0,
        "ply": 0,
        "board": [[king, king, 0, 0]] + [None] * (semantic.support.board_size ** 2 - 1),
        "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
        "aux_state": (),
    }
    native_parent = pack_position(native_rules, payload)
    native_actions = candidate_actions(native_rules, native_parent)
    action = next(action for action in native_actions if unpack_action(action)["to"] == 8)
    native_child = snapshot(native_rules, make_checked(native_rules, native_parent, action))

    from generic_chess.core.position import Hands, Position
    from generic_chess.core.pieces import Piece
    from generic_chess.core.semantic_executor import SemanticEngine

    python_board = [None] * (semantic.support.board_size ** 2)
    python_board[0] = Piece(0, "K", "K", False)
    python_parent = Position(
        tuple(python_board),
        (Hands.empty(), Hands.empty()),
        0,
        semantic.support.ruleset_fingerprint,
    )
    python_child = SemanticEngine(semantic).apply(
        python_parent,
        next(a for a in SemanticEngine(semantic).legal_actions(python_parent) if a.target == 8),
    )
    assert native_child["side"] == python_child.side_to_move
    assert native_child["ply"] == 1
    assert native_child["board"][8] == (king, king, 0, 0)
    assert position_key(native_rules, make_checked(native_rules, native_parent, action)) == semantic_position_key(
        python_child, semantic.support, semantic.ir.aux_slots
    )
    assert make_unmake_roundtrip(native_rules, native_parent, action) == {
        "make_ok": 1,
        "unmake_ok": 1,
        "restored": 1,
    }


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_checked_make_capture_to_hand_matches_python():
    from generic_chess.core.position import Hands, Position
    from generic_chess.core.pieces import Piece
    from generic_chess.core.semantic_executor import SemanticEngine
    from rule_semantics_ir_fixtures import cannon_ruleset

    semantic = compile_semantic_ruleset(cannon_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_board = [None] * 64
    native_board[63] = [ids["K"], ids["K"], 0, 0]
    native_board[0] = [ids["C"], ids["C"], 0, 0]
    native_board[1] = [ids["C"], ids["C"], 1, 0]
    native_board[2] = [ids["C"], ids["C"], 1, 0]
    native_board[56] = [ids["K"], ids["K"], 1, 0]
    native_parent = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": native_board,
            "hands": [[0] * len(ids), [0] * len(ids)],
            "aux_state": (),
        },
    )
    native_action = next(
        action for action in candidate_actions(native_rules, native_parent)
        if unpack_action(action)["to"] == 2
    )
    native_child_capsule = make_checked(native_rules, native_parent, native_action)
    native_child = snapshot(native_rules, native_child_capsule)

    python_board = [None] * 64
    python_board[63] = Piece(0, "K", "K")
    python_board[0] = Piece(0, "C", "C")
    python_board[1] = Piece(1, "C", "C")
    python_board[2] = Piece(1, "C", "C")
    python_board[56] = Piece(1, "K", "K")
    python_parent = Position(
        tuple(python_board),
        (Hands.empty(), Hands.empty()),
        0,
        semantic.support.ruleset_fingerprint,
    )
    engine = SemanticEngine(semantic)
    python_child = engine.apply(
        python_parent,
        next(action for action in engine.legal_actions(python_parent) if action.target == 2),
    )
    assert native_child["board"][1] == (ids["C"], ids["C"], 1, 0)
    assert native_child["board"][2] == (ids["C"], ids["C"], 0, 0)
    assert native_child["hands"][0][ids["C"]] == 1
    assert native_child["side"] == python_child.side_to_move == 1
    assert position_key(native_rules, native_child_capsule) == semantic_position_key(
        python_child, semantic.support, semantic.ir.aux_slots
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_checked_make_drop_matches_python():
    from generic_chess.core.position import Hands, Position
    from generic_chess.core.pieces import Piece
    from generic_chess.core.semantic_executor import SemanticEngine
    from rule_semantics_ir_fixtures import nifu_ruleset

    semantic = compile_semantic_ruleset(nifu_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_board = [None] * 64
    native_board[63] = [ids["K"], ids["K"], 0, 0]
    native_board[56] = [ids["K"], ids["K"], 1, 0]
    native_parent = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": native_board,
            "hands": [[0, 1], [0, 0]],
            "aux_state": (),
        },
    )
    native_action = next(
        action for action in candidate_actions(native_rules, native_parent)
        if unpack_action(action)["kind"] == 3 and unpack_action(action)["to"] == 0
    )
    native_child_capsule = make_checked(native_rules, native_parent, native_action)
    native_child = snapshot(native_rules, native_child_capsule)

    python_board = [None] * 64
    python_board[63] = Piece(0, "K", "K")
    python_board[56] = Piece(1, "K", "K")
    python_parent = Position(
        tuple(python_board),
        (Hands((("P", 1),)), Hands.empty()),
        0,
        semantic.support.ruleset_fingerprint,
    )
    engine = SemanticEngine(semantic)
    python_child = engine.apply(
        python_parent,
        next(action for action in engine.legal_actions(python_parent) if action.target == 0),
    )
    assert native_child["board"][0] == (ids["P"], ids["P"], 0, 0)
    assert native_child["hands"][0][ids["P"]] == 0
    assert native_child["side"] == python_child.side_to_move == 1
    assert position_key(native_rules, native_child_capsule) == semantic_position_key(
        python_child, semantic.support, semantic.ir.aux_slots
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_perft_recurses_over_checked_children():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    king = native_rules.type_ids.index("K")
    parent = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": [[king, king, 0, 0]] + [None] * (semantic.support.board_size ** 2 - 1),
            "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
            "aux_state": (),
        },
    )
    assert perft(native_rules, parent, 0) == 1
    assert perft(native_rules, parent, 1) == 3
    assert perft(native_rules, parent, 2) == 0

    two_kings = [None] * (semantic.support.board_size ** 2)
    two_kings[0] = [king, king, 0, 0]
    two_kings[-1] = [king, king, 1, 0]
    two_king_parent = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": two_kings,
            "hands": [[0] * len(native_rules.type_ids), [0] * len(native_rules.type_ids)],
            "aux_state": (),
        },
    )
    assert [perft(native_rules, two_king_parent, depth) for depth in range(4)] == [1, 3, 9, 54]
