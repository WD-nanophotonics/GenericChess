"""Learning Phase 1: material feature extractor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.learning.features import (
    linear_value,
    material_features,
    non_anchor_type_ids,
)

from native_test_helpers import make_state, simple_ruleset


def _compiled():
    n = 4
    king = PieceType("K", "K", (), is_anchor=True)
    a = PieceType("A", "A", (LeapAtom((0, 1)),))
    b = PieceType("B", "B", (LeapAtom((0, -1)),))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "A", "A", False)
    rows[1][1] = Piece(1, "B", "B", False)
    return simple_ruleset((king, a, b), rows, drop_types=("A", "B"))


def _position(compiled, pieces, hands=None, side=0):
    n = compiled.board_size
    board = [None] * (n * n)
    for base, owner, f, r in pieces:
        board[r * n + f] = Piece(owner, base, base, False)
    if hands is None:
        hands = (Hands.empty(), Hands.empty())
    return Position(
        tuple(board),
        hands,
        side,
        compiled.ruleset_fingerprint,
    )


def test_owner_perspective_sign_flips():
    compiled = _compiled()
    type_ids = non_anchor_type_ids(compiled)
    assert type_ids == ("A", "B")
    pos = _position(
        compiled,
        [("K", 0, 0, 0), ("K", 1, 3, 3), ("A", 0, 1, 0), ("A", 1, 2, 3)],
    )
    f0 = material_features(pos, type_ids, perspective=0)
    f1 = material_features(pos, type_ids, perspective=1)
    assert f1.board_counts == tuple(-v for v in f0.board_counts)
    assert f1.hand_counts == tuple(-v for v in f0.hand_counts)


def test_board_current_and_hand_base_counts():
    compiled = _compiled()
    type_ids = non_anchor_type_ids(compiled)
    pos = _position(
        compiled,
        [("K", 0, 0, 0), ("K", 1, 3, 3), ("A", 0, 1, 0), ("A", 1, 2, 3)],
        hands=(Hands((("B", 2),)), Hands((("A", 1),))),
    )
    f = material_features(pos, type_ids, perspective=0)
    # board: A: 1 self - 1 opp = 0; B: 0
    assert f.board_counts == (0, 0)
    # hand: A: 0 - 1 = -1; B: 2 - 0 = +2
    assert f.hand_counts == (-1, 2)


def test_anchor_excluded():
    compiled = _compiled()
    type_ids = non_anchor_type_ids(compiled)
    assert "K" not in type_ids
    pos = _position(
        compiled,
        [("K", 0, 0, 0), ("K", 1, 3, 3), ("A", 0, 1, 0)],
    )
    f = material_features(pos, type_ids, perspective=0)
    # Only A on the board: board counts (1, 0).
    assert f.board_counts == (1, 0)
    assert len(f.array()) == 2 * len(type_ids)


def test_linear_value_matches_hand_computation():
    compiled = _compiled()
    type_ids = non_anchor_type_ids(compiled)
    pos = _position(
        compiled,
        [("K", 0, 0, 0), ("K", 1, 3, 3), ("A", 0, 1, 0)],
    )
    f = material_features(pos, type_ids, perspective=0)
    board_w = {"A": 100.0, "B": 200.0}
    hand_w = {"A": 90.0, "B": 180.0}
    expected = 100.0 * 1 + 90.0 * 0
    assert linear_value(f, board_w, hand_w) == expected
