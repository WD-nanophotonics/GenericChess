"""Board rendering: ownership prefixes, promotion markers, alignment."""

import re

from generic_chess.cli.render import render_board
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position


def _position(cells: list[Piece | None]) -> Position:
    return Position(
        board=tuple(cells),
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint="fp",
    )


def test_render_shows_owner_prefix():
    board = [None] * 16
    board[0] = Piece(0, "P", "P", False)
    board[1] = Piece(1, "P", "P", False)
    text = render_board(_position(board), 4)
    assert "0:P" in text
    assert "1:P" in text


def test_render_shows_promoted_marker():
    board = [None] * 16
    board[0] = Piece(0, "P", "G", True)
    board[1] = Piece(1, "P", "G", True)
    text = render_board(_position(board), 4)
    assert "0:+G" in text
    assert "1:+G" in text


def test_render_empty_squares_are_dots():
    board = [None] * 16
    board[0] = Piece(0, "P", "P", False)
    text = render_board(_position(board), 4)
    assert text.count(".") >= 15  # every other square renders as '.'


def test_render_multi_char_type_alignment():
    board = [None] * 16
    board[0] = Piece(0, "LONGTYPE", "LONGTYPE", False)
    board[1] = Piece(1, "P", "P", True)
    text = render_board(_position(board), 4)
    assert "0:LONGTYPE" in text
    rank_lines = [line for line in text.splitlines() if re.match(r"^\s*\d+ ", line)]
    assert len(rank_lines) == 4
    widths = {len(line) for line in rank_lines}
    assert len(widths) == 1  # all rank rows align to the same width
