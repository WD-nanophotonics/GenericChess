"""Phase 2A: public checked actions must reject malformed packed integers
safely without mutating the position."""

import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.native.adapter import (
    native_legal_actions,
    native_make_checked,
    native_snapshot,
    pack_native_position,
    to_python_action,
)
from generic_chess.native.compiler import (
    NativeActionError,
    compile_native_rules,
)
from generic_chess.session.session import GameSession

from native_test_helpers import requires_native, simple_ruleset


def _ruleset():
    n = 4
    king = PieceType("K", "K", (), is_anchor=True)
    p = PieceType("P", "P", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    q = PieceType("Q", "Q", (LeapAtom((1, 0)),))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "P", "P", False)
    rows[2][3] = Piece(1, "P", "P", False)
    return simple_ruleset((king, p, q), rows, drop_types=("P", "Q"))


@requires_native
def _fixture():
    compiled = _ruleset()
    rules = compile_native_rules(compiled)
    session = GameSession(compiled)
    pos = pack_native_position(compiled, rules, session.state)
    return compiled, rules, session, pos


@requires_native
def test_malformed_actions_rejected_safely():
    compiled, rules, session, pos = _fixture()
    before = native_snapshot(rules, pos)
    n = compiled.board_size
    legal = native_legal_actions(rules, pos)
    assert legal
    real = legal[0]
    real_action = to_python_action(rules, real)
    base = rules.type_map[
        session.state.position.board[
            real_action.from_square.rank * n + real_action.from_square.file
        ].base_type_id
    ]
    to_idx = real_action.to_square.rank * n + real_action.to_square.file
    from_idx = real_action.from_square.rank * n + real_action.from_square.file
    promo = (
        rules.type_map[real_action.promotion_target_id]
        if real_action.promotion_target_id is not None
        else 0xFF
    )

    cases = {
        "invalid_kind": (2 << 32),
        "to_out_of_range": 255,
        "base_out_of_range": (255 << 24),
        "promo_out_of_range": (254 << 16) | (0 << 8) | 0,
        "board_from_sentinel": (0 << 24) | (0xFF << 8) | 0,
        "drop_from_not_sentinel": (1 << 32) | (0 << 24) | (0 << 8) | 0,
        "reserved_bits": (1 << 36) | real,
        "drop_no_hand": (1 << 32) | (base << 24) | (0xFF << 8) | 1,
    }
    for name, action in cases.items():
        with pytest.raises(NativeActionError) as exc:
            native_make_checked(rules, pos, action)
        fields = exc.value.fields
        assert "status" in fields and "packed" in fields
        assert fields["fingerprint"] == compiled.ruleset_fingerprint
        # The original position capsule is never mutated.
        after = native_snapshot(rules, pos)
        assert after == before


@requires_native
def test_forged_non_legal_action_rejected():
    compiled, rules, session, pos = _fixture()
    before = native_snapshot(rules, pos)
    legal = [to_python_action(rules, a) for a in native_legal_actions(rules, pos)]
    # Take a real move and change its base type to a different existing type.
    from generic_chess.core.actions import DropMove
    from generic_chess.native.adapter import pack_action

    non_anchor_ids = [
        pt.type_id for pt in compiled.piece_types if not pt.is_anchor
    ]
    move = legal[0]
    if isinstance(move, DropMove):
        other_base = next(t for t in non_anchor_ids if t != move.base_type_id)
        forged = pack_action(rules, move, base_type_id=other_base)
    else:
        piece = session.state.position.board[
            move.from_square.rank * compiled.board_size + move.from_square.file
        ]
        other_base = next(t for t in non_anchor_ids if t != piece.base_type_id)
        forged = pack_action(rules, move, base_type_id=piece.base_type_id)
        forged &= ~(0xFF << 24)
        forged |= (rules.type_map[other_base] & 0xFF) << 24
    with pytest.raises(NativeActionError) as exc:
        native_make_checked(rules, pos, forged)
    assert exc.value.reason in ("not_legal", "base_mismatch")
    assert native_snapshot(rules, pos) == before


@requires_native
def test_valid_action_still_works_through_checked_path():
    compiled, rules, session, pos = _fixture()
    action = native_legal_actions(rules, pos)[0]
    child = native_make_checked(rules, pos, action)
    assert child["side_to_move"] == 1 - session.state.position.side_to_move
    assert child["ply"] == session.state.ply_count + 1
