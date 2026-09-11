"""F86N-R1 PREP-frozen candidate and result contracts."""

import json
from pathlib import Path

import pytest

from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from scripts.f86n_r1_transport_aware_signed_sampler import _movement_seed, _select_candidate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json"
RESULT = ROOT / "artifacts/f86n_r1_transport_aware_signed_sampler/results.json"


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_f86n_r1_prep_freezes_all_eight_candidates_and_boundary_safe_predicate():
    payload = _load()
    assert payload["status"] == "PRE_REGISTERED_STATIC_FROZEN_CANDIDATES"
    assert len(payload["entries"]) == 8
    assert all(entry["candidate_ruleset"] is not None for entry in payload["entries"])
    assert all(entry["backbone_predicate"]["passes"] for entry in payload["entries"])
    assert all(entry["backbone_predicate"]["backbone_witness"] is not None for entry in payload["entries"])
    assert payload["backbone_predicate"]["requires_scc_two_file_span"] is True
    assert payload["backbone_predicate"]["requires_scc_two_owner_relative_rank_span"] is True


def test_f86n_r1_seed_and_serialized_candidate_fingerprints_are_deterministic():
    payload = _load()
    for entry in payload["entries"]:
        assert entry["movement_rng_seed"] == _movement_seed(entry["sample_id"], entry["source_ruleset_fingerprint"])
        assert compile_ruleset(ruleset_from_dict(entry["candidate_ruleset"])).ruleset_fingerprint == entry["candidate_ruleset_fingerprint"]
        assert entry["material_profile"]["aggregate_transitive_source_union_square_count"] >= 0


def test_f86n_r1_replaying_prep_selection_reproduces_every_candidate():
    payload = _load()
    for entry in payload["entries"]:
        selected = _select_candidate(ruleset_from_dict(entry["source_ruleset"]), entry["sample_id"], entry["source_ruleset_fingerprint"])
        assert selected["accepted_attempt"] == entry["accepted_attempt"]
        assert selected["candidate_ruleset_fingerprint"] == entry["candidate_ruleset_fingerprint"]


def test_f86n_r1_result_contract_is_deferred_until_after_prep_publish():
    if not RESULT.exists():
        pytest.skip("F86N-R1 result gate runs after independently published PREP")
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["status"] == "F86N_R1_STATIC_PREFLIGHT_ZERO_DYNAMIC_COMPUTE"
    assert payload["dynamic"]["real_games"] == 0
