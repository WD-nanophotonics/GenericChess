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
