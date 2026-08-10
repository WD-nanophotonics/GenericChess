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
    # Product-shell tokens.  Widgets consume these through the application
    # stylesheet instead of inventing local colours and spacing rules.
    window_bg: str = "#111827"
    panel_bg: str = "#182334"
    panel_alt_bg: str = "#202f43"
    panel_border: str = "#334155"
    text_primary: str = "#e5edf6"
    text_secondary: str = "#a9b8c9"
    text_muted: str = "#7f91a6"
    accent: str = "#5aa9e6"
    accent_hover: str = "#76bff2"
    toolbar_bg: str = "#162131"
    radius: int = 6
    texture_style: PieceTextureStyle = field(default_factory=PieceTextureStyle)


def default_theme() -> Theme:
    return Theme()


def application_stylesheet(theme: Theme) -> str:
    """Return the shared product-shell stylesheet for the main window.

    Keeping these values in one place is deliberate: dynamic game labels and
    rules content must be allowed to change without each panel changing its
    own visual contract or size hints.
    """

    t = theme
    return f"""
    QMainWindow, QWidget#board_column {{
        background: {t.window_bg};
        color: {t.text_primary};
    }}
    QGraphicsView {{ background: {t.window_bg}; border: none; }}
    QToolBar {{
        background: {t.toolbar_bg};
        border: none;
        border-bottom: 1px solid {t.panel_border};
        spacing: 4px;
        padding: 5px 8px;
    }}
    QToolButton {{
        color: {t.text_primary};
        padding: 5px;
        border-radius: {t.radius}px;
    }}
    QToolButton:hover {{ background: {t.panel_alt_bg}; }}
    QStatusBar {{
        background: {t.toolbar_bg};
        color: {t.text_secondary};
        border-top: 1px solid {t.panel_border};
    }}
    QSplitter::handle {{ background: {t.panel_border}; }}
    QTabWidget::pane {{
        background: {t.panel_bg};
        border: 1px solid {t.panel_border};
        border-radius: {t.radius}px;
    }}
    QTabBar::tab {{
        background: {t.toolbar_bg};
        color: {t.text_secondary};
        padding: 8px 14px;
        border: 1px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {t.text_primary};
        background: {t.panel_bg};
        border-color: {t.panel_border};
        border-bottom-color: {t.panel_bg};
    }}
    QWidget#player_bar_0, QWidget#player_bar_1 {{
        background: {t.panel_bg};
        border: 1px solid {t.panel_border};
        border-radius: {t.radius}px;
    }}
    QLabel#player_name {{ color: {t.text_primary}; font-weight: 600; }}
    QLabel#player_marker {{ color: {t.accent}; }}
    QLabel#player_marker[state="thinking"] {{ color: {t.accent}; font-style: italic; }}
    QLabel#player_marker[state="active"] {{ color: {t.accent_hover}; font-weight: 600; }}
    QLabel#player_clock {{ color: {t.text_primary}; font-size: 14px; }}
    QLabel#player_hand_label, QLabel#player_hand_empty {{ color: {t.text_muted}; }}
    QLabel#moves_primary {{ color: {t.text_primary}; font-size: 15px; font-weight: 600; }}
    QLabel#moves_secondary {{ color: {t.text_secondary}; font-size: 12px; }}
    QListWidget {{
        background: {t.panel_bg};
        color: {t.text_primary};
        border: 1px solid {t.panel_border};
        border-radius: {t.radius}px;
        padding: 4px;
    }}
    QListWidget::item {{ padding: 6px 8px; border-radius: 4px; }}
    QListWidget::item:selected {{ background: {t.panel_alt_bg}; color: {t.text_primary}; }}
    QToolButton[selected="true"] {{
        border: 2px solid {t.accent};
        border-radius: 4px;
    }}
    QPushButton {{
        background: {t.panel_alt_bg};
        color: {t.text_primary};
        border: 1px solid {t.panel_border};
        border-radius: {t.radius}px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background: {t.accent}; border-color: {t.accent}; }}
    QScrollArea {{ background: {t.panel_bg}; }}
    """


def style_fingerprint(style: PieceTextureStyle) -> str:
    """Stable fingerprint of a texture style (used in the texture cache key)."""
    raw = canonical_json(asdict(style))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
