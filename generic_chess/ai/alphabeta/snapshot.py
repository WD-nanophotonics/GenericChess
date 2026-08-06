"""Frozen search-input snapshot (Qt-free)."""

from __future__ import annotations

from dataclasses import dataclass

from ...session.session import GameSession
from ..limits import SearchLimits


@dataclass(frozen=True, slots=True)
class SearchSnapshot:
    """Everything a worker needs to run one search, frozen on the GUI thread.

    The worker only reads this snapshot and never touches the mutable
    controller; stale results are rejected by comparing ``generation`` /
    ``root_key`` / ``ruleset_fingerprint`` when the decision is committed.
    """

    session: GameSession
    limits: SearchLimits
    ruleset_fingerprint: str
    root_key: str
    generation: int
