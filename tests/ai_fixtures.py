"""Shared hand-made rulesets for AI tests."""

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleSet

from conftest import king_type, make_ruleset, T


def _all_true_mask(n: int):
    return (True,) * (n * n)


def _drop_masks(n: int, type_ids):
    return {tid: (_all_true_mask(n), _all_true_mask(n)) for tid in type_ids}


def king(tid: str = "K") -> PieceType:
    return PieceType(
        tid,
        tid,
        tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)),
        is_anchor=True,
    )


def rook(tid: str = "R") -> PieceType:
    return PieceType(
        tid,
        tid,
        (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
    )


def build_4x4_rooks():
    n = 4
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][2] = Piece(0, "R", "R", False)
    rows[2][1] = Piece(1, "R", "R", False)
    ruleset = RuleSet(
        board_size=n,
        piece_types=(king(), rook()),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed=_drop_masks(n, ("R",)),
        promotion_allowed={},
        promotion_forced={},
    )
    return compile_ruleset(ruleset)


def build_mate(king_file: int):
    """8x8 mate ruleset: K at (king_file, 0); mate-in-1 when king_file=2."""
    n = 8
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(1, "K", "K", False)  # cornered black anchor
    rows[0][king_file] = Piece(0, "K", "K", False)
    rows[4][1] = Piece(0, "R", "R", False)
    rows[1][5] = Piece(0, "R", "R", False)
    ruleset = RuleSet(
        board_size=n,
        piece_types=(king(), rook()),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed=_drop_masks(n, ("R",)),
        promotion_allowed={},
        promotion_forced={},
    )
    return compile_ruleset(ruleset)


def build_promotion():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", RayAtom((1, 0)))
    ruleset = make_ruleset(
        8,
        [king_type(), pawn, gold],
        auto_promotion=True,
        lines=[
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
    return compile_ruleset(ruleset)
