from itertools import product
from fractions import Fraction

import pytest

from scripts.audit_static_semantic_material_prior_v2c import finite_population_union_probability
from scripts.static_path_count_one_event import (
    cubes_are_pairwise_disjoint,
    path_count_one_cubes,
)


def _cube_matches(cube, assignment):
    return all(assignment[index] in labels for index, labels in cube)


def test_one_screen_cubes_match_truth_table_and_are_disjoint():
    path = (0, 1)
    target = 2
    cubes = path_count_one_cubes(path, target)

    assert cubes_are_pairwise_disjoint(cubes)
    for values in product(("empty", "own", "enemy"), repeat=3):
        assignment = dict(enumerate(values))
        expected = (
            sum(assignment[index] != "empty" for index in path) == 1
            and assignment[target] == "enemy"
        )
        assert any(_cube_matches(cube, assignment) for cube in cubes) is expected


def test_one_screen_cubes_have_exact_v2c_fixed_population_probability():
    cubes = path_count_one_cubes((0, 1), 2)
    assert finite_population_union_probability(
        cubes,
        empty_count=2,
        own_count=1,
        enemy_count=2,
    ) == Fraction(4, 15)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"predicate_kind": "path_clear"},
        {"count": 2},
        {"owner_filter": "self"},
    ),
)
def test_unsupported_predicate_variants_fail_closed(kwargs):
    with pytest.raises(ValueError):
        path_count_one_cubes((0, 1), 2, **kwargs)


@pytest.mark.parametrize(
    "path,target",
    (
        ((0, 0), 2),
        ((0, 1), 1),
    ),
)
def test_ambiguous_or_overlapping_indices_fail_closed(path, target):
    with pytest.raises(ValueError):
        path_count_one_cubes(path, target)
