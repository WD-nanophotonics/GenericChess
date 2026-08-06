"""Search budget limits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchLimits:
    """Search budgets; ``None`` means unlimited for that dimension.

    ``max_nodes`` is a **total-node budget**: it counts main nodes plus
    quiescence nodes (``stats.nodes + stats.qnodes``).  Time/cancel checks are
    performed at coarse intervals (every 128 total nodes), so the effective
    budget may overshoot by at most one check interval.
    """

    max_depth: int | None = None
    max_nodes: int | None = None
    max_time_seconds: float | None = None
    quiescence_max_depth: int = 4
    quiescence_hard_max_depth: int = 8
    quiescence_max_nodes: int | None = None
    deterministic: bool = True

    def __post_init__(self) -> None:
        if self.quiescence_hard_max_depth < self.quiescence_max_depth:
            raise ValueError(
                "quiescence_hard_max_depth must be >= quiescence_max_depth "
                f"(got {self.quiescence_hard_max_depth} < {self.quiescence_max_depth})"
            )
