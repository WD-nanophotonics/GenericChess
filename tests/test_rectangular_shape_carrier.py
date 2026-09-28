from __future__ import annotations

from fractions import Fraction

from experiments.rectangular_shape_carrier import (
    ShapeCarrier,
    synthetic_event_sequence,
    synthetic_support_edges,
)


def _legacy_square_events(n: int) -> tuple[tuple[int, int, int, int], ...]:
    events = []
    for owner in (0, 1):
        for rank in range(n):
            for file in range(n):
                if file + 1 >= n:
                    continue
                source = rank * n + file
                target = rank * n + file + 1
                effect_file, effect_rank = n - 1, n - 1
                if owner == 1:
                    effect_file, effect_rank = 0, 0
                effect = effect_rank * n + effect_file
                events.append((owner, source, target, effect))
    return tuple(events)


def _legacy_square_edges(n: int) -> tuple[tuple[int, int], ...]:
    return tuple((rank * n + file, rank * n + file + 1)
                 for rank in range(n) for file in range(n - 1))


def test_square_controls_are_event_and_enumeration_identical() -> None:
    for n in (8, 9):
        shape = ShapeCarrier(n, n)
        assert synthetic_event_sequence(shape) == _legacy_square_events(n)
        assert synthetic_support_edges(shape) == _legacy_square_edges(n)
        values = [Fraction(index + 1) for index in range(n * n)]
        assert shape.normalize(values) == sum(values, Fraction(0)) / (n * n)


def test_rectangular_coordinates_effects_support_and_area_are_shape_safe() -> None:
    shape = ShapeCarrier(3, 2)
    all_indices = [shape.to_index(file, rank)
                   for rank in range(shape.height) for file in range(shape.width)]
    assert all_indices == list(range(shape.area))
    assert [shape.from_index(index) for index in all_indices] == [
        (file, rank) for rank in range(shape.height) for file in range(shape.width)
    ]

    # Core's declared 180-degree square transform is involutive on W x H.
    for file, rank in (shape.from_index(index) for index in all_indices):
        rotated = shape.owner_square(file, rank, 1)
        assert shape.owner_square(*rotated, 1) == (file, rank)
        assert 0 <= rotated[0] < shape.width
        assert 0 <= rotated[1] < shape.height
    assert shape.offset_target(1, 0, (1, 0), 0) == (2, 0)
    assert shape.offset_target(1, 0, (1, 0), 1) == (0, 0)
    assert shape.offset_target(1, 0, (0, -1), 0) is None
    assert shape.offset_target(1, 0, (0, -1), 1) == (1, 1)

    events = synthetic_event_sequence(shape)
    edges = synthetic_support_edges(shape)
    assert events == (
        (0, 0, 1, 5), (0, 1, 2, 5), (0, 3, 4, 5), (0, 4, 5, 5),
        (1, 0, 1, 0), (1, 1, 2, 0), (1, 3, 4, 0), (1, 4, 5, 0),
    )
    assert edges == ((0, 1), (1, 2), (3, 4), (4, 5))
    assert all(0 <= square < shape.area for event in events for square in event[1:])
    assert all(0 <= square < shape.area for edge in edges for square in edge)
    drop_mask = tuple(index in (0, 5) for index in range(shape.area))
    assert [index for index, enabled in enumerate(drop_mask) if enabled] == [0, 5]

    values = [Fraction(index + 1) for index in range(shape.area)]
    assert shape.normalize(values) == Fraction(7, 2)  # denominator W*H = 6


def test_shape_identity_distinguishes_equal_area_domains() -> None:
    wide = ShapeCarrier(6, 8).identity("synthetic-ruleset")
    tall = ShapeCarrier(8, 6).identity("synthetic-ruleset")
    same_area_different_shape = ShapeCarrier(4, 12).identity("synthetic-ruleset")
    assert wide["board_area"] == tall["board_area"] == same_area_different_shape["board_area"]
    assert len({(wide["board_width"], wide["board_height"]),
                (tall["board_width"], tall["board_height"]),
                (same_area_different_shape["board_width"],
                 same_area_different_shape["board_height"])}) == 3
