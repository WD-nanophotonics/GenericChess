"""Pure coordinate/area carrier prototype; no RuleSet or material calculation."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from generic_chess.core.coordinates import (
    BoardShape,
    Offset,
    Square,
    relative_to_absolute,
    rotate_square,
)


@dataclass(frozen=True)
class ShapeCarrier:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("board dimensions must be positive")

    @property
    def shape(self) -> BoardShape:
        return BoardShape(self.width, self.height)

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_index(self, file: int, rank: int) -> int:
        if not (0 <= file < self.width and 0 <= rank < self.height):
            raise ValueError("coordinate outside board shape")
        return rank * self.width + file

    def from_index(self, index: int) -> tuple[int, int]:
        if not 0 <= index < self.area:
            raise ValueError("source index outside board area")
        return index % self.width, index // self.width

    def owner_square(self, file: int, rank: int, owner: int) -> tuple[int, int]:
        if owner not in (0, 1):
            raise ValueError("owner must be 0 or 1")
        square = Square(file, rank)
        if owner == 1:
            square = rotate_square(square, self.shape)
        return square.file, square.rank

    def offset_target(self, file: int, rank: int, offset: Offset,
                      owner: int) -> tuple[int, int] | None:
        if owner not in (0, 1):
            raise ValueError("owner must be 0 or 1")
        df, dr = relative_to_absolute(offset, owner)
        target = (file + df, rank + dr)
        if not (0 <= target[0] < self.width and 0 <= target[1] < self.height):
            return None
        return target

    def normalize(self, values: Iterable[Fraction]) -> Fraction:
        items = tuple(Fraction(value) for value in values)
        if len(items) != self.area:
            raise ValueError("source vector length must equal width * height")
        return sum(items, Fraction(0)) / self.area

    def identity(self, ruleset_fingerprint: str) -> dict[str, object]:
        if not ruleset_fingerprint:
            raise ValueError("RuleSet fingerprint is required")
        return {
            "ruleset_fingerprint": ruleset_fingerprint,
            "board_width": self.width,
            "board_height": self.height,
            "board_area": self.area,
            "index_convention": "rank-major: rank * width + file",
        }


def synthetic_event_sequence(shape: ShapeCarrier) -> tuple[tuple[int, int, int, int], ...]:
    """Enumerate a fixed right-step geometry and owner-relative far-corner effect."""
    events = []
    for owner in (0, 1):
        for rank in range(shape.height):
            for file in range(shape.width):
                if file + 1 >= shape.width:
                    continue
                target = shape.to_index(file + 1, rank)
                effect_file, effect_rank = shape.owner_square(
                    shape.width - 1, shape.height - 1, owner)
                events.append((owner, shape.to_index(file, rank), target,
                               shape.to_index(effect_file, effect_rank)))
    return tuple(events)


def synthetic_support_edges(shape: ShapeCarrier) -> tuple[tuple[int, int], ...]:
    return tuple(
        (shape.to_index(file, rank), shape.to_index(file + 1, rank))
        for rank in range(shape.height)
        for file in range(shape.width - 1)
    )
