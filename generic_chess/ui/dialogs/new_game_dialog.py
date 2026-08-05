"""New Game dialog: generate from preset/seed or load a RuleSet file."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


@dataclass(frozen=True)
class NewGameRequest:
    mode: str  # "generate" | "ruleset"
    seed: int = 42
    board_size: int = 8
    preset: str = "classic_like"
    hybrid: bool = False
    ruleset_path: str | None = None


class NewGameDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Game")
        self._request: NewGameRequest | None = None
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._mode = QComboBox()
        self._mode.addItems(["Generate from seed", "Load RuleSet file"])
        form.addRow("Source", self._mode)
        self._preset = QComboBox()
        self._preset.addItems(["classic_like", "bilateral_random", "free_random"])
        form.addRow("Preset", self._preset)
        self._seed = QSpinBox()
        self._seed.setRange(0, 2**31 - 1)
        self._seed.setValue(42)
        form.addRow("Seed", self._seed)
        self._board_size = QSpinBox()
        self._board_size.setRange(4, 32)
        self._board_size.setValue(8)
        form.addRow("Board size", self._board_size)
        self._hybrid = QCheckBox("Allow hybrid leap/ray pieces")
        form.addRow("", self._hybrid)
        layout.addLayout(form)

        path_row = QHBoxLayout()
        self._path_label = QLabel("—")
        self._path_label.setWordWrap(True)
        self._browse = QPushButton("Choose RuleSet…")
        self._browse.clicked.connect(self._choose_ruleset)
        path_row.addWidget(self._path_label, 1)
        path_row.addWidget(self._browse)
        layout.addLayout(path_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_ruleset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open RuleSet", "", "JSON files (*.json)")
        if path:
            self._path_label.setText(path)

    def _accept(self) -> None:
        if self._mode.currentIndex() == 1 and (
            not self._path_label.text() or self._path_label.text() == "—"
        ):
            self._choose_ruleset()
            if self._path_label.text() == "—":
                return
        if self._mode.currentIndex() == 0:
            self._request = NewGameRequest(
                mode="generate",
                seed=self._seed.value(),
                board_size=self._board_size.value(),
                preset=self._preset.currentText(),
                hybrid=self._hybrid.isChecked(),
            )
        else:
            self._request = NewGameRequest(mode="ruleset", ruleset_path=self._path_label.text())
        self.accept()

    def request(self) -> NewGameRequest | None:
        return self._request
