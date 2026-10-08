"""Geometry-only capability dimensions; not semantic material calibration."""
from dataclasses import replace

import pytest

from generic_chess.ai.evaluation.analyzer import build_movement_capability, movement_signature
from generic_chess.ai.evaluation.cache import MovementCapabilityCache
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.mobility import (
    analytic_mobility_at_density, monte_carlo_mobility_at_density, mobility_density_curve,
)
from generic_chess.ai.evaluation.movement_graph import graph_metrics
from generic_chess.core.coordinates import BoardShape
from generic_chess.core.movement import LeapAtom, RayAtom


@pytest.mark.parametrize('shape', [BoardShape(7, 5), BoardShape(9, 10), BoardShape(1, 5)])
def test_single_leap_closed_form(shape):
    atoms = (LeapAtom((3, 2)),)
    valid = max(0, shape.width - 3) * max(0, shape.height - 2)
    for density in (0.0, 0.25, 1.0):
        assert analytic_mobility_at_density(shape, atoms, density) == pytest.approx(
            valid / shape.area * (1 - density / 2))
    profile = build_movement_capability(shape, atoms, EvaluationConfig())
    assert profile.empty_board_mobility == valid / shape.area
    assert profile.coverage_ratio == valid / shape.area


def test_directed_horizontal_graph_closed_form():
    shape = BoardShape(9, 5)
    graph = graph_metrics(shape, (RayAtom((1, 0)),))
    assert graph.average_out_degree == 4
    assert graph.reachable_pair_ratio == 180 / (45 * 44)
    assert graph.average_shortest_path == 1
    assert graph.diameter == 1
    assert graph.largest_component_ratio == 1 / 45
    # Equal area is insufficient: orientation has distinct geometry.
    transposed = graph_metrics(BoardShape(5, 9), (RayAtom((1, 0)),))
    assert transposed.average_out_degree == 2


def test_hybrid_sampling_deduplicates_rectangular_targets():
    shape = BoardShape(7, 5)
    atoms = (RayAtom((1, 0)), LeapAtom((2, 0)), LeapAtom((0, 1)))
    signature = movement_signature(atoms)
    # Horizontal ray already contains the two-step leap; vertical leap is new.
    expected_empty = (5 * 21 + 7 * 4) / 35
    empty = monte_carlo_mobility_at_density(shape, atoms, 0, signature, 'test', 4)
    assert empty == expected_empty
    args = (shape, atoms, 0.5, signature, 'test', 64)
    sampled = monte_carlo_mobility_at_density(*args)
    assert sampled == monte_carlo_mobility_at_density(*args)
    assert 0 < sampled < empty


@pytest.mark.parametrize('atoms', [
    (LeapAtom((0, 1)),),
    (RayAtom((1, 1)),),
    (RayAtom((1, 0)), LeapAtom((2, 0))),
])
def test_square_integer_and_shape_are_identical(atoms):
    config = EvaluationConfig(mc_samples=16)
    a = build_movement_capability(5, atoms, config)
    b = build_movement_capability(BoardShape(5, 5), atoms, config)
    assert a == b
    cache = MovementCapabilityCache()
    assert not cache.get_or_build(5, atoms, config)[1]
    cached, hit = cache.get_or_build(BoardShape(5, 5), atoms, config)
    assert hit and cached == a


def test_cache_separates_rectangular_dimensions_and_config():
    config = EvaluationConfig(mc_samples=8)
    cache = MovementCapabilityCache()
    atoms = (RayAtom((1, 0)),)
    wide, hit = cache.get_or_build(BoardShape(9, 5), atoms, config)
    assert not hit
    tall, hit = cache.get_or_build(BoardShape(5, 9), atoms, config)
    assert not hit and wide != tall
    assert cache.get_or_build(BoardShape(9, 5), atoms, config) == (wide, True)
    assert not cache.get_or_build(BoardShape(9, 5), atoms, replace(config, mc_samples=9))[1]


@pytest.mark.parametrize('density', [0.0, 0.25, 0.5, 1.0])
def test_exact_analytic_union_of_ray_and_overlapping_leaps(density):
    shape = BoardShape(3, 2)
    atoms = (RayAtom((1, 0)), LeapAtom((2, 0)), LeapAtom((0, 1)))
    # Two horizontal target distances are available from the left file;
    # the long leap bypasses the sole intermediate blocker. There are six
    # horizontal and three vertical destinations over all starting squares.
    assert analytic_mobility_at_density(shape, atoms, density) == pytest.approx(
        1.5 * (1 - density / 2))


@pytest.mark.parametrize('shape', [BoardShape(3, 2), BoardShape(7, 5), BoardShape(9, 10)])
def test_exact_analytic_is_invariant_to_saturation_and_redundancy(shape):
    ray = RayAtom((1, 0))
    variants = [
        (ray,), (RayAtom((1, 0), shape.width - 1),),
        (ray, ray), (ray, LeapAtom((1, 0))),
    ]
    for density in (0.0, 0.25, 0.5, 1.0):
        values = [analytic_mobility_at_density(shape, atoms, density) for atoms in variants]
        assert values == pytest.approx([values[0]] * len(values), abs=1e-12)
    # A two-step leap is not redundant when its intermediate square can block.
    assert analytic_mobility_at_density(shape, (ray, LeapAtom((2, 0))), 0.5) > (
        analytic_mobility_at_density(shape, (ray,), 0.5))


def test_non_axis_primitive_ray_counts_landings_not_manhattan_distance():
    shape = BoardShape(5, 3)
    ray = (RayAtom((2, 1)),)
    ordinary = analytic_mobility_at_density(shape, ray, 0.5)
    redundant = analytic_mobility_at_density(shape, (*ray, LeapAtom((2, 1))), 0.5)
    bypass = analytic_mobility_at_density(shape, (*ray, LeapAtom((4, 2))), 0.5)
    # Six first landings and one second landing, with exactly one blocker
    # before the second. Only source(0,0) reaches endpoint(4,2).
    assert ordinary == pytest.approx((6 * 0.75 + 0.375) / 15)
    assert redundant == ordinary
    assert bypass == pytest.approx(7 * 0.75 / 15)


def test_default_curve_does_not_sample_equivalent_encodings(monkeypatch):
    import generic_chess.ai.evaluation.mobility as module

    def forbidden(*args, **kwargs):
        raise AssertionError('default independent occupancy is exact')

    monkeypatch.setattr(module, 'monte_carlo_mobility_at_density', forbidden)
    shape = BoardShape(5, 3)
    atoms = (RayAtom((2, 1)), LeapAtom((2, 1)))
    a = mobility_density_curve(shape, atoms, (0.0, 0.5, 1.0),
                               signature='first', version='a', mc_samples=1)
    b = mobility_density_curve(shape, (*atoms, *atoms), (0.0, 0.5, 1.0),
                               signature='second', version='b', mc_samples=999)
    assert a == b
    assert a[1] == pytest.approx(0.325)


def test_default_profile_version_is_exact_generation():
    assert EvaluationConfig().evaluator_version == 'generic-v2'


@pytest.mark.parametrize('shape', [5, BoardShape(5, 3)])
def test_duplicate_atoms_cannot_make_same_key_cache_order_dependent(shape):
    cfg = EvaluationConfig()
    balanced = (LeapAtom((0, 1)), LeapAtom((0, -1)))
    duplicated = (*balanced, balanced[0])
    direct = [build_movement_capability(shape, atoms, cfg)
              for atoms in (balanced, duplicated)]
    assert direct[0] == direct[1]
    assert direct[0].directional_asymmetry == 0
    for order in ((balanced, duplicated), (duplicated, balanced)):
        cache = MovementCapabilityCache()
        first, hit = cache.get_or_build(shape, order[0], cfg)
        assert not hit
        second, hit = cache.get_or_build(shape, order[1], cfg)
        assert hit and first == second == direct[0]


def test_redundant_ray_leap_preserves_behavioral_asymmetry():
    cfg = EvaluationConfig()
    atoms = (RayAtom((0, 1)), LeapAtom((0, -1)))
    base = build_movement_capability(BoardShape(5, 3), atoms, cfg)
    redundant = build_movement_capability(BoardShape(5, 3), (*atoms, LeapAtom((0, 1))), cfg)
    assert base.directional_asymmetry == redundant.directional_asymmetry
    assert base.directional_asymmetry == pytest.approx(0.2)
