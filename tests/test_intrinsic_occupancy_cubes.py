from fractions import Fraction

import pytest

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.audit_static_semantic_material_prior_v2c import (
    _event_measure_factory, _source_joint_counts, _token_state_ledger,
    finite_population_union_probability,
)
from scripts.intrinsic_occupancy_cubes import (
    empty_exact_guard_cube, intersect_cubes, path_count_eq_cubes,
    square_zone_guard_holds,
)


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


def test_xiangqi_horse_and_elephant_blocker_guards_are_empty_cubes():
    compiled = compile_semantic_ruleset(build_xiangqi_diagnostic_ruleset())
    shape = compiled.support.board_shape
    source = 4 * shape.width + 4
    blocker_patterns = [row for row in compiled.ir.patterns
                        if row.name.startswith(("horse_", "elephant_")) and row.guards]
    assert len(blocker_patterns) == 24
    for pattern in blocker_patterns:
        assert len(pattern.guards) == 1
        first = empty_exact_guard_cube(pattern.guards[0], owner=0,
                                       source=source, target=source + 1,
                                       path=(), board_shape=shape)
        second = empty_exact_guard_cube(pattern.guards[0], owner=1,
                                        source=source, target=source - 1,
                                        path=(), board_shape=shape)
        assert first is not None and second is not None
        assert first[0][0] != second[0][0]  # owner-relative leg/eye offset mirrors
        assert first[0][1] == second[0][1] == ("empty",)

    facing = next(row for row in compiled.ir.patterns if row.name == "general_facing_capture")
    with pytest.raises(ValueError, match="unsupported exact occupancy guard"):
        empty_exact_guard_cube(facing.guards[0], owner=0, source=source,
                               target=source + 1, path=(), board_shape=shape)


def test_xiangqi_palace_and_river_zone_guards_mirror_by_owner():
    compiled = compile_semantic_ruleset(build_xiangqi_diagnostic_ruleset())
    width = compiled.support.board_shape.width
    palace = next(row for row in compiled.ir.patterns if row.name == "g_empty")
    assert len(palace.square_zone_guards) == 2
    assert all(square_zone_guard_holds(compiled, guard, owner=0,
                                       source=width + 4, target=2 * width + 4,
                                       path=()) for guard in palace.square_zone_guards)
    assert all(square_zone_guard_holds(compiled, guard, owner=1,
                                       source=8 * width + 4, target=7 * width + 4,
                                       path=()) for guard in palace.square_zone_guards)
    assert not square_zone_guard_holds(compiled, palace.square_zone_guards[1],
                                       owner=0, source=width + 4,
                                       target=3 * width + 4, path=())

    elephant = next(row for row in compiled.ir.patterns
                    if row.name == "elephant_1_1_empty")
    assert square_zone_guard_holds(compiled, elephant.square_zone_guards[0],
                                   owner=0, source=4 * width + 4,
                                   target=6 * width + 6, path=())
    assert not square_zone_guard_holds(compiled, elephant.square_zone_guards[1],
                                       owner=0, source=4 * width + 4,
                                       target=6 * width + 6, path=())


def test_compiled_xiangqi_cannon_capture_event_matches_hypergeometric_formula():
    compiled = compile_semantic_ruleset(build_xiangqi_diagnostic_ruleset())
    ledger = _token_state_ledger(compiled)
    assert ledger["complete"]
    cannon = next(row for row in compiled.ir.patterns
                  if row.name == "cannon_capture_one_screen")
    width = compiled.support.board_shape.width
    source = 4 * width + 4
    target, path = next((target, path) for target, path in
                        geometry_candidates(compiled.ir.geometry[cannon.geometry_ids[0]],
                                            "0", source) if len(path) == 2)
    cubes = tuple(intersect_cubes(cube, ((target, ("enemy",)),))
                  for cube in path_count_eq_cubes(path, 1))
    measured = _event_measure_factory(ledger, compiled, "C")(0, "C", list(cubes))

    remaining = ledger["board_square_count"] - 1
    analytic = sum((mass * Fraction(enemy, remaining)
                    * 2 * Fraction(own + enemy - 1, remaining - 1)
                    * Fraction(empty, remaining - 2)
                    for (empty, own, enemy), mass in
                    _source_joint_counts(ledger, 0, source_is_anchor=False).items()), Fraction(0))
    assert measured == analytic == Fraction(2426, 85173)
