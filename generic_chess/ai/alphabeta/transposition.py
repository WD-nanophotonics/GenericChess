"""Bounded transposition table with mate-score normalization."""

from __future__ import annotations

from enum import Enum, auto
from typing import Hashable

from ...core.actions import Action
from ..evaluation.config import MATE_THRESHOLD


class BoundType(Enum):
    EXACT = auto()
    LOWER = auto()
    UPPER = auto()


class TTEntry:
    __slots__ = ("key", "depth", "score", "bound", "best_action", "generation")

    def __init__(
        self,
        key: Hashable,
        depth: int,
        score: int,
        bound: BoundType,
        best_action: Action | None,
        generation: int,
    ) -> None:
        self.key = key
        self.depth = depth
        self.score = score
        self.bound = bound
        self.best_action = best_action
        self.generation = generation


def score_to_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score + ply
    if score <= -MATE_THRESHOLD:
        return score - ply
    return score


def score_from_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score - ply
    if score <= -MATE_THRESHOLD:
        return score + ply
    return score


class TranspositionTable:
    """Bounded TT with generation + depth-preferred replacement.

    When full, entries from older generations are evicted first; if all
    entries share the current generation, a batch is evicted (documented v1
    policy instead of clearing the whole table unconditionally).
    """

    def __init__(self, max_entries: int = 250_000) -> None:
        self._max_entries = max(1, max_entries)
        self._data: dict[Hashable, TTEntry] = {}
        self._generation = 0

    def new_generation(self) -> None:
        self._generation += 1

    @property
    def generation(self) -> int:
        return self._generation

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        self._data.clear()

    def probe(self, key: Hashable, depth: int) -> TTEntry | None:
        entry = self._data.get(key)
        if entry is not None and entry.depth >= depth:
            return entry
        return None

    def store(
        self,
        key: Hashable,
        depth: int,
        score: int,
        bound: BoundType,
        best_action: Action | None,
    ) -> None:
        existing = self._data.get(key)
        if existing is not None:
            if depth >= existing.depth or self._generation > existing.generation:
                existing.depth = depth
                existing.score = score
                existing.bound = bound
                existing.best_action = best_action
                existing.generation = self._generation
            return
        if len(self._data) >= self._max_entries:
            self._evict()
        self._data[key] = TTEntry(key, depth, score, bound, best_action, self._generation)

    def _evict(self) -> None:
        old = [k for k, e in self._data.items() if e.generation < self._generation]
        if old:
            for k in old[: max(1, len(old) // 2)]:
                self._data.pop(k, None)
            return
        # All entries belong to the current search: evict a batch (v1 policy).
        for k in list(self._data)[: max(1, len(self._data) // 4)]:
            self._data.pop(k, None)
