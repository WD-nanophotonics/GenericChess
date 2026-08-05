"""Unified New Match dialog: ruleset, players (Human/AI each side), clock, AI."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ...ai.budget import ThinkingConfig, ThinkingPreset, ThinkingStrategy
from ...clock import SideTimeConfig, TimeControl, TimeControlMode
from ..match import MatchConfig, ParticipantKind
from ..settings import SettingsStore


@dataclass(frozen=True, slots=True)
class NewMatchRequest:
    ruleset_mode: str  # "current" | "generate" | "file"
    seed: int = 42
    board_size: int = 8
    preset: str = "classic_like"
    hybrid: bool = False
    ruleset_path: str | None = None
    participants: tuple[ParticipantKind, ParticipantKind] = (ParticipantKind.HUMAN, ParticipantKind.AI)
    time_control: TimeControl = TimeControl(mode=TimeControlMode.NONE)
    ai_config: ThinkingConfig = ThinkingConfig(strategy=ThinkingStrategy.AUTO_TIME)


class NewMatchDialog(QDialog):
    def __init__(self, settings: SettingsStore, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Match")
        self._settings = settings
        self._request: NewMatchRequest | None = None
        layout = QVBoxLayout(self)

        ruleset_box = QGroupBox("Ruleset")
        ruleset_form = QFormLayout(ruleset_box)
        self._source = QComboBox()
        self._source.addItems(["Current ruleset", "Generate new ruleset", "Load ruleset file"])
        self._source.setCurrentIndex(int(settings.get("match/ruleset_source", 0)))
        self._source.currentIndexChanged.connect(self._sync_source)
        ruleset_form.addRow("Source", self._source)
        self._preset = QComboBox()
        self._preset.addItems(["classic_like", "bilateral_random", "free_random"])
        ruleset_form.addRow("Preset", self._preset)
        self._seed = QSpinBox()
        self._seed.setRange(0, 2**31 - 1)
        self._seed.setValue(int(settings.get("match/seed", 42)))
        ruleset_form.addRow("Seed", self._seed)
        self._board_size = QSpinBox()
        self._board_size.setRange(4, 32)
        self._board_size.setValue(int(settings.get("match/board_size", 8)))
        ruleset_form.addRow("Board size", self._board_size)
        self._hybrid = QCheckBox("Allow hybrid leap/ray pieces")
        ruleset_form.addRow("", self._hybrid)
        path_row = QHBoxLayout()
        self._path_label = QLabel("—")
        self._browse = QPushButton("Choose RuleSet…")
        self._browse.clicked.connect(self._choose_ruleset)
        path_row.addWidget(self._path_label, 1)
        path_row.addWidget(self._browse)
        ruleset_form.addRow("File", path_row)
        layout.addWidget(ruleset_box)

        players_box = QGroupBox("Players")
        players_form = QFormLayout(players_box)
        self._side0 = QComboBox()
        self._side0.addItems(["Human", "AI"])
        self._side0.setCurrentIndex(int(settings.get("match/side0", 0)))
        players_form.addRow("先手 / White (Player 0)", self._side0)
        self._side1 = QComboBox()
        self._side1.addItems(["Human", "AI"])
        self._side1.setCurrentIndex(int(settings.get("match/side1", 1)))
        players_form.addRow("後手 / Black (Player 1)", self._side1)
        layout.addWidget(players_box)

        clock_box = QGroupBox("Time control")
        clock_form = QFormLayout(clock_box)
        self._mode = QComboBox()
        self._mode.addItems(["No clock", "Byoyomi (読秒)", "Fischer (increment)"])
        self._mode.setCurrentIndex(int(settings.get("match/mode", 0)))
        clock_form.addRow("Mode", self._mode)
        self._main_seconds = QSpinBox()
        self._main_seconds.setRange(0, 3600)
        self._main_seconds.setValue(int(settings.get("match/main_seconds", 600)))
        clock_form.addRow("Main time (seconds)", self._main_seconds)
        self._overtime_seconds = QSpinBox()
        self._overtime_seconds.setRange(0, 600)
        self._overtime_seconds.setValue(int(settings.get("match/overtime_seconds", 30)))
        clock_form.addRow("Byoyomi / increment (seconds)", self._overtime_seconds)
        layout.addWidget(clock_box)

        ai_box = QGroupBox("AI strength")
        ai_form = QFormLayout(ai_box)
        self._strategy = QComboBox()
        self._strategy.addItems(
            ["Auto (use remaining clock time)", "Preset node budget", "Fixed seconds per move"]
        )
        self._strategy.setCurrentIndex(int(settings.get("match/strategy", 0)))
        ai_form.addRow("Budget", self._strategy)
        self._preset_ai = QComboBox()
        self._preset_ai.addItems(["Quick", "Balanced", "Deep"])
        self._preset_ai.setCurrentIndex(int(settings.get("match/preset", 1)))
        ai_form.addRow("Preset", self._preset_ai)
        self._move_time = QDoubleSpinBox()
        self._move_time.setRange(0.1, 300.0)
        self._move_time.setSingleStep(0.1)
        self._move_time.setValue(float(settings.get("match/move_time", 1.5)))
        ai_form.addRow("Seconds per move", self._move_time)
        self._max_depth = QSpinBox()
        self._max_depth.setRange(0, 64)
        self._max_depth.setValue(int(settings.get("match/max_depth", 0)))
        ai_form.addRow("Max depth (0 = unlimited)", self._max_depth)
        layout.addWidget(ai_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sync_source()

    def _sync_source(self) -> None:
        index = self._source.currentIndex()
        generate = index == 1
        file_mode = index == 2
        for widget in (self._preset, self._seed, self._board_size, self._hybrid):
            widget.setEnabled(generate)
        self._browse.setEnabled(file_mode)

    def _choose_ruleset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open RuleSet", "", "JSON files (*.json)")
        if path:
            self._path_label.setText(path)

    def _accept(self) -> None:
        mode = [TimeControlMode.NONE, TimeControlMode.BYOYOMI, TimeControlMode.FISCHER][
            self._mode.currentIndex()
        ]
        side = SideTimeConfig(self._main_seconds.value(), self._overtime_seconds.value())
        time_control = TimeControl(mode=mode, owner0=side, owner1=side, time_forfeit=True)
        strategy = [
            ThinkingStrategy.AUTO_TIME,
            ThinkingStrategy.FIXED_NODES,
            ThinkingStrategy.FIXED_TIME,
        ][self._strategy.currentIndex()]
        if strategy is ThinkingStrategy.FIXED_NODES:
            config = ThinkingConfig(
                strategy=strategy,
                preset=[
                    ThinkingPreset.QUICK,
                    ThinkingPreset.BALANCED,
                    ThinkingPreset.DEEP,
                ][self._preset_ai.currentIndex()],
                max_depth=self._max_depth.value() or None,
            )
        elif strategy is ThinkingStrategy.FIXED_TIME:
            config = ThinkingConfig(
                strategy=strategy,
                move_time_seconds=self._move_time.value(),
                max_depth=self._max_depth.value() or None,
            )
        else:
            config = ThinkingConfig(
                strategy=strategy,
                preset=[
                    ThinkingPreset.QUICK,
                    ThinkingPreset.BALANCED,
                    ThinkingPreset.DEEP,
                ][self._preset_ai.currentIndex()],
                move_time_seconds=self._move_time.value(),
                max_depth=self._max_depth.value() or None,
            )
        self._request = NewMatchRequest(
            ruleset_mode=["current", "generate", "file"][self._source.currentIndex()],
            seed=self._seed.value(),
            board_size=self._board_size.value(),
            preset=self._preset.currentText(),
            hybrid=self._hybrid.isChecked(),
            ruleset_path=self._path_label.text()
            if self._source.currentIndex() == 2 and self._path_label.text() != "—"
            else None,
            participants=(
                ParticipantKind.HUMAN if self._side0.currentIndex() == 0 else ParticipantKind.AI,
                ParticipantKind.HUMAN if self._side1.currentIndex() == 0 else ParticipantKind.AI,
            ),
            time_control=time_control,
            ai_config=config,
        )
        self.accept()

    def request(self) -> NewMatchRequest | None:
        return self._request

    def persist_defaults(self) -> None:
        if self._request is None:
            return
        self._settings.set("match/ruleset_source", self._source.currentIndex())
        self._settings.set("match/seed", self._seed.value())
        self._settings.set("match/board_size", self._board_size.value())
        self._settings.set("match/side0", self._side0.currentIndex())
        self._settings.set("match/side1", self._side1.currentIndex())
        self._settings.set("match/mode", self._mode.currentIndex())
        self._settings.set("match/main_seconds", self._main_seconds.value())
        self._settings.set("match/overtime_seconds", self._overtime_seconds.value())
        self._settings.set("match/strategy", self._strategy.currentIndex())
        self._settings.set("match/preset", self._preset_ai.currentIndex())
        self._settings.set("match/move_time", self._move_time.value())
        self._settings.set("match/max_depth", self._max_depth.value())

    def match_config(self) -> MatchConfig:
        req = self._request
        assert req is not None
        return MatchConfig(
            participants=req.participants,
            time_control=req.time_control,
            ai_config=req.ai_config,
        )
