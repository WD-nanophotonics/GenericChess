"""Opt-in, injectable audit recorder for search hot-path timing.

Normal search runs with the null recorder (zero accumulation); instrumented
audits inject :class:`TimingAuditRecorder`.  The recorder is passed through
``run_root_search(recorder=...)`` and never lives in Core.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from enum import IntEnum
from typing import Protocol


class AuditMetric(IntEnum):
    MOVE_GEN = 1
    TT_KEY = 2
    TT_PROBE_STORE = 3
    ORDERING = 4
    EVALUATION = 5
    QUIESCENCE = 6


class AuditRecorder(Protocol):
    def count(self, key: str | AuditMetric, amount: int = 1) -> None: ...

    def time_block(self, key: str | AuditMetric) -> Iterator[None]: ...


class NullAuditRecorder:
    """Zero-cost no-op recorder used by default."""

    __slots__ = ()

    def count(self, key: str | AuditMetric, amount: int = 1) -> None:
        return None

    def time_block(self, key: str | AuditMetric) -> Iterator[None]:
        return nullcontext()


class TimingAuditRecorder:
    """Accumulates per-key call counts and wall-clock totals."""

    __slots__ = ("counts", "times")

    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)
        self.times: dict[str, float] = defaultdict(float)

    def count(self, key: str | AuditMetric, amount: int = 1) -> None:
        name = key.name if isinstance(key, AuditMetric) else str(key)
        self.counts[name] += amount

    @contextmanager
    def time_block(self, key: str | AuditMetric) -> Iterator[None]:
        name = key.name if isinstance(key, AuditMetric) else str(key)
        started = time.perf_counter()
        try:
            yield
        finally:
            self.times[name] += time.perf_counter() - started

    def snapshot(self) -> dict[str, dict[str, int | float]]:
        return {
            "counts": dict(self.counts),
            "times": dict(self.times),
        }
