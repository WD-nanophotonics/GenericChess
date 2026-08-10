"""Desktop UI redesign acceptance: board stability, architecture, replay,
inspect, localization and PlayerBar behavior."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QScrollArea

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.schema import RuleSet
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.panels.movement_diagram import (
    compute_diagram_layout,
    diagram_cell,
    diagram_screen_direction,
)
from generic_chess.ui.settings import (
    KEY_LANGUAGE,
    KEY_SHOW_DEV_STATUS,
    KEY_ZOOM_MODE,
)
from generic_chess.ui.stores import DictSettingsStore
from generic_chess.ui.theme import Theme


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _qt_cleanup(qapp):
    """Keep GUI object graphs isolated between redesign tests.

    The lifecycle suite intentionally asserts that no windows survive a test.
    Without the same bounded shutdown contract here, this module leaves its
    top-level windows alive until the next module happens to collect them.
    """
    import gc

    baseline = set(qapp.topLevelWidgets())
    yield
    for widget in list(qapp.topLevelWidgets()):
        if widget in baseline:
            continue
        if isinstance(widget, MainWindow):
            widget._shutdown()
        try:
            widget.close()
            widget.deleteLater()
        except RuntimeError:
            pass
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()
    gc.collect()


def _window(qapp, seed=42, board_size=8, language="en"):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    ctrl = UIController(settings=settings)
    assert ctrl.new_game(seed=seed, board_size=board_size)
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


def _first_pawn_square(ctrl):
    model = ctrl.board_view_model()
    return next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )


def _mate_setup(qapp):
    from test_ai_match import _mate_ruleset

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(_mate_ruleset())
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


def _window_with_ruleset(qapp, ruleset, language="en"):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(ruleset)
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


def _stalemate_ruleset():
    """One white king move reaches a stalemate for black.

    Black king a8; white rook b2 covers b7/b8, bishop c5 covers a7 through
    the empty b6.  White plays Kc6-d6, leaving every escape square covered
    without giving check.
    """
    n = 8
    king = PieceType(
        "K",
        "K",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ),
        is_anchor=True,
    )
    rook = PieceType(
        "R",
        "R",
        (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
    )
    bishop = PieceType(
        "B",
        "B",
        tuple(RayAtom((df, dr)) for df in (-1, 1) for dr in (-1, 1)),
    )
    rows = [[None] * n for _ in range(n)]
    rows[5][2] = Piece(0, "K", "K", False)  # white king c6
    rows[1][1] = Piece(0, "R", "R", False)  # white rook b2
    rows[4][2] = Piece(0, "B", "B", False)  # white bishop c5
    rows[7][0] = Piece(1, "K", "K", False)  # black king a8
    mask = (False,) * (n * n)
    return RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=(king, rook, bishop),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={"R": (mask, mask), "B": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )


def _max_ply_ruleset():
    """Every first move immediately triggers the ply limit."""
    n = 8
    king = PieceType(
        "K",
        "K",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ),
        is_anchor=True,
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][4] = Piece(0, "K", "K", False)
    rows[7][4] = Piece(1, "K", "K", False)
    mask = (False,) * (n * n)
    return RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=(king,),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=1,
        stalemate_result="draw",
    )


def _first_white_piece_square(ctrl):
    return next(
        sv.square
        for sv in ctrl.board_view_model().squares
        if sv.piece is not None and sv.piece.owner == 0
    )


# --------------------------------------------------------------- board stability

def test_board_transform_stable_across_refresh_and_moves(qapp):
    ctrl, win = _window(qapp)
    win._refresh()
    before = win._board_view.transform()
    win._refresh()
    assert win._board_view.transform() == before

    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    win._refresh()
    assert win._board_view.transform() == before  # selection does not resize
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    win._refresh()
    assert win._board_view.transform() == before  # a move does not resize

    win._sidebar.setCurrentIndex(1)  # tab switch
    win._refresh()
    assert win._board_view.transform() == before

    win._clock_tick()
    assert win._board_view.transform() == before


def test_replay_does_not_resize_board(qapp):
    ctrl, win = _window(qapp)
    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    before = win._board_view.transform()
    assert ctrl.display_ply(1)
    win._refresh()
    assert win._board_view.transform() == before
    ctrl.return_to_current()
    win._refresh()
    assert win._board_view.transform() == before


def test_resize_updates_fit_transform(qapp):
    ctrl, win = _window(qapp)
    win.resize(900, 700)
    win._refresh()
    small = win._board_view.transform().m11()
    win.resize(600, 500)
    win._refresh()
    larger_scale = win._board_view.transform().m11()
    assert larger_scale < small  # smaller viewport -> smaller scale


def test_zoom_gated_by_zoom_mode(qapp):
    _, win = _window(qapp)
    assert not win._board_view.zoom_mode_enabled()
    before = win._board_view.transform()
    win._board_view.zoom_in()
    win._board_view.zoom_out()
    assert win._board_view.transform() == before  # wheel/zoom no-op by default

    win._act_zoom_mode.setChecked(True)
    win._toggle_zoom_mode()
    assert win._board_view.zoom_mode_enabled()
    win._board_view.zoom_in()
    assert win._board_view.transform() != before
    win._board_view.reset_zoom()
    assert win._board_view.transform() == before


def test_zoom_mode_default_from_settings(qapp):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ZOOM_MODE, True)
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    assert win._board_view.zoom_mode_enabled()


# ------------------------------------------------------------- info architecture

def test_sidebar_has_only_moves_and_rules(qapp):
    _, win = _window(qapp)
    assert [win._sidebar.tabText(i) for i in range(win._sidebar.count())] == [
        "Moves",
        "Rules",
    ]


def test_developer_info_absent_from_main_ui(qapp):
    _, win = _window(qapp)
    assert "fingerprint" not in win._status_main.text().lower()
    assert "Player 0" not in win._status_main.text()
    assert "Player 1" not in win._status_main.text()
    overview = win._rules_panel._overview.text()
    assert "fingerprint" not in overview.lower()
    assert "seed" not in overview.lower()


def test_diagnostics_dialog_contains_developer_info(qapp):
    from generic_chess.ui.dialogs.diagnostics_dialog import DiagnosticsDialog

    ctrl, win = _window(qapp)
    dialog = DiagnosticsDialog(ctrl, win._tr, win._app_version)
    fingerprint = dialog._labels["diagnostics.ruleset_fingerprint"].text()
    assert ctrl.compiled.ruleset_fingerprint == fingerprint


# ---------------------------------------------------------------------- replay

def test_replay_selects_ply_and_blocks_submission(qapp):
    ctrl, win = _window(qapp)
    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    live = ctrl.session.state.ply_count
    assert ctrl.display_ply(1)
    win._refresh()
    selected = win._moves_panel._list.selectedItems()
    assert selected and selected[0].data(Qt.UserRole) == 1
    # Submitting while viewing history must not touch the live session.
    before = ctrl.session.state.ply_count
    ctrl.submit_action(ctrl.session.legal_actions()[0])
    assert ctrl.session.state.ply_count == before
    ctrl.return_to_current()
    win._refresh()
    assert ctrl.session.state.ply_count == live


def test_game_over_hides_to_move(qapp):
    from generic_chess.ai.budget import ThinkingConfig
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    ctrl, win = _mate_setup(qapp)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(),
        )
    )
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._refresh()
    assert ctrl.session.result.status.value == "checkmate"
    assert "Game over" in win._moves_panel._primary.text()
    assert "to move" not in win._status_main.text().lower()


# ---------------------------------------------------------------------- inspect

def test_board_piece_inspect_shows_rules_detail(qapp):
    ctrl, win = _window(qapp)
    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    win._refresh()
    type_id = ctrl.piece_info().type_id
    assert type_id in win._rules_panel._detail.text()


def test_inspect_type_switches_to_rules_tab(qapp):
    ctrl, win = _window(qapp)
    win._sidebar.setCurrentIndex(0)
    first = ctrl.compiled.piece_types[0].type_id
    win._inspect_type(first)
    assert win._sidebar.currentWidget() is win._rules_panel
    assert win._rules_panel._types.currentItem() is not None


# ---------------------------------------------------------------- localization

def test_language_switch_updates_main_surfaces(qapp):
    _, win = _window(qapp, language="en")
    assert win._sidebar.tabText(0) == "Moves"
    assert "White" in win._player_bars[0]._name.text()
    win._tr.set_language("ja_JP")
    assert win._sidebar.tabText(0) == "棋譜"
    assert "白" in win._player_bars[0]._name.text()
    assert "Player 0" not in win._player_bars[0]._name.text()


def test_localization_cover_key_surfaces(qapp):
    for language in ("en", "zh_CN", "ja_JP"):
        _, win = _window(qapp, language=language)
        tab = win._sidebar.tabText(0)
        assert tab and tab != "tab.moves"
        assert win._player_bars[0]._name.text()
        assert win._moves_panel._primary.text()


# ------------------------------------------------------------------- player bar

def test_player_bar_flip_swaps_bars_but_not_semantics(qapp):
    ctrl, win = _window(qapp)
    assert win._bar_bottom.owner() == 0
    assert win._bar_top.owner() == 1
    ctrl.flip_board()
    win._refresh()
    assert win._bar_bottom.owner() == 1
    assert win._bar_top.owner() == 0
    assert win._player_bars[0].owner() == 0  # semantics never change


# ---------------------------------------------------------- selection banner

def test_selection_banner_appears_updates_hides(qapp):
    ctrl, win = _window(qapp)
    win._sidebar.setCurrentWidget(win._rules_panel)
    banner = win._rules_panel._entity
    assert not banner.isVisible()

    sq1 = _first_white_piece_square(ctrl)
    ctrl.square_clicked(sq1)
    win._refresh()
    assert banner.isVisible()
    assert banner._title.text() == "Current selection"
    assert str(sq1) in banner._body.text()

    sq2 = next(
        sv.square
        for sv in ctrl.board_view_model().squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.square != sq1
    )
    ctrl.square_clicked(sq2)
    win._refresh()
    assert str(sq2) in banner._body.text()
    assert str(sq1) not in banner._body.text()

    ctrl.cancel()
    win._refresh()
    assert not banner.isVisible()


def test_selection_banner_localized(qapp):
    expected = {
        "en": ("Current selection", "Position:", "White"),
        "zh_CN": ("当前选择", "位置：", "白方"),
        "ja_JP": ("現在の選択", "位置：", "白"),
    }
    for language, (title, position_marker, owner_marker) in expected.items():
        ctrl, win = _window(qapp, language=language)
        win._sidebar.setCurrentWidget(win._rules_panel)
        sq = _first_white_piece_square(ctrl)
        ctrl.square_clicked(sq)
        win._refresh()
        banner = win._rules_panel._entity
        assert banner._title.text() == title
        assert owner_marker in banner._body.text()
        assert position_marker in banner._body.text()
        assert "未升变" in banner._body.text() or "未成" in banner._body.text() or "not promoted" in banner._body.text()


def test_selection_banner_theme_contrast():
    for dark in (True, False):
        theme = Theme(dark_mode=dark)
        assert _contrast_ratio(theme.selection_fg, theme.selection_bg) >= 4.5
        assert _contrast_ratio(theme.selection_secondary, theme.selection_bg) >= 4.5


def test_selection_banner_does_not_resize_board(qapp):
    ctrl, win = _window(qapp)
    win._sidebar.setCurrentWidget(win._rules_panel)
    win._refresh()
    before_transform = win._board_view.transform()
    before_viewport = win._board_view.viewport().size()
    ctrl.square_clicked(_first_white_piece_square(ctrl))
    win._refresh()
    assert win._rules_panel._entity.isVisible()
    assert win._board_view.transform() == before_transform
    assert win._board_view.viewport().size() == before_viewport
    ctrl.cancel()
    win._refresh()
    assert not win._rules_panel._entity.isVisible()
    assert win._board_view.transform() == before_transform
    assert win._board_view.viewport().size() == before_viewport


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    lum_a = _luminance(hex_a)
    lum_b = _luminance(hex_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    channels = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linearize(c) for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# --------------------------------------------------------------- scroll area

def test_rules_detail_is_scrollable(qapp):
    _, win = _window(qapp)
    panel = win._rules_panel
    assert isinstance(panel._scroll, QScrollArea)
    assert panel._scroll.widgetResizable()
    assert (
        panel._scroll.horizontalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    assert panel._detail_layout.alignment() & Qt.AlignmentFlag.AlignTop
    # Narrow window with a long-distance piece -> content overflows vertically.
    ctrl = win._controller
    n = 8
    king = PieceType(
        "K",
        "K",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ),
        is_anchor=True,
    )
    leaper = PieceType(
        "G",
        "G",
        tuple(LeapAtom((df, dr)) for df in (-5, -3, 3, 5) for dr in (-3, 3)),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][4] = Piece(0, "K", "K", False)
    rows[7][4] = Piece(1, "K", "K", False)
    mask = (False,) * (n * n)
    ruleset = RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=(king, leaper),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={"G": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )
    ctrl.new_game_from_ruleset(ruleset)
    win._refresh()
    win._sidebar.setCurrentWidget(win._rules_panel)
    win._rules_panel.inspect_type("G")
    win.resize(640, 500)
    qapp.processEvents()
    assert panel._scroll.verticalScrollBar().maximum() > 0


# ------------------------------------------------------------ movement diagram

def test_diagram_king_like_one_step_is_5x5():
    atoms = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    layout = compute_diagram_layout(atoms)
    assert (layout.cols, layout.rows) == (5, 5)
    assert len(layout.leap_targets) == 8
    assert not any(max(abs(df), abs(dr)) == 2 for df, dr in layout.leap_targets)
    assert not layout.rays


def test_diagram_forward_one_step():
    layout = compute_diagram_layout((LeapAtom((0, 1)),))
    assert (layout.cols, layout.rows) == (5, 5)
    assert layout.leap_targets == frozenset({(0, 1)})
    assert layout.has_forward


def test_diagram_long_leaper_keeps_midpoints_clear():
    atoms = tuple(LeapAtom(off) for off in ((1, 3), (-1, 3), (1, -3), (-1, -3)))
    layout = compute_diagram_layout(atoms)
    assert layout.rows == 9  # max rank distance 3 -> radius 4
    assert layout.cols == 5
    for off in ((1, 3), (-1, 3), (1, -3), (-1, -3)):
        assert off in layout.leap_targets
    assert (0, 1) not in layout.leap_targets
    assert (0, 2) not in layout.leap_targets


def test_diagram_orthogonal_ray_continuous_with_arrow():
    layout = compute_diagram_layout((RayAtom((0, 1)), RayAtom((0, -1))))
    assert (layout.cols, layout.rows) == (7, 7)
    forward = next(r for r in layout.rays if r.direction == (0, 1))
    assert forward.path == ((0, 1), (0, 2), (0, 3))
    assert forward.unlimited and forward.clipped


def test_diagram_slope_2_1_not_drawn_as_diagonal():
    layout = compute_diagram_layout((RayAtom((2, 1)), RayAtom((-2, -1))))
    forward = next(r for r in layout.rays if r.direction == (2, 1))
    assert (2, 1) in forward.path
    assert (1, 1) not in forward.path  # true grid step, not a 45-degree line


def test_diagram_mixed_atoms_dedup_and_order_independent():
    atoms_a = (RayAtom((0, 1)), LeapAtom((2, 2)), LeapAtom((0, 1)))
    atoms_b = (LeapAtom((0, 1)), LeapAtom((2, 2)), RayAtom((0, 1)))
    layout_a = compute_diagram_layout(atoms_a)
    layout_b = compute_diagram_layout(atoms_b)
    assert layout_a == layout_b
    assert (0, 1) in layout_a.leap_targets
    assert len(layout_a.rays) == 1


def test_diagram_large_leap_uses_edge_marker_not_silent_drop():
    layout = compute_diagram_layout((LeapAtom((8, 4)),))
    assert layout.cols <= 11 and layout.rows <= 11
    assert layout.clipped_leaps
    direction, offset = layout.clipped_leaps[0]
    assert offset == (8, 4)
    assert direction == (1, 1)


def test_diagram_cell_forward_maps_above_center():
    assert diagram_cell((2, 2), (0, 1)) == (2, 1)


def test_diagram_cell_backward_maps_below_center():
    assert diagram_cell((2, 2), (0, -1)) == (2, 3)


def test_diagram_cell_forward_diagonal_preserves_left_right():
    assert diagram_cell((4, 4), (-1, 3)) == (3, 1)
    assert diagram_cell((4, 4), (1, 3)) == (5, 1)


def test_diagram_screen_direction_flips_only_y():
    assert diagram_screen_direction((2, 1)) == (2, -1)
    assert diagram_screen_direction((-2, -1)) == (-2, 1)


def test_center_point_maps_forward_above_center(qapp):
    from generic_chess.ui.board.texture_cache import TextureCache
    from generic_chess.ui.i18n.manager import LocalizationManager
    from generic_chess.ui.panels.movement_diagram import MovementDiagram
    from generic_chess.ui.theme import default_theme

    widget = MovementDiagram(
        TextureCache(), default_theme(), LocalizationManager("en")
    )
    layout = compute_diagram_layout((LeapAtom((0, 1)), LeapAtom((0, -1))))
    widget._layout = layout
    widget._cell = 10
    forward = widget._center_point(layout, 0, 0, (0, 1))
    backward = widget._center_point(layout, 0, 0, (0, -1))
    center = widget._center_point(layout, 0, 0, (0, 0))
    assert forward.y() < center.y() < backward.y()
    assert forward.x() == center.x() == backward.x()


def test_diagram_clipped_markers_inside_view():
    layout = compute_diagram_layout((LeapAtom((8, 4)),))
    assert layout.clipped_leaps
    for direction, _offset in layout.clipped_leaps:
        edge_offset = (
            direction[0] * layout.center[0],
            direction[1] * layout.center[1],
        )
        col, row = diagram_cell(layout.center, edge_offset)
        assert 0 <= col < layout.cols
        assert 0 <= row < layout.rows


def test_rules_panel_diagram_populated_and_localized(qapp):
    ctrl, win = _window(qapp, language="zh_CN")
    first = win._rules_panel._types.item(0).data(Qt.UserRole)
    win._inspect_type(first)
    diagram = win._rules_panel._diagram
    assert diagram.layout_data() is not None
    assert diagram.layout_data().cols >= 5
    assert win._tr.text("diagram.forward") == "前进方向"
    assert win._tr.text("diagram.leap_legend") == "跳跃可达格"


# --------------------------------------------------------------- game overlay

def test_game_over_overlay_checkmate_and_buttons(qapp):
    ctrl, win = _mate_setup(qapp)
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._refresh()
    overlay = win._overlay
    assert overlay.isVisible()
    assert "wins" in overlay._winner.text()
    assert "Checkmate" in overlay._reason.text()
    assert overlay._title.text() == "Game over"

    win._sidebar.setCurrentWidget(win._rules_panel)
    overlay._btn_view_moves.click()
    assert win._sidebar.currentWidget() is win._moves_panel

    overlay._btn_play_again.click()
    win._refresh()
    assert ctrl.session.state.ply_count == 0
    assert not overlay.isVisible()


def test_game_over_overlay_stalemate(qapp):
    ctrl, win = _window_with_ruleset(qapp, _stalemate_ruleset())
    ctrl.submit_action(BoardMove(Square(2, 5), Square(3, 5)))
    win._refresh()
    assert ctrl.session.result.status.value == "stalemate"
    overlay = win._overlay
    assert overlay.isVisible()
    assert "Draw" in overlay._winner.text()
    assert "Stalemate" in overlay._reason.text()


def test_game_over_overlay_max_ply(qapp):
    ctrl, win = _window_with_ruleset(qapp, _max_ply_ruleset())
    actions = ctrl.session.legal_actions()
    assert actions
    ctrl.submit_action(actions[0])
    win._refresh()
    assert ctrl.session.result.status.value == "max_ply"
    assert win._overlay.isVisible()
    assert "Move limit" in win._overlay._reason.text()


def test_game_over_overlay_resignation_dismiss_keeps_terminal(qapp):
    ctrl, win = _window(qapp)
    ctrl.resign()
    win._refresh()
    overlay = win._overlay
    assert overlay.isVisible()
    assert "wins" in overlay._winner.text()
    assert "resigned" in overlay._reason.text()
    overlay._btn_dismiss.click()
    assert not overlay.isVisible()
    assert ctrl.session.result.status.value == "resignation"


def test_overlay_hides_on_history_preview_and_restores(qapp):
    ctrl, win = _mate_setup(qapp)
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._refresh()
    assert win._overlay.isVisible()
    ctrl.display_ply(0)
    win._refresh()
    assert not win._overlay.isVisible()
    ctrl.return_to_current()
    win._refresh()
    assert win._overlay.isVisible()
    win._restart()
    win._refresh()
    assert not win._overlay.isVisible()


def test_overlay_centered_on_resize_and_flip(qapp):
    ctrl, win = _mate_setup(qapp)
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._refresh()
    win.resize(1000, 700)
    qapp.processEvents()
    assert win._overlay.geometry() == win._board_container.rect()
    before_transform = win._board_view.transform()
    ctrl.flip_board()
    win._refresh()
    qapp.processEvents()
    assert win._overlay.geometry() == win._board_container.rect()
    assert win._board_view.transform() == before_transform


def test_overlay_does_not_change_board_transform(qapp):
    ctrl, win = _window(qapp)
    win._refresh()
    before = win._board_view.transform()
    ctrl.resign()
    win._refresh()
    assert win._overlay.isVisible()
    assert win._board_view.transform() == before


# -------------------------------------------------------------- localization

def test_zh_mode_has_no_english_menu_or_replay_labels(qapp):
    _, win = _window(qapp, language="zh_CN")
    menus = [a.text() for a in win.menuBar().actions()]
    assert menus == ["文件(&F)", "对局(&G)", "查看(&V)", "工具(&T)", "帮助(&H)"]
    moves = win._moves_panel
    assert moves._btn_first.text() == "最前"
    assert moves._btn_prev.text() == "上一手"
    assert moves._btn_next.text() == "下一手"
    assert moves._btn_last.text() == "最后"
    assert moves._return_btn.text() == "返回当前局面"
    english = {
        "File",
        "Game",
        "View",
        "Tools",
        "Help",
        "First",
        "Previous",
        "Next",
        "Last",
        "Return to Current Position",
    }
    labels = {
        moves._btn_first.text(),
        moves._btn_prev.text(),
        moves._btn_next.text(),
        moves._btn_last.text(),
        moves._return_btn.text(),
    }
    assert not labels & english
    assert not win._rules_panel._entity.isVisible()
    assert win._tr.text("rules.current_selection") == "当前选择"
    assert win._overlay._title.text() == "对局结束"


def test_i18n_critical_key_parity_across_languages():
    base = os.path.join(os.path.dirname(__file__), "..", "generic_chess", "ui", "i18n")
    tables = {
        lang: json.load(open(os.path.join(base, f"{lang}.json"), encoding="utf-8"))
        for lang in ("en", "zh_CN", "ja_JP")
    }
    critical = [
        "menu.file",
        "menu.game",
        "menu.view",
        "menu.tools",
        "menu.help",
        "moves.first",
        "moves.prev",
        "moves.next",
        "moves.last",
        "moves.return_live",
        "toolbar.new",
        "toolbar.open",
        "toolbar.save",
        "toolbar.undo",
        "toolbar.redo",
        "toolbar.flip",
        "rules.current_selection",
        "rules.base_type",
        "rules.selection_line",
        "rules.position_line",
        "rules.status_line",
        "rules.base_type_line",
        "rules.movement_section",
        "diagram.forward",
        "diagram.leap_legend",
        "diagram.ray_legend",
        "overlay.game_over",
        "overlay.view_moves",
        "overlay.play_again",
        "overlay.view_board",
        "status.ai_timeout",
        "prefs.animations",
        "promotion.title",
        "promotion.choose",
        "promotion.promote_to",
        "promotion.none",
        "new_match.title",
        "new_match.choose_ruleset",
        "new_match.ai_timeout_note",
    ]
    for key in critical:
        for lang, table in tables.items():
            assert key in table, (key, lang)


# ------------------------------------------------------------------ toolbar

def test_toolbar_icons_distinct_and_localized(qapp):
    _, win = _window(qapp, language="zh_CN")
    names = ("new", "open", "save", "undo", "redo", "flip")
    actions = [win._toolbar_actions()[name] for name in names]
    pixmaps = [action.icon().pixmap(24, 24) for action in actions]
    assert all(not pixmap.isNull() for pixmap in pixmaps)
    images = [pixmap.toImage() for pixmap in pixmaps]
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            assert images[i] != images[j], (names[i], names[j])
    assert win._toolbar_actions()["new"].toolTip() == "新建对局"
    assert win._toolbar_actions()["undo"].toolTip() == "撤销"
    assert win._toolbar_actions()["redo"].toolTip() == "重做"
    assert win._toolbar_actions()["flip"].toolTip() == "翻转棋盘"
