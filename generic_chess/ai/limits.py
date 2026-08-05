"""Search budget limits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchLimits:
    """Search budgets; ``None`` means unlimited for that dimension."""

    max_depth: int | None = None
    max_nodes: int | None = None
    max_time_seconds: float | None = None
    quiescence_max_depth: int = 4
    quiescence_max_nodes: int | None = None
    deterministic: bool = True
