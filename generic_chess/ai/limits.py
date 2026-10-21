"""Search budget limits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral


@dataclass(frozen=True, slots=True)
class SearchLimits:
    """Search budgets with field-specific ``None`` behavior.

    ``max_depth=None`` selects AlphaBeta's default maximum depth (64); the
    Native engine requires an explicit supported depth. ``None`` means no
    limit for ``max_nodes``, ``max_time_seconds`` and
    ``quiescence_max_nodes``.

    ``deterministic`` is retained as compatibility metadata; current search
    backends do not consume it.

    ``max_nodes`` is a **total-node budget**: it counts main nodes plus
    quiescence nodes (``stats.nodes + stats.qnodes``). Node limits are checked
    at search boundaries and cooperative semantic checkpoints. A supplied
    deadline or cancellation token enables prompt polling; fixed-node work
    avoids clock polling. An indivisible work unit can delay a wall-clock stop,
    so the time limit is cooperative rather than a strict execution deadline.

    ``quiescence_max_nodes`` is checked when further q expansion is needed,
    after terminal, stand-pat and ordinary-depth exits. It is not a strict
    ceiling on q visits: the first-iteration ordinary-q0 reserve can finish
    several quiet leaves after that count. Use ``max_nodes`` to bound all
    main-plus-q visits, independently of q expansion policy.
    """

    max_depth: int | None = None
    max_nodes: int | None = None
    max_time_seconds: float | None = None
    quiescence_max_depth: int = 4
    quiescence_hard_max_depth: int = 8
    quiescence_max_nodes: int | None = None
    deterministic: bool = True

    def __post_init__(self) -> None:
        integer_fields = (
            ("max_depth", self.max_depth, True),
            ("max_nodes", self.max_nodes, True),
            ("quiescence_max_depth", self.quiescence_max_depth, False),
            ("quiescence_hard_max_depth", self.quiescence_hard_max_depth, False),
            ("quiescence_max_nodes", self.quiescence_max_nodes, True),
        )
        for name, value, optional in integer_fields:
            if optional and value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise ValueError(f"{name} must be an integer")
        if self.max_depth is not None and self.max_depth < 0:
            raise ValueError("max_depth must be >= 0; use None for the default depth")
        if self.max_nodes is not None and self.max_nodes < 0:
            raise ValueError("max_nodes must be >= 0; use None for no node limit")
        if self.quiescence_max_depth < 0:
            raise ValueError(
                "quiescence_max_depth must be >= 0; use 0 to disable ordinary qsearch"
            )
        if self.max_time_seconds is not None:
            try:
                valid_time_limit = (
                    not isinstance(self.max_time_seconds, bool)
                    and math.isfinite(self.max_time_seconds)
                    and self.max_time_seconds >= 0
                )
            except (OverflowError, TypeError, ValueError):
                valid_time_limit = False
            if not valid_time_limit:
                raise ValueError(
                    "max_time_seconds must be a finite non-negative number; "
                    "use None for no time limit"
                )
        if self.quiescence_hard_max_depth < self.quiescence_max_depth:
            raise ValueError(
                "quiescence_hard_max_depth must be >= quiescence_max_depth "
                f"(got {self.quiescence_hard_max_depth} < {self.quiescence_max_depth})"
            )
        if self.quiescence_max_nodes is not None and self.quiescence_max_nodes < 0:
            raise ValueError(
                "quiescence_max_nodes must be >= 0; use None for no qsearch node limit"
            )
