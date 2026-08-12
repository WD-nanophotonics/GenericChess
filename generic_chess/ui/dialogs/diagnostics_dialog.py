"""Diagnostics dialog: developer information moved out of the main UI."""

from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Qt, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ...core.identity import position_identity_key
from ..controller import UIController
from ..i18n.manager import LocalizationManager


class DiagnosticsDialog(QDialog):
    def __init__(
        self,
        controller: UIController,
        tr: LocalizationManager,
        app_version: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._tr = tr
        self._app_version = app_version
        self.setWindowTitle(tr.text("diagnostics.title"))
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._labels: dict[str, QLabel] = {}
        rows = (
            "diagnostics.app_version",
            "diagnostics.ruleset_fingerprint",
            "diagnostics.ruleset_seed",
            "diagnostics.ruleset_file",
            "diagnostics.record_file",
            "diagnostics.position_key",
            "diagnostics.ply",
            "diagnostics.backend",
            "diagnostics.native_available",
            "diagnostics.native_version",
            "diagnostics.python_version",
            "diagnostics.qt_version",
        )
        for key in rows:
            label = QLabel("—")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(tr.text(key), label)
            self._labels[key] = label
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self._copy_btn = QPushButton(tr.text("diagnostics.copy"))
        self._copy_btn.clicked.connect(self._copy)
        buttons.addWidget(self._copy_btn)
        close_btn = QPushButton(tr.text("dialog.close"))
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        tr = self._tr
        controller = self._controller
        compiled = controller.compiled
        session = controller.session
        info = controller.game_info()
        try:
            from ...native import native_available, native_version
        except Exception:  # pragma: no cover
            native_available = lambda: False  # type: ignore[assignment]
            native_version = lambda: "unavailable"  # type: ignore[assignment]
        values = {
            "diagnostics.app_version": self._app_version,
            "diagnostics.ruleset_fingerprint": (
                compiled.ruleset_fingerprint if compiled is not None else "—"
            ),
            "diagnostics.ruleset_seed": (
                str(info.seed) if info is not None and info.seed is not None else "—"
            ),
            "diagnostics.ruleset_file": (
                info.ruleset_path if info is not None and info.ruleset_path else "—"
            ),
            "diagnostics.record_file": (
                info.record_path if info is not None and info.record_path else "—"
            ),
            "diagnostics.position_key": (
                position_identity_key(session.state.position, compiled)
                if session is not None and compiled is not None
                else "—"
            ),
            "diagnostics.ply": (
                str(session.state.ply_count) if session is not None else "—"
            ),
            "diagnostics.backend": "python + native" if native_available() else "python",
            "diagnostics.native_available": (
                "yes" if native_available() else "no"
            ),
            "diagnostics.native_version": native_version(),
            "diagnostics.python_version": sys.version.split()[0],
            "diagnostics.qt_version": qVersion(),
        }
        for key, value in values.items():
            self._labels[key].setText(str(value))

    def _copy(self) -> None:
        lines = [f"{self._tr.text(k)}: {self._labels[k].text()}" for k in self._labels]
        QGuiApplication.clipboard().setText("\n".join(lines))
