"""Contracts for the provenance-safe F23B evaluator corpus."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_f23b_evaluator_corpus import build_corpus, recover_f22_stratum
from scripts.audit_f23b_evaluator_corpus import audit_development


FIXTURE = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v1.json"


def test_f23b_fixture_is_a_deterministic_builder_output():
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert build_corpus() == expected


def test_f23b_preserves_f22_legacy_stratum_exactly():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    recovered = recover_f22_stratum()
    assert fixture["frozen_legacy_f22"] == recovered
    assert len(fixture["frozen_legacy_f22"]["positions"]) == 10
    assert len(fixture["frozen_legacy_f22"]["references"]) == 10


def test_f23b_split_is_frozen_and_nonempty():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    generic = fixture["generic_exact"]
    assert fixture["split"]["frozen_before_fitting"] is True
    assert fixture["split"]["development_count"] == sum(
        case["split"] == "DEVELOPMENT" for case in generic
    )
    assert fixture["split"]["holdout_count"] == sum(
        case["split"] == "HOLDOUT" for case in generic
    )
    assert fixture["split"]["development_count"] > 0
    assert fixture["split"]["holdout_count"] > 0


def test_f23b_labels_are_exact_solver_labels_not_evaluator_scores():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for case in fixture["generic_exact"]:
        assert "reference_authority" in case
        assert "evaluator" not in case["reference_authority"].lower()
        assert case["solver"]["max_nodes"] > 0
        assert case["state_identity_sha256"]


def test_f23b_development_probe_reproduces_f22_and_holds_prototype_gate():
    report = audit_development()
    assert report["status"] == "PASS"
    assert report["frozen_f22_reproduced"] is True
    assert report["holdout_excluded"] == 1
    assert report["quality_gate"]["cross_ruleset_meaningful_family_count"] == 3
    assert report["quality_gate"]["prototype_gate_passed"] is False
    assert report["selected_next_boundary"] == "F23C_EVALUATOR_CORPUS_EXPANSION_R2"
