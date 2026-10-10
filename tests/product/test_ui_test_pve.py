"""Real frozen-backend PVE handoff checks, without native acceleration."""

import os
import time
import hashlib
import json
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
from generic_chess.clock import TimeControl
from generic_chess.ui.ai_backend import create_ui_player
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.match import MatchConfig, ParticipantKind
from generic_chess.ui.stores import DictSettingsStore


def test_frozen_backend_sources_are_unchanged():
    root = Path(__file__).resolve().parents[2]
    baseline = json.loads((root / "docs/ui/AI_BASELINE.json").read_bytes())
    for name, expected in baseline["files"].items():
        assert hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected, name


def match(human):
    return MatchConfig(
        participants=tuple(ParticipantKind.HUMAN if i == human else ParticipantKind.AI for i in range(2)),
        time_control=TimeControl(),
        ai_config=ThinkingConfig(strategy=ThinkingStrategy.FIXED_TIME, move_time_seconds=.25,
                                 max_nodes=512, max_depth=2, quiescence_max_depth=0),
    )


@pytest.mark.parametrize("rules", ["western_chess", "standard_shogi", "generated", "hybrid"])
@pytest.mark.parametrize("human", [0, 1])
def test_real_pve_roundtrip(rules, human, tmp_path):
    ctrl = UIController()
    if rules in ("generated", "hybrid"):
        assert ctrl.new_game(seed=42, hybrid=rules == "hybrid")
    else:
        assert ctrl.new_game_from_builtin(rules)
    ctrl.start_match(match(human))
    player = create_ui_player(ctrl.compiled, use_disk_cache=False)
    for _ in range(4):
        if ctrl.session.result.status.value != "ongoing":
            break
        if ctrl.ai_move_needed():
            before = ctrl.session.state.ply_count
            decision = ctrl.make_ai_move(lambda s, limits, token: player.choose_action(s, limits, cancel_token=token))
            assert decision.action is not None
            assert ctrl.session.state.ply_count == before + 1
            assert not ctrl.ai_thinking
        else:
            assert ctrl.submit_action(ctrl.session.legal_actions()[0])
    assert ctrl.session.state.ply_count > 0
    path = tmp_path / "game.json"
    assert ctrl.save_record(str(path))
    restored = UIController()
    if rules in ("generated", "hybrid"):
        assert restored.new_game(seed=42, hybrid=rules == "hybrid")
    else:
        assert restored.new_game_from_builtin(rules)
    assert restored.open_record(str(path))
    assert restored.session.state == ctrl.session.state
    ctrl.restart()
    assert ctrl.session.state.ply_count == 0
    assert ctrl.resign()
    assert not ctrl.ai_move_needed()


def test_real_qt_worker_returns_ai_turn():
    app = QApplication.instance() or QApplication([])
    settings = DictSettingsStore()
    ctrl = UIController(settings=settings)
    assert ctrl.new_game_from_builtin("western_chess")
    ctrl.start_match(match(human=1))
    win = MainWindow(ctrl, settings)
    win._ai_player = create_ui_player(ctrl.compiled, use_disk_cache=False)
    win.show()
    try:
        win._maybe_start_ai()
        deadline = time.monotonic() + 10
        while ctrl.session.state.ply_count == 0 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        assert ctrl.session.state.ply_count == 1
        assert win._ai_error is None
        assert not ctrl.ai_thinking
        assert not ctrl.ai_move_needed()
    finally:
        assert win._shutdown()
        win.close()
        win.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
