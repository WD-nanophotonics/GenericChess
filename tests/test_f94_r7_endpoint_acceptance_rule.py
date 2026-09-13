from __future__ import annotations

import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULE = ROOT / "docs/architecture/GENERICCHESS_F94_R7_ENDPOINT_ACCEPTANCE_RULE_V1.json"
PREREG = ROOT / "docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json"


def test_r7_endpoint_rule_is_frozen_and_zero_compute():
    payload = json.loads(RULE.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f94-r7-layer-d-endpoint-acceptance-rule-v1"
    assert payload["status"] == "FROZEN_PROSPECTIVE_NO_DATA_COLLECTED"
    assert payload["compute_boundary"] == {
        "new_arena_authorized": False,
        "new_heavy_authorized": False,
        "classifier_mutation_allowed": False,
    }
    assert payload["endpoint"]["name"] == "4096_vs_256"
    assert payload["endpoint"]["required_complete_pairs"] == 18
    actual_parent_sha = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    assert payload["parent_preregistration"]["sha256"] == actual_parent_sha


def test_r7_endpoint_rule_requires_strict_positive_direction_and_confidence():
    payload = json.loads(RULE.read_text(encoding="utf-8"))
    direction = payload["positive_direction"]
    assert direction["reference_value"] == 0.5
    assert direction["mean_pair_score"] == "strictly_greater_than_reference"
    assert direction["child_better_pairs"] == "strictly_greater_than_child_worse_pairs"
    confidence = payload["confidence"]
    assert confidence["method"] == "deterministic_nonparametric_bootstrap_of_pair_means"
    assert confidence["confidence"] == 0.95
    assert confidence["resamples"] == 10_000
    assert confidence["seed"] == 271828
    assert confidence["lower_index"] == 250
    assert confidence["acceptance"] == "bootstrap_low_strictly_greater_than_0.5"
    assert confidence["sampling_unit_warning"] == "resample_pairs_never_individual_games"


def test_r7_endpoint_rule_fails_closed_and_preserves_r6_authority():
    payload = json.loads(RULE.read_text(encoding="utf-8"))
    assert len(payload["integrity_blockers"]) >= 5
    assert payload["decision"]["otherwise"] == "DEFER_PRIMARY_ENDPOINT_UNRESOLVED"
    assert payload["decision"]["authority"] == "prospective_design_only"
    assert payload["decision"]["r6_reinterpretation"] == "forbidden"
    assert payload["decision"]["promotion_or_classifier_effect"] == "none"
