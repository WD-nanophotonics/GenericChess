"""F86N prep and static-prefight contracts."""

import json
from pathlib import Path

import pytest

from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/f86n_transport_aware_signed_sampler/manifest.json"
RESULT = ROOT / "artifacts/f86n_transport_aware_signed_sampler/results.json"
SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_f86n_manifest_freezes_signed_pool_sampler_and_all_eight_samples():
    payload = _load()
    assert payload["candidate_profile"] == "TRANSPORT_AWARE_SIGNED_MOVEMENT_SAMPLER_PREFLIGHT"
    assert [row["sample_id"] for row in payload["entries"]] == list(SAMPLES)
    assert payload["sampler"] == {
        "dedupe": True,
        "fallback": "one_signed_leap",
        "leap_include_probability": 0.7,
        "leap_slot_count": 2,
        "max_attempts": 4096,
        "ordering": "sample_order_after_source_type_order",
        "ray_include_probability": 0.55,
        "result_driven_replacement_forbidden": True,
        "retry_algorithm": "seed_plus_attempt_random_mt19937",
    }
    assert payload["signed_movement_pool"]["reverse_ray_preserves_max_steps"] is True
    assert payload["backbone_predicate"]["piece_type_index1_not_required_globally"] is True
    assert payload["dynamic_budget"]["real_games"] == 0
    assert payload["default_generator_changed"] is False


def test_f86n_source_fingerprints_and_seed_binding_are_exact():
    payload = _load()
    for entry in payload["entries"]:
        compiled = compile_ruleset(ruleset_from_dict(entry["source_ruleset"]))
        assert compiled.ruleset_fingerprint == entry["source_ruleset_fingerprint"]
        assert entry["movement_rng_seed"] == entry["source_seed"] * 10 + 9


def test_f86n_result_contract_is_deferred_until_after_prep_publish():
    if not RESULT.exists():
        pytest.skip("F86N result gate runs after independently published prep")
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["status"] == "F86N_STATIC_PREFLIGHT_ZERO_DYNAMIC_COMPUTE"
    assert payload["dynamic"]["real_games"] == 0


def test_f86n_result_freezes_bounded_sampling_and_fail_closed_unavailable_material():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    candidates = {row["sample_id"]: row for row in payload["candidates"]}
    assert payload["sampling_summary"] == {
        "accepted_count": 7,
        "max_attempts": 4096,
        "structural_predicate_unavailable_count": 1,
    }
    assert [candidates[sample_id]["accepted_attempt"] for sample_id in ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")] == [1, 14, 4, 41, None, 7, 25, 31]
    assert candidates["V5-2"]["sampling_status"] == "STRUCTURAL_PREDICATE_UNAVAILABLE"
    assert candidates["V5-3"]["backbone_type"] == "P1"


def test_f86n_targeted_static_gate_routes_witness_before_truncation():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["static_candidate_checks"] == {
        "V4-3": 396,
        "V5-3": 2048,
        "per_cell_cap": 2048,
        "total": 2444,
        "total_cap": 4096,
    }
    targeted = {row["sample_id"]: row for row in payload["targeted_static_mate_capacity"]}
    assert targeted["V4-3"]["validated_position_count"] == 334
    assert targeted["V4-3"]["validated_template_count"] == 33
    assert targeted["V4-3"]["truncation"] is False
    assert targeted["V4-3"]["joint_kinematically_reachable_count"] == 0
    assert targeted["V5-3"]["validated_position_count"] == 1870
    assert targeted["V5-3"]["validated_template_count"] == 98
    assert targeted["V5-3"]["truncation"] is True
    assert targeted["V5-3"]["joint_kinematically_reachable_count"] == 16
    assert targeted["V5-3"]["minimum_optimistic_ply_lower_bound"] == 10
    assert payload["routing"] == {
        "dynamic": "NOT_RUN_BY_STATIC_PREFLIGHT",
        "static": [
            {"sample_id": "V4-3", "routing": "TRANSPORT_AWARE_SIGNED_SAMPLER_INSUFFICIENT_KINEMATICALLY"},
            {"sample_id": "V5-3", "routing": "TRANSPORT_AWARE_SIGNED_SAMPLER_STATIC_WITNESS_EXISTS"},
        ],
    }
