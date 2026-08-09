from __future__ import annotations

import pytest

from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    candidate_actions,
    guarded_actions,
    history_occurrences,
    make_checked,
    make_unmake_roundtrip,
    candidate_perft,
    pack_action,
    pack_position,
    position_key,
    probe_search,
    snapshot,
    unpack_action,
)
from generic_chess import _native_core
from generic_chess.core.keys import semantic_position_key
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
)
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
@pytest.mark.parametrize("unicode_ids", [("兵", "王"), ("é", "😀")])
def test_native_semantic_position_key_matches_python_for_unicode_type_ids(unicode_ids):
    actor_id, king_id = unicode_ids
    n = 3
    king = PieceType(
        king_id,
        king_id,
        tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)),
        is_anchor=True,
    )
    actor = PieceType(actor_id, actor_id, (LeapAtom((1, 0)),))
    action = RuleSemanticAction(
        name="unicode_move",
        type_ids=(actor_id,),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, king_id, king_id)
    rows[2][2] = Piece(1, king_id, king_id)
    ruleset = RuleSet(
        board_size=n,
        piece_types=(king, actor),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={actor_id: ((False,) * (n * n), (False,) * (n * n))},
        semantic_actions=(action,),
    )
    semantic = compile_semantic_ruleset(ruleset)
    board = list(rows[0] + rows[1] + rows[2])
    board[1] = Piece(0, actor_id, actor_id)
    python_position = Position(tuple(board), (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, 0] for piece in board],
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })
    assert position_key(native_rules, native_position) == semantic_position_key(
        python_position, semantic.support, semantic.ir.aux_slots
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_position_rejects_ruleset_mismatch_at_every_rules_bound_api():
    from rule_semantics_ir_fixtures import cannon_ruleset

    semantic_a = compile_semantic_ruleset(castling_ruleset())
    semantic_b = compile_semantic_ruleset(cannon_ruleset())
    rules_a = compile_native_semantic_rules(semantic_a)
    rules_b = compile_native_semantic_rules(semantic_b)
    ids = {type_id: index for index, type_id in enumerate(rules_a.type_ids)}
    board = [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, int(piece.promoted)] for row in semantic_a.support.initial_position for piece in row]
    position = pack_position(rules_a, {
        "side": 0,
        "ply": 0,
        "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })
    calls = (
        lambda: snapshot(rules_b, position),
        lambda: position_key(rules_b, position),
        lambda: candidate_actions(rules_b, position),
        lambda: guarded_actions(rules_b, position),
        lambda: make_checked(rules_b, position, 0),
        lambda: make_unmake_roundtrip(rules_b, position, 0),
        lambda: candidate_perft(rules_b, position, 1),
        lambda: probe_search(rules_b, position, 1),
    )
    for call in calls:
        with pytest.raises(ValueError, match="fingerprint"):
            call()


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
def test_native_semantic_full_history_words_are_preserved_for_runtime_children():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [None] * 64
    board[0] = [ids["K"], ids["K"], 0, 0]
    board[63] = [ids["K"], ids["K"], 1, 0]
    position = pack_position(native_rules, {"side": 0, "ply": 0, "board": board, "hands": [[0] * len(ids), [0] * len(ids)], "history": [], "aux_state": ()})
    action = min(guarded_actions(native_rules, position))
    child = snapshot(native_rules, make_checked(native_rules, position, action))
    assert child["history"]
    assert len(child["history"][0]) == 4


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_perft_stops_at_max_ply_terminal_state():
    from dataclasses import replace

    ruleset = replace(castling_ruleset(), max_ply=1)
    semantic = compile_semantic_ruleset(ruleset)
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, 0] for row in semantic.support.initial_position for piece in row]
    position = pack_position(native_rules, {"side": 0, "ply": 1, "board": board, "hands": [[0] * len(ids), [0] * len(ids)], "aux_state": ()})
    assert candidate_perft(native_rules, position, 2) == 1


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_probe_stops_on_exact_full_digest_repetition():
    semantic = compile_semantic_ruleset(castling_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, 0] for row in semantic.support.initial_position for piece in row]
    base = pack_position(native_rules, {"side": 0, "ply": 0, "board": board, "hands": [[0] * len(ids), [0] * len(ids)], "aux_state": ()})
    digest = position_key(native_rules, base)
    words = tuple(int(digest[i:i + 16], 16) for i in range(0, 64, 16))
    repeated = pack_position(native_rules, {"side": 0, "ply": 0, "board": board, "hands": [[0] * len(ids), [0] * len(ids)], "history": (words,) * 4, "aux_state": ()})
    result = probe_search(native_rules, repeated, 2)
    assert result["has_best"] == 0
    assert result["score"] == 0
    assert result["nodes"] == 1


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_probe_detects_checkmate_terminal_state():
    king = PieceType(
        "K",
        "K",
        tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)),
        is_anchor=True,
    )
    actor = PieceType("X", "X", (LeapAtom((1, 0)),))
    action = RuleSemanticAction(
        name="x_move",
        type_ids=("X",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    initial = ((Piece(0, "K", "K"), None, None), (None, Piece(0, "X", "X"), None), (None, None, Piece(1, "K", "K")))
    ruleset = RuleSet(
        board_size=3,
        piece_types=(king, actor),
        initial_position=initial,
        drop_allowed={"X": ((False,) * 9, (False,) * 9)},
        semantic_actions=(action,),
    )
    semantic = compile_semantic_ruleset(ruleset)
    python_position = Position(
        (Piece(0, "K", "K"), None, None, None, Piece(1, "K", "K"), None, None, None, None),
        (Hands.empty(), Hands.empty()),
        0,
        semantic.support.ruleset_fingerprint,
    )
    engine = SemanticEngine(semantic)
    assert not engine.legal_actions(python_position)
    assert engine.in_check(python_position, 0)
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, 0] for piece in python_position.board],
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })
    result = probe_search(native_rules, native_position, 2)
    assert result["has_best"] == 0
    assert result["score"] == -1000000
    assert result["nodes"] == 1


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_probe_detects_stalemate_terminal_state():
    king = PieceType("K", "K", (), is_anchor=True)
    actor = PieceType("X", "X", (LeapAtom((1, 0)),))
    initial = ((Piece(0, "K", "K"), None, None), (None, Piece(0, "X", "X"), None), (None, None, Piece(1, "K", "K")))
    action = RuleSemanticAction(
        name="x_move",
        type_ids=("X",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),),
    )
    ruleset = RuleSet(
        board_size=3,
        piece_types=(king, actor),
        initial_position=initial,
        drop_allowed={"X": ((False,) * 9, (False,) * 9)},
        semantic_actions=(action,),
    )
    semantic = compile_semantic_ruleset(ruleset)
    stalemate_board = ((Piece(0, "K", "K"), None, None), (None, None, None), (None, None, Piece(1, "K", "K")))
    python_position = Position(
        tuple(piece for row in stalemate_board for piece in row),
        (Hands.empty(), Hands.empty()),
        0,
        semantic.support.ruleset_fingerprint,
    )
    engine = SemanticEngine(semantic)
    assert not engine.legal_actions(python_position)
    assert not engine.in_check(python_position, 0)
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, 0] for piece in python_position.board],
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })
    result = probe_search(native_rules, native_position, 2)
    assert result["has_best"] == 0
    assert result["score"] == 0
    assert result["nodes"] == 1


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
    assert candidate_perft(native_rules, parent, 0) == 1
    assert candidate_perft(native_rules, parent, 1) == 3
    assert candidate_perft(native_rules, parent, 2) == 0

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
    assert [candidate_perft(native_rules, two_king_parent, depth) for depth in range(4)] == [1, 3, 9, 54]


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_castling_path_step_invariants_preserve_python_root_count():
    from rule_semantics_ir_fixtures import castling_ruleset

    ruleset = castling_ruleset()
    semantic = compile_semantic_ruleset(ruleset)
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = tuple(piece for row in ruleset.initial_position for piece in row)
    native_board = [
        None
        if piece is None
        else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, int(piece.promoted)]
        for piece in board
    ]
    parent = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": native_board,
            "hands": [[0] * len(ids), [0] * len(ids)],
            "aux_state": (),
        },
    )
    assert candidate_perft(native_rules, parent, 1) == 15


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_bounded_s4_uchifuzume_root_count_matches_python():
    from rule_semantics_ir_fixtures import uchifuzume_ruleset

    semantic = compile_semantic_ruleset(uchifuzume_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [None] * 64
    board[63] = [ids["K"], ids["K"], 0, 0]
    board[56] = [ids["K"], ids["K"], 1, 0]
    parent = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": board,
            "hands": [[0, 1], [0, 0]],
            "aux_state": (),
        },
    )
    assert candidate_perft(native_rules, parent, 1) == 65
    assert len(guarded_actions(native_rules, parent)) == 65


def _assert_exact_guarded_action_set(semantic, python_position):
    native_rules = compile_native_semantic_rules(semantic)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    geometry_ids = {geometry_id: index for index, geometry_id in enumerate(sorted(semantic.ir.geometry))}
    pattern_ids = {pattern.pattern_id: index for index, pattern in enumerate(semantic.ir.patterns)}
    native_board = [
        None
        if piece is None
        else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)]
        for piece in python_position.board
    ]
    native_hands = [[0] * len(type_ids), [0] * len(type_ids)]
    for owner, hand in enumerate(python_position.hands):
        for type_id, count in hand.counts:
            native_hands[owner][type_ids[type_id]] = count
    native_position = pack_position(
        native_rules,
        {
            "side": python_position.side_to_move,
            "ply": 0,
            "board": native_board,
            "hands": native_hands,
            "aux_state": python_position.aux_state,
        },
    )
    python_actions = set()
    for action in SemanticEngine(semantic).legal_actions(python_position):
        piece = python_position.board[action.source] if action.source is not None else None
        base_type = type_ids[piece.base_type_id] if piece is not None else type_ids[action.actor_type]
        python_actions.add(
            pack_action(
                {
                    "to": action.target,
                    "from": action.source if action.source is not None else 255,
                    "promotion": type_ids[action.promotion_target_id] if action.promotion_target_id else 255,
                    "base": base_type,
                    "kind": 2 if action.source is not None else 3,
                    "pattern": pattern_ids[action.pattern_id],
                    "geometry": geometry_ids[action.geometry_id],
                    "actor_current": type_ids[action.actor_type],
                }
            )
        )
    assert set(guarded_actions(native_rules, native_position)) == python_actions


def test_native_guarded_action_set_matches_python_across_core_fixtures():
    from rule_semantics_ir_fixtures import cannon_ruleset, nifu_ruleset

    castling = castling_ruleset()
    castling_semantic = compile_semantic_ruleset(castling)
    castling_board = tuple(piece for row in castling.initial_position for piece in row)
    _assert_exact_guarded_action_set(
        castling_semantic,
        Position(
            castling_board,
            (Hands.empty(), Hands.empty()),
            0,
            castling_semantic.support.ruleset_fingerprint,
        ),
    )

    cannon = cannon_ruleset()
    cannon_semantic = compile_semantic_ruleset(cannon)
    cannon_board = [None] * 64
    cannon_board[63] = Piece(0, "K", "K")
    cannon_board[0] = Piece(0, "C", "C")
    cannon_board[1] = Piece(1, "C", "C")
    cannon_board[2] = Piece(1, "C", "C")
    cannon_board[56] = Piece(1, "K", "K")
    _assert_exact_guarded_action_set(
        cannon_semantic,
        Position(
            tuple(cannon_board),
            (Hands.empty(), Hands.empty()),
            0,
            cannon_semantic.support.ruleset_fingerprint,
        ),
    )

    nifu = nifu_ruleset()
    nifu_semantic = compile_semantic_ruleset(nifu)
    nifu_board = [None] * 64
    nifu_board[63] = Piece(0, "K", "K")
    nifu_board[56] = Piece(1, "K", "K")
    _assert_exact_guarded_action_set(
        nifu_semantic,
        Position(
            tuple(nifu_board),
            (Hands((("P", 1),)), Hands.empty()),
            0,
            nifu_semantic.support.ruleset_fingerprint,
        ),
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_guarded_action_set_matches_python_for_inherited_promotion_variants():
    from rule_semantics_ir_fixtures import _king_type

    n = 5
    pawn = PieceType("P", "P", (LeapAtom((0, 1)),), is_promotable=True, promotion_target_ids=("G",))
    gold = PieceType("G", "G", (LeapAtom((1, 0)),))
    rows = []
    for rank in range(n):
        row = []
        for file in range(n):
            row.append(
                Piece(0, "K", "K") if (file, rank) == (0, 0)
                else Piece(1, "K", "K") if (file, rank) == (n - 1, n - 1)
                else None
            )
        rows.append(tuple(row))
    action = RuleSemanticAction(
        name="promotion_move",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),),
        promotion_mode="inherit_compiled_masks",
    )
    all_empty = (False,) * (n * n)
    source, target = Square(1, 1), Square(1, 2)
    source_index, target_index = source.rank * n + source.file, target.rank * n + target.file
    ruleset = RuleSet(
        board_size=n,
        piece_types=(_king_type(), pawn, gold),
        initial_position=tuple(rows),
        drop_allowed={"P": (all_empty, all_empty), "G": (all_empty, all_empty)},
        promotion_allowed={"P": (frozenset({(source, target)}), frozenset({(source, target)}))},
        promotion_forced={"P": (frozenset(), frozenset())},
        semantic_actions=(action,),
    )
    semantic = compile_semantic_ruleset(ruleset)
    board = list(rows[0] + rows[1] + rows[2] + rows[3] + rows[4])
    board[source_index] = Piece(0, "P", "P")
    python_position = Position(tuple(board), (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    _assert_exact_guarded_action_set(semantic, python_position)
    native_rules = compile_native_semantic_rules(semantic)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_board = [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, 0] for piece in board]
    native_position = pack_position(native_rules, {"side": 0, "ply": 0, "board": native_board, "hands": [[0] * len(type_ids), [0] * len(type_ids)], "aux_state": ()})
    assert any(unpack_action(value)["promotion"] == type_ids["G"] for value in guarded_actions(native_rules, native_position))


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_guarded_action_set_matches_python_for_path_between_state_guard():
    from rule_semantics_ir_fixtures import _king_type

    n = 5
    actor = PieceType("A", "A", (LeapAtom((1, 0)),))
    marker = PieceType("B", "B", (LeapAtom((1, 0)),))
    rows = []
    for rank in range(n):
        row = []
        for file in range(n):
            row.append(
                Piece(0, "K", "K") if (file, rank) == (0, 0)
                else Piece(1, "K", "K") if (file, rank) == (n - 1, n - 1)
                else None
            )
        rows.append(tuple(row))
    action = RuleSemanticAction(
        name="path_guarded_move",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        state_guards=(RuleStateGuard(
            aggregation="count",
            owner="any",
            type_ref=RuleTypeRef("explicit", "B"),
            compare_field="base",
            promoted="any",
            location="board",
            spatial=RuleSpatialSelector(
                kind="path_between",
                refs=(RuleSquareRef("fixed", square=(0, 0)), RuleSquareRef("fixed", square=(4, 4))),
            ),
            comparison="eq",
            value=1,
        ),),
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    ruleset = RuleSet(
        board_size=n,
        piece_types=(_king_type(), actor, marker),
        initial_position=tuple(rows),
        drop_allowed={"A": ((False,) * 25, (False,) * 25), "B": ((False,) * 25, (False,) * 25)},
        semantic_actions=(action,),
    )
    semantic = compile_semantic_ruleset(ruleset)
    board = list(rows[0] + rows[1] + rows[2] + rows[3] + rows[4])
    board[1] = Piece(0, "A", "A")
    board[12] = Piece(1, "B", "B")
    python_position = Position(tuple(board), (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    _assert_exact_guarded_action_set(semantic, python_position)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_python_deterministic_multiplay_action_and_child_differential():
    import random
    from rule_semantics_ir_fixtures import castling_ruleset

    semantic = compile_semantic_ruleset(castling_ruleset())
    engine = SemanticEngine(semantic)
    native_rules = compile_native_semantic_rules(semantic)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    geometry_ids = {geometry_id: index for index, geometry_id in enumerate(sorted(semantic.ir.geometry))}
    pattern_ids = {pattern.pattern_id: index for index, pattern in enumerate(semantic.ir.patterns)}

    python_board = [None] * 64
    python_board[0] = Piece(0, "K", "K")
    python_board[63] = Piece(1, "K", "K")
    python_position = Position(
        tuple(python_board),
        (Hands.empty(), Hands.empty()),
        0,
        semantic.support.ruleset_fingerprint,
    )
    native_board = [None] * 64
    native_board[0] = [type_ids["K"], type_ids["K"], 0, 0]
    native_board[63] = [type_ids["K"], type_ids["K"], 1, 0]
    native_position = pack_position(
        native_rules,
        {
            "side": 0,
            "ply": 0,
            "board": native_board,
            "hands": [[0] * len(type_ids), [0] * len(type_ids)],
            "aux_state": (),
        },
    )

    rng = random.Random(7)
    for _ in range(8):
        python_actions = engine.legal_actions(python_position)
        native_actions = guarded_actions(native_rules, native_position)
        packed_python = set()
        for action in python_actions:
            piece = python_position.board[action.source] if action.source is not None else None
            packed_python.add(
                pack_action(
                    {
                        "to": action.target,
                        "from": action.source if action.source is not None else 255,
                        "promotion": type_ids[action.promotion_target_id] if action.promotion_target_id else 255,
                        "base": type_ids[piece.base_type_id] if piece is not None else type_ids[action.actor_type],
                        "kind": 2 if action.source is not None else 3,
                        "pattern": pattern_ids[action.pattern_id],
                        "geometry": geometry_ids[action.geometry_id],
                        "actor_current": type_ids[action.actor_type],
                    }
                )
            )
        assert set(native_actions) == packed_python
        chosen_python = python_actions[rng.randrange(len(python_actions))]
        chosen_raw = next(
            raw
            for raw in native_actions
            if unpack_action(raw)["to"] == chosen_python.target
            and unpack_action(raw)["from"] == (chosen_python.source if chosen_python.source is not None else 255)
            and unpack_action(raw)["pattern"] == pattern_ids[chosen_python.pattern_id]
            and unpack_action(raw)["geometry"] == geometry_ids[chosen_python.geometry_id]
        )
        native_position = make_checked(native_rules, native_position, chosen_raw)
        python_position = engine.apply(python_position, chosen_python)
        native_snapshot = snapshot(native_rules, native_position)
        assert native_snapshot["side"] == python_position.side_to_move
        assert position_key(native_rules, native_position) == semantic_position_key(
            python_position, semantic.support, semantic.ir.aux_slots
        )
        for square, piece in enumerate(python_position.board):
            expected = None if piece is None else (
                type_ids[piece.base_type_id],
                type_ids[piece.current_type_id],
                piece.owner,
                int(piece.promoted),
            )
            assert native_snapshot["board"][square] == expected
