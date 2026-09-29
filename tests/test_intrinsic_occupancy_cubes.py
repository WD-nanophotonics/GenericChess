from fractions import Fraction

import pytest

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.audit_static_semantic_material_prior_v2c import finite_population_union_probability
from scripts.intrinsic_occupancy_cubes import intersect_cubes, path_count_eq_cubes


def test_xiangqi_cannon_one_screen_has_exact_finite_population_event():
    compiled = compile_semantic_ruleset(build_xiangqi_diagnostic_ruleset())
    cannon = next(pattern for pattern in compiled.ir.patterns
                  if pattern.name == "cannon_capture_one_screen")
    assert [(predicate.kind, predicate.count, predicate.owner_filter)
            for predicate in cannon.path] == [("path_count_eq", 1, "any")]
    geometry = compiled.ir.geometry[cannon.geometry_ids[0]]
    source = 4 * compiled.support.board_shape.width + 4
    path = next(path for _target, path in geometry_candidates(geometry, "0", source)
                if len(path) == 2)
    cubes = path_count_eq_cubes(path, 1)
    assert len(cubes) == 2
    assert finite_population_union_probability(
        cubes, empty_count=2, own_count=1, enemy_count=1
    ) == Fraction(2, 3)


def test_path_count_events_partition_and_fail_closed():
    path = (10, 11)
    probabilities = [finite_population_union_probability(
        path_count_eq_cubes(path, count), empty_count=2, own_count=1, enemy_count=1
    ) for count in range(3)]
    assert probabilities == [Fraction(1, 6), Fraction(2, 3), Fraction(1, 6)]
    assert sum(probabilities) == 1
    assert path_count_eq_cubes(path, 3) == ()
    with pytest.raises(ValueError, match="owner filter"):
        path_count_eq_cubes(path, 1, owner_filter="enemy")
    with pytest.raises(ValueError, match="budget"):
        path_count_eq_cubes(tuple(range(12)), 6)


def test_cannon_screen_cubes_compose_with_enemy_target():
    target_enemy = ((12, ("enemy",)),)
    cubes = tuple(intersect_cubes(cube, target_enemy)
                  for cube in path_count_eq_cubes((10, 11), 1))
    assert None not in cubes
    assert finite_population_union_probability(
        cubes, empty_count=2, own_count=1, enemy_count=2
    ) == Fraction(4, 15)
    assert intersect_cubes(((10, ("empty",)),), ((10, ("enemy",)),)) is None
