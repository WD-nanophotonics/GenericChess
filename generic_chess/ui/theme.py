"""Centralized UI theme (colors + texture style), decoupled from geometry."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..visual.texture_style import PieceTextureStyle


@dataclass(frozen=True)
class Theme:
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
    texture_style: PieceTextureStyle = field(default_factory=PieceTextureStyle)


def default_theme() -> Theme:
    return Theme()
