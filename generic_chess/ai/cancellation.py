"""Cooperative cancellation token."""

from __future__ import annotations


class CancellationToken:
    """Simple cooperative cancellation flag (never used for normal control flow)."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled
