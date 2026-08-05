"""Qt-free match configuration for Human vs AI games."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..ai.budget import ThinkingConfig
from ..clock import TimeControl


class ParticipantKind(StrEnum):
    HUMAN = "human"
    AI = "ai"


@dataclass(frozen=True, slots=True)
class MatchConfig:
    """Per-side participants, the time control and the AI thinking config."""

    participants: tuple[ParticipantKind, ParticipantKind]
    time_control: TimeControl
    ai_config: ThinkingConfig
