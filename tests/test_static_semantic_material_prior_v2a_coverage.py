from __future__ import annotations

from collections import Counter
from dataclasses import replace
import re
from types import SimpleNamespace

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts import audit_static_semantic_material_prior_v2a_coverage as coverage


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def test_current_builder_coverage_is_fingerprint_bound_and_value_free():
    result = coverage.audit_current_builders()

    assert result["kind"] == "STATIC_MATERIAL_PRIOR_V2A_SCOPED_COVERAGE_ONLY"
    assert result["scope_contract"] == "INTRINSIC_BOARD_SEMANTICS"
    assert result["generator"]["version"] == coverage.GENERATOR_VERSION
    assert re.fullmatch(r"[0-9a-f]{64}", result["generator"]["source_sha256"])
    assert set(result["rulesets"]) == {
        "western_chess", "standard_shogi", "xiangqi_diagnostic"
    }

    exclusion_families = set()
    for name, row in result["rulesets"].items():
        assert row["ruleset_name"] == name
        assert re.fullmatch(r"[0-9a-f]{64}", row["ruleset_fingerprint"])
        assert row["scope_contract"] == "INTRINSIC_BOARD_SEMANTICS"
        assert row["inventory_complete"]
        assert row["IN_SCOPE_MODELED"]
        assert row["OUT_OF_SCOPE_EXPLICIT"]
        for exclusion in row["OUT_OF_SCOPE_EXPLICIT"]:
            assert exclusion["family"]
            assert exclusion["reason"]
            assert "semantic_inputs" in exclusion
            exclusion_families.add(exclusion["family"])
        assert all("semantic_inputs" in item for item in row["IN_SCOPE_MODELED"])
        if name == "xiangqi_diagnostic":
            assert not row["scoped_coverage_complete"]
            assert row["classification"] == (
                "CURRENT_BUILDERS_SCOPED_COVERAGE_NOT_READY"
            )
            assert (
                len(row["IN_SCOPE_MODELED"]),
                len(row["OUT_OF_SCOPE_EXPLICIT"]),
                len(row["IN_SCOPE_UNSUPPORTED"]),
            ) == (62, 75, 1)
            modeled_counts = Counter(item["pattern"] for item in row["IN_SCOPE_MODELED"])
            assert modeled_counts["cannon_capture_one_screen"] == 4
            assert sum(modeled_counts[name] for name in modeled_counts if name.startswith("horse_")) == 16
            assert sum(modeled_counts[name] for name in modeled_counts if name.startswith("elephant_")) == 8
            assert modeled_counts["g_empty"] == modeled_counts["g_enemy"] == 4
            assert modeled_counts["a_empty"] == modeled_counts["a_enemy"] == 4
            assert modeled_counts["s_empty"] == modeled_counts["s_enemy"] == 3
            assert sum(
                "deterministic_geometry_domain_masks" in item["families"]
                for item in row["IN_SCOPE_MODELED"]
                if item["pattern"] in ("s_empty", "s_enemy")
            ) == 4
            for item in row["IN_SCOPE_MODELED"]:
                families = set(item["families"])
                if item["pattern"].startswith(("horse_", "elephant_", "cannon_capture")):
                    assert "finite_local_occupancy_predicates" in families
                if item["pattern"].startswith(("g_", "a_", "elephant_")) or (
                    item["pattern"].startswith("s_")
                    and "deterministic_geometry_domain_masks" in families
                ):
                    assert "deterministic_geometry_domain_masks" in families
                if item["pattern"].startswith("elephant_"):
                    assert {
                        "finite_local_occupancy_predicates",
                        "deterministic_geometry_domain_masks",
                    } <= families
            assert len(row["IN_SCOPE_UNSUPPORTED"]) == 1
            facing = row["IN_SCOPE_UNSUPPORTED"][0]
            assert facing["pattern"] == "general_facing_capture"
            assert facing["reasons"] == [
                "typed_target_occupancy_not_in_frozen_alphabet"
            ]
            assert "target_enemy" in facing["semantic_inputs"]["target"]
            assert "type_id='G'" in facing["semantic_inputs"]["guards"][0]
            assert any(
                item["family"] == "dynamic_positional_legality"
                and item["invariant"] == "own_anchor_safe"
                for item in row["OUT_OF_SCOPE_EXPLICIT"]
            )
            assert all(
                "square_zone_guards" in item["semantic_inputs"]
                for item in row["IN_SCOPE_UNSUPPORTED"]
            )
        else:
            assert row["IN_SCOPE_UNSUPPORTED"] == []
            assert row["scoped_coverage_complete"]
            assert row["classification"] == "CURRENT_BUILDERS_SCOPED_COVERAGE_VERIFIED"
            expected_counts = {
                "western_chess": (68, 94),
                "standard_shogi": (142, 168),
            }
            assert (
                len(row["IN_SCOPE_MODELED"]),
                len(row["OUT_OF_SCOPE_EXPLICIT"]),
            ) == expected_counts[name]

    assert exclusion_families == {
        "dynamic_positional_legality",
        "held_or_reentry_semantics",
        "history_or_auxiliary_state",
    }

    forbidden = (
        "board_intrinsic", "hand_drop", "raw_exact", "human_metric",
        "material_score", "rho_max", "density_model", "components_exact",
    )
    keys = " ".join(_all_keys(result)).lower()
    assert not any(field in keys for field in forbidden)


def test_coverage_only_path_fails_closed_on_intrinsic_unsupported(monkeypatch):
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    monkeypatch.setattr(
        coverage,
        "_intrinsic_unsupported",
        lambda _pattern, _geometry: ["fixture_intrinsic_unsupported"],
    )

    result = coverage.audit_coverage_ruleset(compiled, "western_chess")

    assert not result["scoped_coverage_complete"]
    assert result["classification"] == "CURRENT_BUILDERS_SCOPED_COVERAGE_NOT_READY"
    assert result["IN_SCOPE_UNSUPPORTED"]
    assert result["IN_SCOPE_UNSUPPORTED"][0]["reasons"] == ["fixture_intrinsic_unsupported"]


def test_xiangqi_finite_local_and_domain_primitives_have_paired_fixtures():
    compiled = compile_semantic_ruleset(build_xiangqi_diagnostic_ruleset())
    patterns = compiled.ir.patterns

    cannon = next(p for p in patterns if p.name == "cannon_capture_one_screen")
    assert coverage._finite_local_path_supported(cannon)
    count_one = cannon.path[0]

    def exactly_one_occupied(labels):
        return sum(label != "empty" for label in labels) == count_one.count

    assert exactly_one_occupied(("own", "empty"))
    assert exactly_one_occupied(("empty", "enemy"))
    assert not exactly_one_occupied(("empty", "empty"))
    assert not exactly_one_occupied(("own", "enemy"))
    assert not coverage._finite_local_path_supported(
        replace(cannon, path=(replace(count_one, count=2),))
    )

    horse = next(p for p in patterns if p.name == "horse_2_1_empty")
    elephant = next(p for p in patterns if p.name == "elephant_1_1_empty")
    eye = elephant.guards[0]
    assert coverage._single_square_empty_guard(horse.guards[0])
    assert coverage._single_square_empty_guard(eye)

    def guard_accepts(guard, occupant):
        occupied_count = int(occupant != "empty")
        return occupied_count == guard.value

    assert guard_accepts(eye, "empty")
    assert not guard_accepts(eye, "own")
    assert not guard_accepts(eye, "enemy")
    assert not coverage._single_square_empty_guard(replace(eye, value=1))

    width = compiled.board_shape.width
    palace_move = next(p for p in patterns if p.name == "g_empty")
    palace_guards = palace_move.square_zone_guards
    assert palace_guards and all(
        coverage._deterministic_domain_guard_supported(compiled, guard)
        for guard in palace_guards
    )
    source = 0 * width + 3
    target = 0 * width + 4
    assert all(
        coverage._domain_guard_holds(compiled, guard, 0, source, target)
        for guard in palace_guards
    )
    assert not coverage._domain_guard_holds(
        compiled, palace_guards[-1], 0, source, 0 * width + 6
    )
    owner_one_source = 9 * width + 5
    owner_one_target = 9 * width + 4
    assert all(
        coverage._domain_guard_holds(
            compiled, guard, 1, owner_one_source, owner_one_target
        )
        for guard in palace_guards
    )

    soldier = next(
        p for p in patterns
        if p.name == "s_empty" and p.square_zone_guards
    )
    soldier_zone = soldier.square_zone_guards[0]
    assert coverage._domain_guard_holds(
        compiled, soldier_zone, 0, 5 * width + 4, 5 * width + 5
    )
    assert not coverage._domain_guard_holds(
        compiled, soldier_zone, 0, 4 * width + 4, 4 * width + 5
    )

    elephant_zones = elephant.square_zone_guards
    elephant_source = 2 * width + 2
    elephant_target = 4 * width + 4
    assert all(
        coverage._domain_guard_holds(
            compiled, guard, 0, elephant_source, elephant_target
        )
        for guard in elephant_zones
    )
    assert guard_accepts(eye, "empty") and all(
        coverage._domain_guard_holds(
            compiled, guard, 0, elephant_source, elephant_target
        )
        for guard in elephant_zones
    )
    assert not guard_accepts(eye, "enemy")
    assert not coverage._domain_guard_holds(
        compiled, elephant_zones[-1], 0, elephant_source, 6 * width + 4
    )

    facing = next(p for p in patterns if p.name == "general_facing_capture")
    typed_guard = facing.guards[0]
    assert coverage._typed_target_guard(typed_guard)
    assert not coverage._typed_target_guard(replace(typed_guard, value=2))
    assert not coverage._typed_target_guard(
        replace(typed_guard, compare_field="base")
    )
    assert not coverage._finite_local_path_supported(
        replace(facing, path=(replace(facing.path[0], kind="path_count_range"),))
    )
    assert "typed_target_occupancy_not_in_frozen_alphabet" in (
        coverage._coverage_intrinsic_reasons(
            facing, compiled.ir.geometry[facing.geometry_ids[0]], compiled
        )
    )


def test_coverage_inventory_fails_closed_on_unrecognized_effect():
    pattern = SimpleNamespace(
        name="unknown_creation",
        effects=(SimpleNamespace(kind="spawn_piece", disposition=None),),
        geometry_ids=(0,),
    )
    compiled = SimpleNamespace(
        ir=SimpleNamespace(patterns=(pattern,), geometry={0: SimpleNamespace(kind="leap")}),
        support=SimpleNamespace(initial_position=((object(), None),)),
    )

    result = coverage._inventory_coverage(compiled)

    assert not result["complete"]
    assert any("unrecognized_effect" in reason for reason in result["failure_reasons"])
