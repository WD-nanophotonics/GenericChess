"""Piece texture generation: stability, ownership, structure, categories."""

import re

import pytest

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import PieceType
from generic_chess.visual import PieceTextureStyle, generate_piece_texture


def pt(tid: str, *atoms, **kw) -> PieceType:
    return PieceType(tid, tid, tuple(atoms), **kw)


KING = pt("K", *(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)))
ROOK_RAY = pt("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
FALSE_ROOK = pt("F", LeapAtom((0, 1)), LeapAtom((0, -1)), LeapAtom((1, 0)), LeapAtom((-1, 0)))
BISHOP_RAY = pt("B", RayAtom((1, 1)), RayAtom((1, -1)), RayAtom((-1, 1)), RayAtom((-1, -1)))
QUEEN = pt("Q", *(RayAtom(v) for v in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))))
PAWN = pt("P", LeapAtom((0, 1)))


def test_stability_same_inputs_same_output():
    a = generate_piece_texture(ROOK_RAY, owner=0, size=96)
    b = generate_piece_texture(ROOK_RAY, owner=0, size=96)
    assert a.svg == b.svg
    assert a.fingerprint == b.fingerprint
    assert a.width == b.width == 96


def test_owner_palette_differs():
    w = generate_piece_texture(ROOK_RAY, owner=0, size=96)
    b = generate_piece_texture(ROOK_RAY, owner=1, size=96)
    assert w.svg != b.svg
    assert w.fingerprint != b.fingerprint
    assert "#f5f5f5" in w.svg  # white fill
    assert "#1f1f1f" in b.svg  # black fill


def test_pawn_orientation_mirrors_for_owner1():
    size = 96
    apex = lambda tex: float(re.search(r'<polygon points="[\d.]+,([\d.]+)', tex.svg).group(1))
    w = generate_piece_texture(PAWN, owner=0, size=size)
    b = generate_piece_texture(PAWN, owner=1, size=size)
    assert apex(w) < size / 2  # player 0 wedge points up
    assert apex(b) > size / 2  # player 1 wedge points down (mirrored)


def test_svg_structure():
    tex = generate_piece_texture(ROOK_RAY, owner=0, size=128)
    assert tex.svg.startswith("<svg")
    assert 'width="128"' in tex.svg
    assert 'height="128"' in tex.svg
    assert 'viewBox="0 0 128 128"' in tex.svg
    assert "<circle" in tex.svg  # center marker
    assert "stroke=" in tex.svg
    assert "stroke-width=" in tex.svg


def test_ray_has_arrowheads_leap_does_not():
    rook = generate_piece_texture(ROOK_RAY, owner=0)
    false_rook = generate_piece_texture(FALSE_ROOK, owner=0)
    assert rook.svg.count("<polygon") == 4
    assert false_rook.svg.count("<polygon") == 0
    assert rook.svg != false_rook.svg


def test_category_distinctions():
    rook = generate_piece_texture(ROOK_RAY, owner=0).svg
    bishop = generate_piece_texture(BISHOP_RAY, owner=0).svg
    king = generate_piece_texture(KING, owner=0).svg
    queen = generate_piece_texture(QUEEN, owner=0).svg
    assert rook != bishop
    assert rook != king
    assert king != queen
    assert "<rect" in king  # king is a rounded square ring
    assert "<rect" not in rook
    assert queen.count("<polygon") == 8  # eight ray arrowheads


def test_oblique_and_mixed_pieces_render_generic():
    knight = pt("N", LeapAtom((1, 2)), LeapAtom((-1, 2)))
    mixed = pt("M", RayAtom((1, 0)), LeapAtom((1, 1)))
    k = generate_piece_texture(knight, owner=0)
    m = generate_piece_texture(mixed, owner=0)
    assert k.svg.count("<polygon") == 0  # leaps: rounded caps only
    assert m.svg.count("<polygon") == 1  # one ray arrow
    assert k.svg != m.svg


def test_size_parameter():
    small = generate_piece_texture(QUEEN, owner=0, size=16)
    large = generate_piece_texture(QUEEN, owner=0, size=256)
    assert 'width="16"' in small.svg
    assert 'width="256"' in large.svg
    assert small.svg != large.svg


def test_style_override():
    custom = PieceTextureStyle(white_fill="#ff0000", white_stroke="#00ff00")
    tex = generate_piece_texture(ROOK_RAY, owner=0, size=96, style=custom)
    assert "#ff0000" in tex.svg
    assert "#00ff00" in tex.svg
    default = generate_piece_texture(ROOK_RAY, owner=0, size=96)
    assert tex.fingerprint != default.fingerprint


def test_empty_atoms_render_center_only():
    empty = pt("Z")
    tex = generate_piece_texture(empty, owner=0, size=64)
    assert "<circle" in tex.svg
    assert "<line" not in tex.svg
    assert "<polygon" not in tex.svg


def test_invalid_arguments_rejected():
    with pytest.raises(TypeError):
        generate_piece_texture("not-a-piece-type")
    with pytest.raises(ValueError):
        generate_piece_texture(PAWN, owner=5)
    with pytest.raises(ValueError):
        generate_piece_texture(PAWN, size=0)


def test_fingerprint_distinguishes_inputs():
    base = generate_piece_texture(ROOK_RAY, owner=0, size=96).fingerprint
    assert generate_piece_texture(ROOK_RAY, owner=1, size=96).fingerprint != base
    assert generate_piece_texture(ROOK_RAY, owner=0, size=128).fingerprint != base
    assert generate_piece_texture(BISHOP_RAY, owner=0, size=96).fingerprint != base
