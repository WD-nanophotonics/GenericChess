"""Frozen search-input envelope (Qt-free; the contained session is not copied)."""

from __future__ import annotations

from dataclasses import dataclass

from ...session.session import GameSession
from ..limits import SearchLimits


@dataclass(frozen=True, slots=True)
class SearchSnapshot:
    """Search inputs and stale-result identity captured on the GUI thread.

    This is a frozen envelope, not a deep immutable state copy: ``session`` is
    the captured GameSession object and backends must treat it as read-only.
    The worker never touches the mutable controller; stale results are rejected
    by comparing ``generation`` / ``root_key`` / ``ruleset_fingerprint`` when
    the decision is committed. A backend that needs an isolated value snapshot
    must define that contract explicitly rather than mutating this session.
    """

    session: GameSession
    limits: SearchLimits
    ruleset_fingerprint: str
    root_key: str
    generation: int
