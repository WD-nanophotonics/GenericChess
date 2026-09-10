"""Contract tests for the F76-R1 trusted-root correction."""

import json
from pathlib import Path

from scripts import f76_parent_retained_pointwise_q_output_delta as f76
from scripts import f76_r1_trusted_pointwise_q_corrective as r1


ROOT = Path(__file__).resolve().parents[1]


def test_r1_scope_and_separate_candidate_identity():
    source = (ROOT / "scripts" / "f76_r1_trusted_pointwise_q_corrective.py").read_text(
        encoding="utf-8"
    )
    assert r1.WORK_ORDER == "GENERICCHESS-F76-R1-TRUSTED-POINTWISE-Q-CORRECTIVE"
    assert r1.PARENT_SHA == "b40792426a4df593efb9febe8b97350cc029d097"
    assert r1.GEN1_ID == f76.GEN1_ID
    assert r1.CANDIDATE_PATH != f76.CANDIDATE_PATH
    assert "_trusted_roots_with_predicates" in source
    assert "pointwise = f76._pointwise_rows(trusted_rows" in source
    assert "fit_data_all = [f76._root_rows(root, parent_model) for root in fit_roots]" in source
    assert "alpha_star = float(min(1.0, 0.5 * high_boundary, residual_boundary))" in source
    assert "development = None" in source
    assert "POINTWISE_OUTPUT_DELTA_UNSAFE" in source
    assert "POINTWISE_OUTPUT_DELTA_REDUNDANT_WITH_F74" in source


def test_trusted_root_predicate_has_all_registered_components():
    root = {
        "metadata": {
            "root_40k": {"action_key": "deep"},
            "root_80k": {"action_key": "deep"},
            "spectrum_top_10k_action_key": "deep",
            "spectrum_top_20k_action_key": "deep",
            "root_80k_mate_band": False,
            "retained_q20_any_mate_band": False,
        },
        "root_index": 7,
    }
    trusted, audited = r1._trusted_roots_with_predicates([root])
    assert trusted == [root]
    assert audited[0]["trusted"] is True
    assert set(audited[0]) == {
        "root_index", "root_40k_matches_root_80k", "q10k_matches_q20k",
        "q10k_matches_deep", "root_80k_not_mate_band",
        "retained_q20_not_mate_band", "trusted",
    }


def test_nontrusted_root_is_excluded_without_changing_filter():
    root = {
        "metadata": {
            "root_40k": {"action_key": "a"},
            "root_80k": {"action_key": "deep"},
            "spectrum_top_10k_action_key": "deep",
            "spectrum_top_20k_action_key": "deep",
            "root_80k_mate_band": False,
            "retained_q20_any_mate_band": False,
        },
        "root_index": 9,
    }
    trusted, audited = r1._trusted_roots_with_predicates([root])
    assert trusted == []
    assert audited[0]["root_40k_matches_root_80k"] is False


def test_invalid_f76_artifact_remains_historical_and_compact():
    old = json.loads(
        (ROOT / "artifacts" / "f76_parent_retained_pointwise_q" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )
    assert old["child_checkpoint_id"] == r1.INVALID_F76_ID
    assert len(old["raw_delta"]) == 32
    assert r1.CANDIDATE_PATH.name == "candidate.json"
    assert r1.CANDIDATE_PATH.parent.name == "f76_r1_trusted_pointwise_q"


def test_r1_classification_order_distinguishes_contract_safety_redundancy_and_visibility():
    visible = {"decision_changes": 1}
    hidden = {"decision_changes": 0}
    assert r1._classify(["split"], [], 0.0, None) == "HARNESS_MISMATCH"
    assert r1._classify([], ["alpha"], 0.0, None) == "POINTWISE_OUTPUT_DELTA_UNSAFE"
    assert r1._classify([], [], 0.995, None) == "POINTWISE_OUTPUT_DELTA_REDUNDANT_WITH_F74"
    assert r1._classify([], [], 0.0, visible) == "POINTWISE_OUTPUT_DELTA_DEPLOYMENT_VISIBLE"
    assert r1._classify([], [], 0.0, hidden) == "POINTWISE_OUTPUT_DELTA_NOT_DEPLOYMENT_VISIBLE"
