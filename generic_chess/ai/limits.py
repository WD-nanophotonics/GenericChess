"""Search budget limits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchLimits:
    """Search budgets; ``None`` means unlimited for that dimension.

    ``max_nodes`` is a **total-node budget**: it counts main nodes plus
    quiescence nodes (``stats.nodes + stats.qnodes``). Node limits are checked
    at search boundaries and cooperative semantic checkpoints. A supplied
    deadline or cancellation token enables prompt polling; fixed-node work
    avoids clock polling. An indivisible work unit can delay a wall-clock stop,
    so the time limit is cooperative rather than a strict execution deadline.
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
