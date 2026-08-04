"""Repetition-count bookkeeping."""

from __future__ import annotations


def update_repetition_counts(
    counts: tuple[tuple[str, int], ...], position_key: str
) -> tuple[tuple[str, int], ...]:
    """Return a new sorted counts tuple with ``position_key`` incremented."""
    d = dict(counts)
    d[position_key] = d.get(position_key, 0) + 1
    return tuple(sorted(d.items()))


def is_repetition_draw(counts: tuple[tuple[str, int], ...], limit: int) -> bool:
    return any(count >= limit for _, count in counts)
