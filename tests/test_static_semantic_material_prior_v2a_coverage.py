from __future__ import annotations

import re
from types import SimpleNamespace

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
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
    assert set(result["rulesets"]) == {"western_chess", "standard_shogi"}

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
        assert row["IN_SCOPE_UNSUPPORTED"] == []
        assert row["scoped_coverage_complete"]
        assert row["classification"] == "CURRENT_BUILDERS_SCOPED_COVERAGE_VERIFIED"

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
