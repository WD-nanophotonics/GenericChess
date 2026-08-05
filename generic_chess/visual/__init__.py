"""Procedural piece texture generation (SVG) driven by movement geometry.

This module is UI infrastructure: given a ``PieceType`` it derives a
deterministic, owner-aware SVG glyph from the piece's real movement atoms
(ray branches get arrowheads, leap branches get rounded caps, and the origin
is always marked).  It is intentionally neutral: geometry, style and SVG
serialization live in separate modules so future UIs can reuse them.
"""

from .textures import PieceTexture, generate_piece_texture
from .texture_style import PieceTextureStyle

__all__ = [
    "generate_piece_texture",
    "PieceTexture",
    "PieceTextureStyle",
]
