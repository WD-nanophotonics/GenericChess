"""Human-readable error dialog with expandable technical details."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


def show_error(parent, title: str, message: str, details: str | None = None) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    label = QLabel(message)
    label.setWordWrap(True)
    layout.addWidget(label)
    if details:
        text = QPlainTextEdit()
        text.setPlainText(details)
        text.setReadOnly(True)
        text.setMaximumHeight(180)
        layout.addWidget(text)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()


def show_info(parent, title: str, message: str) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    label = QLabel(message)
    label.setWordWrap(True)
    layout.addWidget(label)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()
