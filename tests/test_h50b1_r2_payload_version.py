from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from generic_chess.native import _module, native_capabilities
from generic_chess.native.compiler import (
    SEMANTIC_PAYLOAD_VERSION,
    build_semantic_compile_payload,
    compile_native_semantic_rules,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset


ROOT = Path(__file__).resolve().parents[1]
R2_FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r2_semantic_native_execution.json"


def _payload(builder):
    semantic = compile_semantic_ruleset(builder())
    payload, report = build_semantic_compile_payload(semantic)
    return semantic, payload, report


def test_r2_fixture_contains_complete_canonical_matrices_and_provenance():
    fixture = json.loads(R2_FIXTURE.read_text(encoding="utf-8"))
    western = {row["id"] for row in fixture["western_matrix"]}
    shogi = {row["id"] for row in fixture["standard_shogi_matrix"]}
    assert len(western) == 24
    assert len(shogi) == 21
    assert all(row["status"] == "PASS" and row["witness"] for row in fixture["western_matrix"])
    assert all(row["status"] == "PASS" and row["witness"] for row in fixture["standard_shogi_matrix"])
    assert fixture["payload_version_transition"] == {"H50A": 2, "H50B1": 3, "H50B1-R2": 4}
    assert fixture["generic_witness"]["game_name_branch"] is False
    assert len(fixture["generic_witness"]["canonical_ir_sha256"]) == 64
    assert len(fixture["generic_witness"]["canonical_native_payload_sha256"]) == 64
    assert len(fixture["native_build"]["sha256"].replace(" ", "")) == 64
    assert fixture["F50B2_status"] == "NOT_STARTED"


def test_r2_current_builder_and_capability_report_v4():
    semantic, payload, report = _payload(build_standard_shogi_ruleset)
    native = compile_native_semantic_rules(semantic)
    assert SEMANTIC_PAYLOAD_VERSION == 4
    assert payload["semantic_payload_version"] == 4
    assert report.semantic_payload_version == 4
    assert native_capabilities()["semantic_payload_version"] == 4
    assert _module().semantic_rules_info(native.capsule)["semantic_payload_version"] == 4


def test_r2_v4_roundtrips_declarations_and_automatic_records():
    semantic, payload, _report = _payload(build_standard_shogi_ruleset)
    native = compile_native_semantic_rules(semantic)
    info = _module().semantic_rules_info(native.capsule)
    assert info["declarations"] == payload["declarations"]
    assert info["automatic_adjudications"] == payload["automatic_adjudications"]
    assert info["repetition_policy"] == payload["repetition_policy"]
    assert info["max_ply"] == payload["max_ply"]


def test_r2_historical_v3_shape_is_accepted_but_v4_fields_are_not_reinterpreted():
    _semantic, payload, _report = _payload(cannon_ruleset)
    legacy = deepcopy(payload)
    legacy["semantic_payload_version"] = 3
    legacy.pop("automatic_adjudications")
    legacy.pop("declarations")
    info = _module().semantic_rules_info(_module().compile_semantic_rules(legacy))
    assert info["semantic_payload_version"] == 3
    assert info["declarations"] == []
    assert info["automatic_adjudications"] == []

    with pytest.raises(ValueError, match="require payload v4"):
        invalid = deepcopy(payload)
        invalid["semantic_payload_version"] = 3
        _module().compile_semantic_rules(invalid)


@pytest.mark.parametrize("field", ["declarations", "automatic_adjudications"])
def test_r2_v4_missing_contract_field_fails_closed(field):
    _semantic, payload, _report = _payload(build_standard_shogi_ruleset)
    malformed = deepcopy(payload)
    malformed.pop(field)
    with pytest.raises(ValueError):
        _module().compile_semantic_rules(malformed)


def test_r2_unknown_future_version_fails_closed():
    _semantic, payload, _report = _payload(cannon_ruleset)
    payload["semantic_payload_version"] = 5
    with pytest.raises(ValueError, match="unsupported semantic_payload_version"):
        _module().compile_semantic_rules(payload)
