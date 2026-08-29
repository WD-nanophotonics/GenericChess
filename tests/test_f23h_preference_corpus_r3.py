"""F23H effective-orbit V5 corpus contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_f23h_preference_corpus_r3 as f23h


ROOT = Path(__file__).parents[1]
V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
V5 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json"
F23F = ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json"


def test_f23h_rebuild_is_deterministic_and_all_prior_artifacts_are_immutable():
    frozen = {path: path.read_bytes() for path in (V1, V2, V3, V4, F23F)}
    expected = json.loads(V5.read_text(encoding="utf-8"))
    assert f23h.build_corpus() == expected
    assert {path: path.read_bytes() for path in frozen} == frozen
    assert expected["source_v4_sha256"] == hashlib.sha256(frozen[V4]).hexdigest()


def test_f23h_uses_effective_orbits_for_a_clean_deep_gate():
    fixture = json.loads(V5.read_text(encoding="utf-8"))
    new = [entry for entry in fixture["generic_exact"] if entry["id"].startswith("generic-f23h-")]
    effective = fixture["effective_orbits"]
    coverage = fixture["coverage"]
    assert fixture["sampling"]["candidate_pool_size"] == 30
    assert fixture["sampling"]["solved_candidate_count"] == 30
    assert fixture["sampling"]["unresolved_candidate_count"] == 0
    assert len(new) == 30
    assert effective["effective_decision_orbits"] == 30
    assert effective["excluded_cross_split_orbit_ids"] == []
    assert effective["fit_eligible_development_orbit_ids"].__len__() == 20
    assert effective["validation_eligible_holdout_orbit_ids"].__len__() == 7
    assert effective["excluded_cross_split_orbit_ids"] == []
    assert effective["historical_v4_duplicate_orbit_ids"].__len__() == 3
    assert coverage["multiply_development"] == 20
    assert coverage["wdl_partition_diverse_development"] == 20
    assert coverage["non_max_ply_development"] == 20
    assert len(coverage["ruleset_distribution"]) == 5
    assert len(coverage["mechanic_distribution"]) == 2
    assert fixture["corrected_deep_supervision_gate"]["passes"] is True


def test_f23h_representatives_have_real_behavioral_diversity_and_no_duplicates():
    fixture = json.loads(V5.read_text(encoding="utf-8"))
    new = [entry for entry in fixture["generic_exact"] if entry["id"].startswith("generic-f23h-")]
    assert len({(entry["ruleset_id"], entry["decision_subtree_fingerprint"]) for entry in new}) == 30
    assert len({entry["effective_orbit_id"] for entry in new}) == 30
    assert len({(entry["ruleset_id"], json.dumps(entry["state"], sort_keys=True)) for entry in new}) == 30
    assert {entry["mechanic_family"] for entry in new} == {"auxiliary_reply_chain", "capture_bad_branch"}
    assert all(entry["physical_multiplicity"] == 1 for entry in new)
    assert all(not entry["preference_authority"]["max_ply_dependence"] for entry in new)
    assert all(min(entry["preference_authority"]["optimal_proof_depths"]) >= 2 for entry in new)


def test_f23h_capture_branch_changes_root_action_partition():
    fixture = json.loads(V5.read_text(encoding="utf-8"))
    capture = [entry for entry in fixture["generic_exact"] if entry.get("mechanic_family") == "capture_bad_branch"]
    assert capture
    assert all({row["value"] for row in entry["preference_authority"]["all_root_action_values"]} == {"DRAW", "LOSS"} for entry in capture)
    assert any(any(row["action"].get("pattern_id") == "sem_02_capture_bad" for row in entry["preference_authority"]["all_root_action_values"]) for entry in capture)
