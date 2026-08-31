"""GameSession: the stateful session layer for UI, human and future AI players.

This layer sits between the deterministic Core kernel and any interactive
front end (currently the minimal CLI).  It only uses Core's public semantics:
``legal_actions``, ``apply_action``, ``terminal_result`` and ``position_key``.
"""

from .record import ActionRecord, GameRecord
from .result import SessionResult, SessionStatus
from .serialization import deserialize_game_record, serialize_game_record
from ..core.declarations import (
    DeclarationAssessment,
    InvalidDeclarationError,
    assess_declaration,
    available_declarations,
)
from .session import (
    GameSession,
    SessionFinishedError,
    SessionRecordError,
)

__all__ = [
    "GameSession",
    "ActionRecord",
    "GameRecord",
    "SessionResult",
    "SessionStatus",
    "SessionFinishedError",
    "SessionRecordError",
    "serialize_game_record",
    "deserialize_game_record",
    "DeclarationAssessment",
    "InvalidDeclarationError",
    "assess_declaration",
    "available_declarations",
]
