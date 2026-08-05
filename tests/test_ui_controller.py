"""UIController logic tests (Qt-free, deterministic)."""

import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.ui.controller import UIController
from generic_chess.ui.settings import DictSettingsStore, KEY_ENABLE_PREVIEW

from conftest import king_type, make_ruleset, T


@pytest.fixture()
def ui_tmp_dir():
    base = Path(__file__).resolve().parent.parent
    tmp = base / f".gc_ui_tmp_{uuid.uuid4().hex}"
    os.makedirs(tmp, mode=0o777)
    yield tmp
    resolved = tmp.resolve()
    if tmp.exists() and resolved.is_relative_to(base.resolve()):
        shutil.rmtree(resolved)


def _controller(seed=42):
    ctrl = UIController(settings=DictSettingsStore())
    assert ctrl.new_game(seed=seed)
    return ctrl


def _own_pawn_square(ctrl):
    model = ctrl.board_view_model()
    return next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )


def _own_piece(ctrl, owner):
    model = ctrl.board_view_model()
    return next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == owner
    )


def test_new_game_initial_state():
    ctrl = _controller()
    model = ctrl.board_view_model()
    assert model.board_size == 8
    assert len(model.squares) == 64
    assert model.side_to_move == 0
    info = ctrl.game_info()
    assert info.ply_count == 0
    assert info.fingerprint
    assert info.result.status.value == "ongoing"


def test_select_own_piece_and_legal_targets():
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    assert ctrl.interaction.selected_square == square
    assert ctrl.interaction.legal_actions
    assert all(isinstance(a, BoardMove) and a.from_square == square for a in ctrl.interaction.legal_actions)
    model = ctrl.board_view_model()
    selected = next(s for s in model.squares if s.is_selected)
    assert selected.square == square
    legal_squares = {s.square for s in model.squares if s.is_legal_move or s.is_legal_capture}
    assert legal_squares == {a.to_square for a in ctrl.interaction.legal_actions}


def test_click_another_own_piece_switches_selection():
    ctrl = _controller()
    model = ctrl.board_view_model()
    pawns = [
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    ]
    ctrl.square_clicked(pawns[0])
    ctrl.square_clicked(pawns[1])
    assert ctrl.interaction.selected_square == pawns[1]


def test_cancel_clears_interaction():
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    ctrl.cancel()
    assert ctrl.interaction.selected_square is None
    assert ctrl.interaction.legal_actions == ()
    assert ctrl.interaction.preview_squares == ()


def test_enemy_preview_and_disabling():
    settings = DictSettingsStore()
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    model = ctrl.board_view_model()
    enemy = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 1
    )
    ctrl.square_clicked(enemy)
    assert ctrl.interaction.preview_piece_square == enemy
    assert ctrl.interaction.preview_squares
    assert ctrl.piece_info().is_preview
    assert ctrl.session.state.ply_count == 0  # no action executed
    ctrl.cancel()
    assert ctrl.interaction.preview_squares == ()

    settings.set(KEY_ENABLE_PREVIEW, False)
    ctrl.square_clicked(enemy)
    assert ctrl.interaction.preview_squares == ()


def test_submit_updates_state_history_and_last_move():
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    assert ctrl.session.state.ply_count == 1
    assert ctrl.interaction.selected_square is None
    assert len(ctrl.history_entries()) == 1
    model = ctrl.board_view_model()
    last_from = next(s for s in model.squares if s.is_last_move_from).square
    last_to = next(s for s in model.squares if s.is_last_move_to).square
    assert (last_from, last_to) == (square, target)


def test_undo_redo_and_redo_cleared_by_new_move():
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    assert ctrl.undo()
    assert ctrl.session.state.ply_count == 0
    assert not ctrl.can_undo
    assert ctrl.can_redo
    assert ctrl.redo()
    assert ctrl.session.state.ply_count == 1
    # A new move clears the redo stack.
    ctrl.square_clicked(_own_piece(ctrl, 1))  # player 1 is to move after redo
    target2 = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target2)
    assert not ctrl.can_redo


def test_restart_resets():
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    ctrl.restart()
    assert ctrl.session.state.ply_count == 0
    assert ctrl.history_entries() == ()


def _promotion_controller():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, -1)))
    ruleset = make_ruleset(
        8,
        [king_type(), pawn, gold],
        auto_promotion=True,
        lines=[
            ".......k",
            "....P...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    ctrl = UIController(settings=DictSettingsStore())
    assert ctrl.new_game_from_ruleset(ruleset)
    return ctrl


def test_forced_unique_promotion_auto_submitted():
    ctrl = _promotion_controller()
    ctrl.square_clicked(Square(4, 6))
    assert len(ctrl.interaction.legal_actions) == 1
    ctrl.square_clicked(Square(4, 7))
    assert ctrl.session.state.ply_count == 1
    assert ctrl.interaction.pending_promotion_actions == ()
    promoted = [p for p in ctrl.session.state.position.board if p is not None and p.promoted]
    assert len(promoted) == 1
    assert (promoted[0].base_type_id, promoted[0].current_type_id) == ("P", "G")


def _multi_promotion_controller():
    hybrid = T(
        "H",
        LeapAtom((1, 0)),
        LeapAtom((-1, 0)),
        LeapAtom((0, 1)),
        is_promotable=True,
        targets=("G",),
    )
    gold = T("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, -1)))
    ruleset = make_ruleset(
        8,
        [king_type(), hybrid, gold],
        auto_promotion=True,
        lines=[
            ".......k",
            "....H...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    ctrl = UIController(settings=DictSettingsStore())
    assert ctrl.new_game_from_ruleset(ruleset)
    return ctrl


def test_multiple_promotion_options_prompt_and_choose():
    ctrl = _multi_promotion_controller()
    ctrl.square_clicked(Square(4, 6))
    ctrl.square_clicked(Square(4, 7))
    assert len(ctrl.interaction.pending_promotion_actions) == 2
    promoted = next(
        a for a in ctrl.interaction.pending_promotion_actions if a.promotion_target_id == "G"
    )
    ctrl.choose_promotion(promoted)
    assert ctrl.session.state.ply_count == 1
    assert ctrl.interaction.pending_promotion_actions == ()
    piece = ctrl.session.state.position.board[7 * 8 + 4]
    assert piece.promoted and piece.current_type_id == "G"


def test_multiple_promotion_cancel_does_not_move():
    ctrl = _multi_promotion_controller()
    ctrl.square_clicked(Square(4, 6))
    ctrl.square_clicked(Square(4, 7))
    assert ctrl.interaction.pending_promotion_actions
    ctrl.cancel_promotion()
    assert ctrl.session.state.ply_count == 0
    assert ctrl.interaction.pending_promotion_actions == ()


def _drop_controller():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    filler = T("F", LeapAtom((1, 0)))
    ruleset = make_ruleset(
        8,
        [king_type(), rook, filler],
        lines=[
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRf.....",
        ],
    )
    ctrl = UIController(settings=DictSettingsStore())
    assert ctrl.new_game_from_ruleset(ruleset)
    return ctrl


def test_drop_flow():
    ctrl = _drop_controller()
    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(Square(2, 0))  # capture -> hand
    assert ctrl.session.state.position.hands[0].count("F") == 1
    # Player 1 moves so player 0 gets the turn back.
    ctrl.square_clicked(Square(7, 7))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    ctrl.hand_piece_clicked("F")
    assert ctrl.interaction.selected_hand_piece_type_id == "F"
    assert ctrl.interaction.legal_actions
    assert all(isinstance(a, DropMove) and a.base_type_id == "F" for a in ctrl.interaction.legal_actions)
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    assert ctrl.session.state.ply_count == 3
    assert ctrl.session.state.position.hands[0].count("F") == 0
    assert ctrl.history_entries()[-1].label.startswith("drop F@")


def test_drop_cancel_leaves_state_unchanged():
    ctrl = _drop_controller()
    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(Square(2, 0))
    ctrl.square_clicked(Square(7, 7))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    ctrl.hand_piece_clicked("F")
    ctrl.cancel()
    assert ctrl.interaction.selected_hand_piece_type_id is None
    assert ctrl.session.state.ply_count == 2
    assert ctrl.session.state.position.hands[0].count("F") == 1


def test_history_preview_and_return():
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    assert ctrl.display_ply(0)
    assert ctrl.interaction.displayed_ply == 0
    assert ctrl.session.state.ply_count == 1  # live session untouched
    pos0 = ctrl.displayed_position()
    assert sum(1 for p in pos0.board if p is not None) == 32  # initial position
    ctrl.return_to_current()
    assert ctrl.interaction.displayed_ply is None
    assert ctrl.session.state.ply_count == 1


def test_file_roundtrip(ui_tmp_dir):
    ctrl = _controller()
    square = _own_pawn_square(ctrl)
    ctrl.square_clicked(square)
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)

    ruleset_path = ui_tmp_dir / "rules.json"
    record_path = ui_tmp_dir / "record.json"
    assert ctrl.export_ruleset(str(ruleset_path))
    assert ctrl.save_record(str(record_path))

    from generic_chess.rules.serialization import deserialize_ruleset

    ctrl2 = UIController(settings=DictSettingsStore())
    assert ctrl2.new_game_from_ruleset(deserialize_ruleset(ruleset_path.read_text(encoding="utf-8")))
    assert ctrl2.open_record(str(record_path))
    assert ctrl2.session.state.ply_count == ctrl.session.state.ply_count
    assert ctrl2.history_entries() == ctrl.history_entries()
    assert ctrl2.board_view_model().squares == ctrl.board_view_model().squares


def test_record_fingerprint_mismatch_preserves_game(ui_tmp_dir):
    ctrl_a = _controller(seed=42)
    ctrl_b = _controller(seed=43)
    record_path = ui_tmp_dir / "record.json"
    ctrl_a.square_clicked(_own_pawn_square(ctrl_a))
    ctrl_a.square_clicked(ctrl_a.interaction.legal_actions[0].to_square)
    assert ctrl_a.save_record(str(record_path))
    ply_before = ctrl_b.session.state.ply_count
    assert not ctrl_b.open_record(str(record_path))
    assert "fingerprint" in ctrl_b.last_error
    assert ctrl_b.session.state.ply_count == ply_before  # original game preserved


def test_open_ruleset_error_keeps_game(ui_tmp_dir):
    ctrl = _controller()
    ply_before = ctrl.session.state.ply_count
    assert not ctrl.open_ruleset(str(ui_tmp_dir / "missing.json"))
    assert ctrl.last_error
    assert ctrl.session.state.ply_count == ply_before
