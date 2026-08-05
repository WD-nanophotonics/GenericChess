"""Centralized keyboard shortcut definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Shortcut:
    action: str
    keys: str
    description: str


SHORTCUTS: tuple[Shortcut, ...] = (
    Shortcut("New Game", "Ctrl+N", "Start a new game"),
    Shortcut("Open", "Ctrl+O", "Open a RuleSet or Record"),
    Shortcut("Save Record", "Ctrl+S", "Save the current record"),
    Shortcut("Save Record As", "Ctrl+Shift+S", "Save the record to a new file"),
    Shortcut("Undo", "Ctrl+Z", "Undo the last move"),
    Shortcut("Redo", "Ctrl+Y", "Redo the last undone move"),
    Shortcut("Cancel selection", "Esc", "Clear selection / preview / drop state"),
    Shortcut("Flip board", "F", "Flip the board orientation"),
    Shortcut("Preferences", "Ctrl+,", "Open preferences"),
    Shortcut("Full screen", "F11", "Toggle full screen"),
)
