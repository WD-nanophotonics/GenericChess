"""F23C V2 corpus, exact-solver, split, and invariance contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_f23b_evaluator_corpus as f23b
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts.audit_f23c_evaluator_corpus_r2 import audit_development


V1 = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v2.json"


def test_f23c_builder_is_deterministic_and_v1_bytes_are_untouched():
    before = V1.read_bytes()
    expected = json.loads(V2.read_text(encoding="utf-8"))
    assert f23c.build_corpus() == expected
    assert V1.read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == expected["source_v1_sha256"]


def test_f23c_preserves_v1_generic_stratum_and_f22_exactly():
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    v2 = json.loads(V2.read_text(encoding="utf-8"))
    assert v2["frozen_legacy_f22"] == v1["frozen_legacy_f22"]
    assert v2["generic_exact"][: len(v1["generic_exact"])] == v1["generic_exact"]
    assert len(v2["generic_exact"]) == 21
    assert v2["coverage"]["generic_positions_added_r2"] == 13


def test_f23c_split_is_reused_and_both_sides_are_nonempty():
    fixture = json.loads(V2.read_text(encoding="utf-8"))
    cases = fixture["generic_exact"]
    assert fixture["split"]["algorithm"] == json.loads(V1.read_text(encoding="utf-8"))["split"]["algorithm"]
    assert fixture["split"]["frozen_before_fitting"] is True
    assert fixture["split"]["development_count"] == sum(case["split"] == "DEVELOPMENT" for case in cases)
    assert fixture["split"]["holdout_count"] == sum(case["split"] == "HOLDOUT" for case in cases)
    assert fixture["split"]["development_count"] > 0
    assert fixture["split"]["holdout_count"] > 0
    assert len({case["state_identity_sha256"] for case in cases}) == len(cases)


def test_f23c_event_cases_have_independent_exact_evidence():
    fixture = json.loads(V2.read_text(encoding="utf-8"))
    added = fixture["generic_exact"][8:]
    assert {case["reference_authority_class"] for case in added} == {"exact legal-action set", "exact one-ply terminal outcome"}
    assert any("capture" in case["event_tags"] and case["event_evidence"]["capture_action_count"] > 0 for case in added)
    assert any("recapture" in case["event_tags"] and case["event_evidence"]["recapture_witness_count"] > 0 for case in added)
    assert any("drop" in case["event_tags"] and case["event_evidence"]["drop_action_count"] > 0 for case in added)
    for case in added:
        assert case["label"]["diagnostic_reference_action"]
        assert case["source"].startswith("fixture:")
        assert "evaluator" not in case["reference_authority"].lower()


def test_f23c_feature_probe_uses_development_only_and_meets_prototype_gate():
    report = audit_development()
    assert report["status"] == "PASS"
    assert report["source_v1_sha256_matches"] is True
    assert report["frozen_f22_reproduced"] is True
    assert report["development_cases"] == 18
    assert report["holdout_excluded"] == 3
    gate = report["quality_gate"]
    assert gate["cross_ruleset_meaningful_family_count"] >= 5
    assert gate["attack_defense_meaningful"] is True
    assert gate["capture_recapture_meaningful"] is True
    assert gate["prototype_gate_passed"] is True
    assert report["selected_next_boundary"] == "F23D_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE"
    assert all(row["id"] not in {case["id"] for case in json.loads(V2.read_text(encoding="utf-8"))["generic_exact"] if case["split"] == "HOLDOUT"} for row in report["rows"])


def test_f23c_identity_is_key_order_stable_and_owner_symmetric_orbit_is_distinct():
    m = f23c._imports()
    payload = {"ruleset_id": "r", "state": {"rows": ["kK"], "side_to_move": 0}, "label_kind": "exact"}
    reordered = {"label_kind": "exact", "state": {"side_to_move": 0, "rows": ["kK"]}, "ruleset_id": "r"}
    case = {"ruleset_id": "r", "state": payload["state"], "label_kind": "exact"}
    other = {"ruleset_id": "r", "state": reordered["state"], "label_kind": "exact"}
    assert f23c._identity(case, m) == f23c._identity(other, m)
    # The corpus deliberately uses owner-labelled states; an owner-swapped
    # orbit is a separate invariance control, never a hidden duplicate.
    swapped = {"ruleset_id": "r", "state": {"rows": ["Kk"], "side_to_move": 1}, "label_kind": "exact"}
    assert f23c._identity(case, m) != f23c._identity(swapped, m)
