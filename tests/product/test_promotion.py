"""Promotion: forced/optional zones, targets, dead targets, no re-promotion."""

import pytest

from generic_chess.core.actions import BoardMove
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.rules.validation import RuleValidationError

from conftest import king_type, make_compiled, make_position, sq, T


def _promo_compiled():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    lance = T("L", RayAtom((0, 1)), is_promotable=True, targets=("G",))
    knight = T("N", LeapAtom((1, 2)), LeapAtom((-1, 2)), is_promotable=True, targets=("G",))
    hybrid = T(
        "H",
        LeapAtom((1, 0)),
        LeapAtom((-1, 0)),
        LeapAtom((0, 1)),
        is_promotable=True,
        targets=("G",),
    )
    gold = T("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1)))
    return make_compiled(8, [king_type(), pawn, lance, knight, hybrid, gold], auto_promotion=True)


def _actions(compiled, lines, **kw):
    return legal_actions_from_position(make_position(compiled, lines, **kw), compiled)


def _from(actions, from_sq):
    if isinstance(from_sq, tuple):
        from_sq = sq(*from_sq)
    return [a for a in actions if isinstance(a, BoardMove) and a.from_square == from_sq]


def test_pawn_like_last_rank_forced_promotion():
    compiled = _promo_compiled()
    actions = _actions(
        compiled,
        [
            ".......k",  # rank 7
            "....P...",  # rank 6
            "........",  # rank 5
            "........",  # rank 4
            "........",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "K.......",  # rank 0
        ],
    )
    moves = _from(actions, (4, 6))
    promoted = [a for a in moves if a.promotion_target_id is not None]
    plain = [a for a in moves if a.promotion_target_id is None]
    assert any(a.to_square == sq(4, 7) for a in promoted)
    assert plain == []


def test_lance_like_last_rank_forced_promotion():
    compiled = _promo_compiled()
    actions = _actions(
        compiled,
        [
            ".......k",
            "....L...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    moves = _from(actions, (4, 6))
    promoted = [a for a in moves if a.promotion_target_id is not None]
    plain = [a for a in moves if a.promotion_target_id is None]
    assert any(a.to_square == sq(4, 7) for a in promoted)
    assert plain == []


def test_knight_like_last_two_ranks_forced_promotion():
    compiled = _promo_compiled()
    # Knight at rank 4; moves to rank 6 are in the forced zone.
    actions = _actions(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "....N...",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    moves = _from(actions, (4, 4))
    to_rank6 = [a for a in moves if a.to_square.rank == 6]
    assert to_rank6 and all(a.promotion_target_id is not None for a in to_rank6)

    # Knight at rank 0; moves to rank 2 are plain (outside the zone).
    actions2 = _actions(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K...N...",
        ],
    )
    moves2 = _from(actions2, (4, 0))
    to_rank2 = [a for a in moves2 if a.to_square.rank == 2]
    assert to_rank2 and all(a.promotion_target_id is None for a in to_rank2)


def test_optional_promotion_for_hybrid_forward_piece():
    compiled = _promo_compiled()
    actions = _actions(
        compiled,
        [
            ".......k",
            "....H...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    moves = _from(actions, (4, 6))
    to7 = [a for a in moves if a.to_square == sq(4, 7)]
    assert len([a for a in to7 if a.promotion_target_id is None]) == 1
    assert len([a for a in to7 if a.promotion_target_id is not None]) == 1


def test_already_promoted_piece_cannot_promote_again():
    compiled = _promo_compiled()
    actions = _actions(
        compiled,
        [
            ".......k",
            "....G...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
        promoted={(4, 6): "P"},
    )
    moves = _from(actions, (4, 6))
    assert all(a.promotion_target_id is None for a in moves)


def test_promotion_target_cannot_be_anchor():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("K",))
    with pytest.raises(RuleValidationError) as exc:
        make_compiled(8, [king_type(), pawn], auto_promotion=True)
    assert any(i.code == "PROMOTION_TARGET_IS_ANCHOR" for i in exc.value.issues)


def test_anchor_cannot_be_promotable():
    bad_king = T("K", LeapAtom((1, 0)), is_anchor=True, is_promotable=True)
    with pytest.raises(RuleValidationError) as exc:
        make_compiled(8, [bad_king])
    assert any(i.code == "ANCHOR_IS_PROMOTABLE" for i in exc.value.issues)


def test_dead_promotion_target_removes_forced_move():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    dead = T("G")  # no atoms: structurally dead everywhere
    compiled = make_compiled(8, [king_type(), pawn, dead], auto_promotion=True)
    actions = _actions(
        compiled,
        [
            ".......k",
            "....P...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    moves = _from(actions, (4, 6))
    assert [a for a in moves if a.to_square == sq(4, 7)] == []


def test_dead_promotion_target_optional_keeps_plain_move():
    hybrid = T(
        "H",
        LeapAtom((1, 0)),
        LeapAtom((-1, 0)),
        LeapAtom((0, 1)),
        is_promotable=True,
        targets=("G",),
    )
    dead = T("G")
    compiled = make_compiled(8, [king_type(), hybrid, dead], auto_promotion=True)
    actions = _actions(
        compiled,
        [
            ".......k",
            "....H...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    moves = _from(actions, (4, 6))
    to7 = [a for a in moves if a.to_square == sq(4, 7)]
    assert len([a for a in to7 if a.promotion_target_id is None]) == 1
    assert [a for a in to7 if a.promotion_target_id is not None] == []
