"""Centralized UI theme (colors + texture style), decoupled from geometry."""

from __future__ import annotations

from dataclasses import dataclass, field

import hashlib
from dataclasses import asdict

from ..rules.schema import canonical_json
from ..visual.texture_style import PieceTextureStyle


@dataclass(frozen=True)
class Theme:
    dark_mode: bool = True
    light_square: str = "#f0d9b5"
    dark_square: str = "#b58863"
    selected_border: str = "#2a9df4"
    legal_move_dot: str = "#3fa34d"
    capture_ring: str = "#ff6b35"
    preview_fill: str = "#7f8c9d"
    last_move_from: str = "#f6d365"
    last_move_to: str = "#f4a261"
    threat_border: str = "#e63946"
    hover_fill: str = "#ffffff"
    coordinate_text: str = "#6b5b4f"
    hover_opacity: float = 0.35
    preview_opacity: float = 0.45
    # Selection banner (rules explorer).
    selection_bg: str = "#245A82"
    selection_fg: str = "#FFFFFF"
    selection_secondary: str = "#DCEEFF"
    selection_accent: str = "#6EC1FF"
    # Movement diagram.
    diagram_grid: str = "#6b5b4f"
    diagram_ray: str = "#1a6fd1"
    diagram_leap: str = "#1e8a3c"
    diagram_arrow: str = "#1a6fd1"
    diagram_forward: str = "#3d5a6d"
    diagram_ray_alpha: float = 0.55
    # Game-over overlay.
    overlay_scrim_alpha: float = 0.35
    overlay_card_bg: str = "#1e293b"
    overlay_title: str = "#FFFFFF"
    overlay_text: str = "#cbd5e1"
    overlay_button_bg: str = "#245A82"
    overlay_button_fg: str = "#FFFFFF"
    # Toolbar glyphs.
    toolbar_icon: str = "#d8e3ee"
    texture_style: PieceTextureStyle = field(default_factory=PieceTextureStyle)


def default_theme() -> Theme:
    return Theme()


def style_fingerprint(style: PieceTextureStyle) -> str:
    """Stable fingerprint of a texture style (used in the texture cache key)."""
    raw = canonical_json(asdict(style))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
