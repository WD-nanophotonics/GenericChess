from dataclasses import replace
from fractions import Fraction
from itertools import product
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.audit_static_semantic_material_prior_v2c import finite_population_union_probability
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from scripts.static_path_count_one_event import (
    compiled_path_count_one_cubes,
    cubes_are_pairwise_disjoint,
    path_count_one_cubes,
)
from rule_semantics_ir_fixtures import cannon_ruleset


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


def test_compiled_ir_candidate_maps_to_same_two_screen_cubes_and_probability():
    compiled = compile_semantic_ruleset(cannon_ruleset())
    pattern = next(
        pattern for pattern in compiled.ir.patterns
        if pattern.pattern_id == "sem_01_cannon_capture"
    )
    cubes = compiled_path_count_one_cubes(
        pattern,
        compiled.ir.geometry,
        owner="0",
        source=0,
        target=3,
        board_area=64,
    )

    assert cubes == path_count_one_cubes((1, 2), 3)
    assert cubes_are_pairwise_disjoint(cubes)
    for values in product(("empty", "own", "enemy"), repeat=3):
        assignment = dict(zip((1, 2, 3), values))
        expected = (
            sum(assignment[index] != "empty" for index in (1, 2)) == 1
            and assignment[3] == "enemy"
        )
        assert any(_cube_matches(cube, assignment) for cube in cubes) is expected

    assert finite_population_union_probability(
        cubes,
        empty_count=2,
        own_count=1,
        enemy_count=2,
    ) == Fraction(4, 15)


def test_compiled_adapter_fails_closed_for_bad_target_or_index_domain():
    compiled = compile_semantic_ruleset(cannon_ruleset())
    pattern = next(
        pattern for pattern in compiled.ir.patterns
        if pattern.pattern_id == "sem_01_cannon_capture"
    )
    args = (pattern, compiled.ir.geometry)
    with pytest.raises(ValueError):
        compiled_path_count_one_cubes(
            *args, owner="0", source=0, target=63, board_area=64,
        )
    with pytest.raises(ValueError):
        compiled_path_count_one_cubes(
            *args, owner="0", source=0, target=3, board_area=3,
        )

    bad_predicate = replace(pattern.path[0], owner_filter="self")
    with pytest.raises(ValueError):
        compiled_path_count_one_cubes(
            replace(pattern, path=(bad_predicate,)),
            compiled.ir.geometry,
            owner="0",
            source=0,
            target=3,
            board_area=64,
        )

    bad_target = replace(pattern, target=replace(pattern.target, kind="target_empty"))
    with pytest.raises(ValueError):
        compiled_path_count_one_cubes(
            bad_target,
            compiled.ir.geometry,
            owner="0",
            source=0,
            target=3,
            board_area=64,
        )

    geometry_id = next(
        geometry_id
        for geometry_id in pattern.geometry_ids
        if any(
            candidate_target == 3 and len(path) == 2
            for candidate_target, path in geometry_candidates(
                compiled.ir.geometry[geometry_id], "0", 0
            )
        )
    )
    geometry = compiled.ir.geometry[geometry_id]
    malformed_paths = {
        owner: dict(per_source) for owner, per_source in geometry.paths.items()
    }
    malformed_paths["0"][0] = (64, 2, 3, 4, 5, 6, 7)
    bad_geometries = dict(compiled.ir.geometry)
    bad_geometries[geometry_id] = replace(geometry, paths=malformed_paths)
    with pytest.raises(ValueError):
        compiled_path_count_one_cubes(
            pattern,
            bad_geometries,
            owner="0",
            source=0,
            target=3,
            board_area=64,
        )


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
