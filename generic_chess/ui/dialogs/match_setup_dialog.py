"""New AI Match dialog: side, time control and AI strength."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
)

from ...ai.budget import ThinkingConfig, ThinkingPreset, ThinkingStrategy
from ...clock import SideTimeConfig, TimeControl, TimeControlMode
from ..match import MatchConfig, ParticipantKind
from ..settings import SettingsStore


@dataclass(frozen=True, slots=True)
class MatchSetupValues:
    human_owner: int
    time_control: TimeControl
    ai_config: ThinkingConfig


class MatchSetupDialog(QDialog):
    def __init__(self, settings: SettingsStore, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New AI Match")
        self._settings = settings
        self._values: MatchSetupValues | None = None
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._side = QComboBox()
        self._side.addItems(["White / Player 0 (先手)", "Black / Player 1 (後手)"])
        self._side.setCurrentIndex(int(settings.get("match/human_owner", 0)))
        form.addRow("Play as", self._side)
        layout.addLayout(form)

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
        self._forfeit = QCheckBox("Time forfeit ends the game")
        self._forfeit.setChecked(bool(settings.get("match/forfeit", True)))
        clock_form.addRow("", self._forfeit)
        layout.addWidget(clock_box)

        ai_box = QGroupBox("AI strength")
        ai_form = QFormLayout(ai_box)
        self._strategy = QComboBox()
        self._strategy.addItems(["Preset node budget", "Fixed seconds per move"])
        self._strategy.setCurrentIndex(int(settings.get("match/strategy", 0)))
        ai_form.addRow("Budget", self._strategy)
        self._preset = QComboBox()
        self._preset.addItems(["Quick", "Balanced", "Deep"])
        self._preset.setCurrentIndex(int(settings.get("match/preset", 1)))
        ai_form.addRow("Preset", self._preset)
        self._move_time = QDoubleSpinBox()
        self._move_time.setRange(0.1, 300.0)
        self._move_time.setSingleStep(0.1)
        self._move_time.setValue(float(settings.get("match/move_time", 1.0)))
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

    def _accept(self) -> None:
        mode = [TimeControlMode.NONE, TimeControlMode.BYOYOMI, TimeControlMode.FISCHER][
            self._mode.currentIndex()
        ]
        side = SideTimeConfig(self._main_seconds.value(), self._overtime_seconds.value())
        time_control = TimeControl(
            mode=mode,
            owner0=side,
            owner1=side,
            time_forfeit=self._forfeit.isChecked(),
        )
        if self._strategy.currentIndex() == 0:
            config = ThinkingConfig(
                strategy=ThinkingStrategy.FIXED_NODES,
                preset=[
                    ThinkingPreset.QUICK,
                    ThinkingPreset.BALANCED,
                    ThinkingPreset.DEEP,
                ][self._preset.currentIndex()],
                max_depth=self._max_depth.value() or None,
            )
        else:
            config = ThinkingConfig(
                strategy=ThinkingStrategy.FIXED_TIME,
                move_time_seconds=self._move_time.value(),
                max_depth=self._max_depth.value() or None,
            )
        self._values = MatchSetupValues(
            human_owner=self._side.currentIndex(),
            time_control=time_control,
            ai_config=config,
        )
        self.accept()

    def match_config(self) -> MatchConfig:
        values = self._values
        assert values is not None
        participants = [ParticipantKind.AI, ParticipantKind.AI]
        participants[values.human_owner] = ParticipantKind.HUMAN
        return MatchConfig(
            participants=(participants[0], participants[1]),
            time_control=values.time_control,
            ai_config=values.ai_config,
        )

    def persist_defaults(self) -> None:
        values = self._values
        if values is None:
            return
        self._settings.set("match/human_owner", self._side.currentIndex())
        self._settings.set("match/mode", self._mode.currentIndex())
        self._settings.set("match/main_seconds", self._main_seconds.value())
        self._settings.set("match/overtime_seconds", self._overtime_seconds.value())
        self._settings.set("match/forfeit", self._forfeit.isChecked())
        self._settings.set("match/strategy", self._strategy.currentIndex())
        self._settings.set("match/preset", self._preset.currentIndex())
        self._settings.set("match/move_time", self._move_time.value())
        self._settings.set("match/max_depth", self._max_depth.value())
