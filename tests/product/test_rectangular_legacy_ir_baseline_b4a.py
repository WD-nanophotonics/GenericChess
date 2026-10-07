import hashlib
from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.coordinates import BoardShape
from generic_chess.rules.compiler import (
    _build_semantic_support,
    _compile_geometry_carrier,
    compile_semantic_ruleset,
    lower_legacy_to_ir,
)
from generic_chess.rules.ir import geometry_candidates, validate_executable_completeness, validate_ir
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset
from test_rectangular_board_geometry_a import _fixture


def _serialized_sha(ir):
    return hashlib.sha256(ir.serialized().encode("utf-8")).hexdigest()


def test_compile_only_carrier_lowers_canonical_legacy_ray_and_leap_patterns():
    rules = _fixture()
    carrier = _compile_geometry_carrier(rules)
    ir = lower_legacy_to_ir(carrier, ruleset=rules)
    support = _build_semantic_support(carrier, ruleset=rules)

    assert support.board_shape == BoardShape(9, 10)
    assert support.board_area == 90
    assert support.board_size is None
    assert all(not value for value in (
        ir.capabilities.legacy_core_executable,
        ir.capabilities.new_ir_core_executable,
        ir.capabilities.native_executable,
    ))

    assert len(ir.geometry) == 7  # six canonical atom geometries plus drop
    for geometry in ir.geometry.values():
        if geometry.kind == "drop":
            assert not geometry.paths
            continue
        assert set(geometry.paths) == {"0", "1"}
        assert all(len(per_source) == 90 for per_source in geometry.paths.values())
        assert {
            pattern.target.kind
            for pattern in ir.patterns
            if geometry.geometry_id in pattern.geometry_ids
        } == {"target_empty", "target_enemy"}

    ray_id = next(
        geometry_id for geometry_id, geometry in ir.geometry.items()
        if geometry.atom_source == ("K", 0)
    )
    ray = ir.geometry[ray_id]
    assert ray.kind == "ray"
    assert ray.paths["0"][45] == tuple(range(46, 54))
    assert (53, tuple(range(46, 53))) in geometry_candidates(ray, "0", 45)
    ray_capture = next(
        pattern for pattern in ir.patterns
        if pattern.geometry_ids == (ray_id,) and pattern.target.kind == "target_enemy"
    )
    assert [predicate.kind for predicate in ray_capture.path] == ["path_clear"]

    leap_id = next(
        geometry_id for geometry_id, geometry in ir.geometry.items()
        if geometry.atom_source == ("K", 4)
    )
    leap = ir.geometry[leap_id]
    assert leap.kind == "leap"
    assert leap.paths["0"][30] == (41,)
    assert leap.paths["1"][30] == (19,)
    leap_capture = next(
        pattern for pattern in ir.patterns
        if pattern.geometry_ids == (leap_id,) and pattern.target.kind == "target_enemy"
    )
    assert not leap_capture.path

    errors = validate_ir(ir)
    errors.extend(validate_executable_completeness(ir, tuple(sorted(carrier.types_by_id))))
    assert errors == []


def test_compile_only_carrier_requires_matching_ruleset():
    rules = _fixture()
    carrier = _compile_geometry_carrier(rules)
    with pytest.raises(ValueError, match="required"):
        lower_legacy_to_ir(carrier)
    with pytest.raises(ValueError, match="does not match"):
        lower_legacy_to_ir(
            carrier,
            ruleset=replace(rules, board_width=10, board_height=9),
        )


@pytest.mark.parametrize(
    "builder,expected_sha",
    (
        (
            build_western_chess_ruleset,
            "9c56a182d005eb01149b3c6d8211cec5db22350c0f8c87d7a510a1943bbcbf00",
        ),
        (
            build_standard_shogi_ruleset,
            "dba7039afb4c33a7f49028de14e23ec3e9fb3b2c04136ff6c15f2ab76bb179a4",
        ),
        (
            cannon_ruleset,
            "9b35a423f13da6e5583436bcb05cac251bda8768b195a745f28bc5fadf50f5cb",
        ),
    ),
)
def test_square_semantic_ir_serialization_is_byte_identical(builder, expected_sha):
    ir = compile_semantic_ruleset(builder()).ir
    assert _serialized_sha(ir) == expected_sha
