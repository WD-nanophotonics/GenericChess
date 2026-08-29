"""F23I development-only evaluator V2 prototype audit contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import audit_f23i_evaluator_v2_prototype_r3 as f23i


ROOT = Path(__file__).parents[1]
V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
V5 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json"
F23F = ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json"
SCRIPT = ROOT / "scripts" / "audit_f23i_evaluator_v2_prototype_r3.py"


def _audit():
    f23i.audit_development.cache_clear()
    return f23i.audit_development()


def test_f23i_consumes_only_explicit_development_orbits_and_keeps_later_phases_closed():
    fixture = json.loads(V5.read_text(encoding="utf-8"))
    report = _audit()
    eligible = set(fixture["effective_orbits"]["fit_eligible_development_orbit_ids"])
    holdout = set(fixture["effective_orbits"]["validation_eligible_holdout_orbit_ids"])
    assert set(report["eligible_orbit_ids"]) == eligible
    assert set(report["eligible_orbit_ids"]).isdisjoint(holdout)
    assert report["development_orbits"] == 20
    assert report["holdout_opened"] is False
    assert report["shogi_opened"] is False
    assert report["candidate_spec"] is None


def test_f23i_grouped_gate_is_deterministic_bounded_and_selects_next_boundary():
    first = _audit()
    second = _audit()
    first_semantic = {key: value for key, value in first.items() if key != "runtime_cost"}
    second_semantic = {key: value for key, value in second.items() if key != "runtime_cost"}
    assert json.dumps(first_semantic, sort_keys=True) == json.dumps(second_semantic, sort_keys=True)
    assert set(first["runtime_cost"]["median_feature_seconds"]) == set(first["feature_selection"]["selected"])
    assert len(first["feature_selection"]["selected"]) <= 4
    assert first["folds_improved"] == 2
    assert first["transfer_improved"] == 0
    assert first["advancement_gate_passed"] is False
    assert first["decision"]["selected_next_boundary"] == "F23J_REFERENCE_PREFERENCE_CORPUS_R4"
    assert set(first["loo"]) == {
        "f23h-aux-geometry-0",
        "f23h-aux-geometry-1",
        "f23h-aux-geometry-2",
        "f23h-capture-geometry-3",
        "f23h-capture-geometry-4",
    }
    assert set(first["mechanic_transfer"]) == {"auxiliary_reply_chain", "capture_bad_branch"}


def test_f23i_does_not_mutate_frozen_corpora_or_import_fit_history():
    frozen = {path: path.read_bytes() for path in (V1, V2, V3, V4, V5, F23F)}
    _audit()
    assert {path: path.read_bytes() for path in frozen} == frozen
    source = SCRIPT.read_text(encoding="utf-8")
    assert "audit_f23f_evaluator_v2_prototype_r2" not in source
    assert "evaluator_v2_candidate_spec_f23f" not in source
    assert "validation_eligible_holdout_orbit_ids" not in source
    assert hashlib.sha256(V4.read_bytes()).hexdigest() == json.loads(V5.read_text(encoding="utf-8"))["source_v4_sha256"]
