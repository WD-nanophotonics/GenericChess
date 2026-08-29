"""F23F grouped-fit, leakage, weighting, and rejection contracts."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

from scripts import audit_f23f_evaluator_v2_prototype_r2 as f23f


ROOT = Path(__file__).parents[1]
V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
SPEC = ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json"


def test_f23f_candidate_spec_is_reproducible_and_corpus_inputs_are_immutable():
    before = {path: path.read_bytes() for path in (V1, V2, V3)}
    report = f23f.audit_development()
    persisted = json.loads(SPEC.read_text(encoding="utf-8"))
    assert persisted["status"] == "REJECTED_BEFORE_HOLDOUT"
    assert persisted["candidate_spec"] == report["candidate_spec"]
    encoded = json.dumps(report["candidate_spec"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert persisted["candidate_spec_sha256"] == report["candidate_spec_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert {path: path.read_bytes() for path in (V1, V2, V3)} == before


def test_f23f_grouped_validation_is_equal_ruleset_and_rejects_candidate_before_holdout():
    report = f23f.audit_development()
    assert report["development_roots"] == 20
    assert report["feature_selection"]["selected"] == ["attack_defense_hanging", "anchor_check_pressure", "legal_safe_mobility", "capture_recapture_pressure"]
    assert set(report["loo"]) == {"strong-ray-8x8", "strong-bishop-knight-7x7", "strong-knight-6x6", "strong-drop-lance-8x8"}
    assert report["folds_improved"] == 0
    assert report["advancement_gate_passed"] is False
    assert report["decision"]["selected_next_boundary"] == "F23G_REFERENCE_PREFERENCE_CORPUS_R2"
    assert report["holdout_opened"] is False
    assert report["shogi_opened"] is False


def test_f23f_structural_and_weak_roots_are_excluded_from_fit():
    rows = f23f._load_dev_rows()
    fixture = json.loads(V3.read_text(encoding="utf-8"))
    expected = {entry["id"] for entry in fixture["generic_exact"] if entry["split"] == "DEVELOPMENT" and entry.get("supervision_class") == "PREFERENCE_STRONG"}
    assert {row["id"] for row in rows} == expected
    assert len(rows) == 20
    assert "holdout" not in inspect.getsource(f23f._load_dev_rows).lower()


def test_f23f_constraints_never_order_ties_and_deduplicate_within_groups():
    rows = f23f._load_dev_rows()
    raw, deduped = f23f._constraints(rows)
    assert set(raw) == set(deduped)
    assert sum(len(pairs) for pairs in deduped.values()) <= sum(len(pairs) for pairs in raw.values())
    for pairs in raw.values():
        for optimal, inferior in pairs:
            assert optimal["optimal"] is True
            assert inferior["optimal"] is False
    assert len({row["ruleset_id"] for row in rows}) == 4


def test_f23f_source_has_no_shogi_or_production_path_dependency():
    source = Path(f23f.__file__).read_text(encoding="utf-8")
    assert "AlphaSho" not in source
    assert "build_semantic_shogi_ruleset" not in source
    assert "Evaluator(" not in source
    assert "generic_chess.ai.evaluation.evaluator" not in source
