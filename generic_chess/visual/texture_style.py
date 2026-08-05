"""Theme/style parameters for piece textures (decoupled from geometry)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PieceTextureStyle:
    """Visual parameters for texture rendering.

    Ratios are relative to the final texture size.  The white/black palettes
    cover the two owners; the neutral palette is used for geometry previews
    (``owner=None``).
    """

    occupancy_ratio: float = 0.8
    corner_radius_ratio: float = 0.18
    stroke_width_ratio: float = 0.05
    center_marker_ratio: float = 0.20
    white_fill: str = "#f5f5f5"
    white_stroke: str = "#1f1f1f"
    white_center_fill: str = "#1f1f1f"
    black_fill: str = "#1f1f1f"
    black_stroke: str = "#f0f0f0"
    black_center_fill: str = "#f0f0f0"
    neutral_fill: str = "#9a9a9a"
    neutral_stroke: str = "#1c1c1c"
    neutral_center_fill: str = "#1c1c1c"


def palette_for(style: PieceTextureStyle, owner: int | None) -> tuple[str, str, str]:
    """Return ``(fill, stroke, center_fill)`` for an owner."""
    if owner == 0:
        return (style.white_fill, style.white_stroke, style.white_center_fill)
    if owner == 1:
        return (style.black_fill, style.black_stroke, style.black_center_fill)
    return (style.neutral_fill, style.neutral_stroke, style.neutral_center_fill)
