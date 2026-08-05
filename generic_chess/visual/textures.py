"""Public texture API: generate_piece_texture + deterministic fingerprints."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from ..core.pieces import PieceType
from ..rules.schema import canonical_json
from .texture_geometry import GeometryModel, build_geometry
from .texture_style import PieceTextureStyle
from .texture_svg import render_svg


@dataclass(frozen=True, slots=True)
class PieceTexture:
    """A generated texture: an SVG string plus its deterministic fingerprint."""

    svg: str
    width: int
    height: int
    fingerprint: str


def compute_texture_fingerprint(
    model: GeometryModel,
    owner: int | None,
    size: int,
    style: PieceTextureStyle,
) -> str:
    """SHA-256 of the canonical JSON of every input that defines the texture."""
    payload = {
        "geometry": {
            "kind": model.kind,
            "branches": [
                [b.vector[0], b.vector[1], b.kind, b.span] for b in model.branches
            ],
        },
        "owner": owner,
        "size": size,
        "style": asdict(style),
    }
    raw = canonical_json(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_piece_texture(
    piece_type: PieceType,
    *,
    owner: int | None = None,
    size: int = 128,
    style: PieceTextureStyle | None = None,
) -> PieceTexture:
    """Generate a deterministic SVG texture for ``piece_type``.

    ``owner`` selects the palette (0 = white, 1 = black, None = neutral) and,
    for owner 1, rotates the geometry 180 degrees so the icon matches the
    piece's on-board forward direction.  ``size`` is the square output size;
    ``style`` overrides the default rendering parameters.
    """
    if not isinstance(piece_type, PieceType):
        raise TypeError(f"piece_type must be a PieceType, got {piece_type!r}")
    if owner not in (0, 1, None):
        raise ValueError(f"owner must be 0, 1 or None, got {owner!r}")
    if not isinstance(size, int) or size < 1:
        raise ValueError(f"size must be a positive integer, got {size!r}")
    style = style if style is not None else PieceTextureStyle()
    model = build_geometry(piece_type, owner)
    svg = render_svg(model, owner, size, style)
    fingerprint = compute_texture_fingerprint(model, owner, size, style)
    return PieceTexture(svg=svg, width=size, height=size, fingerprint=fingerprint)
