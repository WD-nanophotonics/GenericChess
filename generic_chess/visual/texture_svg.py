"""Geometry model -> SVG rendering with normalization and styling."""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

from .texture_geometry import GeometryModel
from .texture_style import PieceTextureStyle, palette_for


BRANCH_WIDTH = 0.5
LEAP_BASE_LEN = 0.8
LEAP_EXTRA_PER_SPAN = 0.25
RAY_LEN = 1.9
ARROW_LEN = 0.45
ARROW_HALF_WIDTH = 0.3
KING_HALF = 1.05
PAWN_LEN = 1.15
PAWN_HALF_WIDTH = 0.55
CENTER_RADIUS = 0.42


def _unit(v: tuple[int, int]) -> tuple[float, float]:
    length = math.hypot(v[0], v[1])
    return (v[0] / length, v[1] / length)


def _render_unit(v: tuple[int, int]) -> tuple[float, float]:
    """Convert a movement vector to SVG space (y grows downward, so flip dr)."""
    length = math.hypot(v[0], v[1])
    return (v[0] / length, -v[1] / length)


def _branch_len(branch) -> float:
    if branch.kind == "ray":
        return RAY_LEN
    return LEAP_BASE_LEN + LEAP_EXTRA_PER_SPAN * (branch.span - 1)


def _geometry_bbox(model: GeometryModel):
    xs: list[float] = [0.0]
    ys: list[float] = [0.0]
    half = BRANCH_WIDTH / 2
    for b in model.branches:
        ux, uy = _render_unit(b.vector)
        end = _branch_len(b)
        xs.append(ux * end)
        ys.append(uy * end)
        if b.kind == "ray":
            tip = end + ARROW_LEN
            xs.append(ux * tip)
            ys.append(uy * tip)
    if model.kind == "king":
        xs += [-KING_HALF, KING_HALF]
        ys += [-KING_HALF, KING_HALF]
    if model.kind == "pawn":
        b = model.branches[0]
        ux, uy = _render_unit(b.vector)
        px, py = -uy, ux
        xs += [ux * PAWN_LEN, px * PAWN_HALF_WIDTH, -px * PAWN_HALF_WIDTH]
        ys += [uy * PAWN_LEN, py * PAWN_HALF_WIDTH, -py * PAWN_HALF_WIDTH]
    xs.append(CENTER_RADIUS)
    ys.append(CENTER_RADIUS)
    return (min(xs) - half, max(xs) + half, min(ys) - half, max(ys) + half)


def render_svg(
    model: GeometryModel,
    owner: int | None,
    size: int,
    style: PieceTextureStyle,
) -> str:
    """Render ``model`` to an SVG string of ``size`` x ``size`` pixels."""
    fill, stroke, center_fill = palette_for(style, owner)
    outline_w = max(1.0, size * style.stroke_width_ratio)

    # Normalization: fit the geometry bbox into the target area.
    gx0, gx1, gy0, gy1 = _geometry_bbox(model)
    scale0 = (size * style.occupancy_ratio) / max(gx1 - gx0, gy1 - gy0)
    pad = outline_w / scale0  # outline padding in unit space
    x0, x1 = gx0 - pad, gx1 + pad
    y0, y1 = gy0 - pad, gy1 + pad
    scale = (size * style.occupancy_ratio) / max(x1 - x0, y1 - y0)
    tx = size / 2 - (x0 + x1) / 2 * scale
    ty = size / 2 - (y0 + y1) / 2 * scale

    def X(x: float) -> float:
        return round(x * scale + tx, 2)

    def Y(y: float) -> float:
        return round(y * scale + ty, 2)

    body_w = round(BRANCH_WIDTH * scale, 2)
    parts: list[str] = []

    if model.kind == "generic":
        for b in model.branches:
            ux, uy = _render_unit(b.vector)
            end = _branch_len(b)
            cx, cy = X(0.0), Y(0.0)
            ex, ey = X(ux * end), Y(uy * end)
            cap = "round" if b.kind == "leap" else "butt"
            parts.append(
                f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" '
                f'stroke="{escape(stroke)}" stroke-width="{body_w + 2 * outline_w}" '
                f'stroke-linecap="{cap}"/>'
            )
            parts.append(
                f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" '
                f'stroke="{escape(fill)}" stroke-width="{body_w}" stroke-linecap="{cap}"/>'
            )
            if b.kind == "ray":
                tip = end + ARROW_LEN
                ax, ay = X(ux * tip), Y(uy * tip)
                px, py = -uy, ux
                b1x, b1y = X(ux * end + px * ARROW_HALF_WIDTH), Y(uy * end + py * ARROW_HALF_WIDTH)
                b2x, b2y = X(ux * end - px * ARROW_HALF_WIDTH), Y(uy * end - py * ARROW_HALF_WIDTH)
                parts.append(
                    f'<polygon points="{ax},{ay} {b1x},{b1y} {b2x},{b2y}" '
                    f'fill="{escape(fill)}" stroke="{escape(stroke)}" '
                    f'stroke-width="{outline_w}" stroke-linejoin="round"/>'
                )

    if model.kind == "king":
        x, y = X(-KING_HALF), Y(-KING_HALF)
        w = X(KING_HALF) - x
        h = Y(KING_HALF) - y
        rx = size * style.corner_radius_ratio
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="none" stroke="{escape(stroke)}" stroke-width="{body_w + 2 * outline_w}"/>'
        )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="none" stroke="{escape(fill)}" stroke-width="{body_w}"/>'
        )

    if model.kind == "pawn":
        b = model.branches[0]
        ux, uy = _render_unit(b.vector)
        px, py = -uy, ux
        ax, ay = X(ux * PAWN_LEN), Y(uy * PAWN_LEN)
        b1x, b1y = X(px * PAWN_HALF_WIDTH), Y(py * PAWN_HALF_WIDTH)
        b2x, b2y = X(-px * PAWN_HALF_WIDTH), Y(-py * PAWN_HALF_WIDTH)
        parts.append(
            f'<polygon points="{ax},{ay} {b1x},{b1y} {b2x},{b2y}" '
            f'fill="{escape(fill)}" stroke="{escape(stroke)}" '
            f'stroke-width="{outline_w}" stroke-linejoin="round"/>'
        )

    r = size * style.center_marker_ratio / 2
    cx, cy = X(0.0), Y(0.0)
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{escape(center_fill)}" stroke="{escape(stroke)}" stroke-width="{outline_w}"/>'
    )

    body = "\n".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">{body}</svg>'
    )
