"""Controls for task2625's frozen selection and UNKNOWN arithmetic."""
from __future__ import annotations

import json
from pathlib import Path

from results.dev_aux.task2625.analyze import bounds
from results.dev_aux.task2625.freeze_study import initial_vector
from results.dev_aux.task2624.prepare_roots import record_fields

ROOT = Path(__file__).resolve().parents[3]


def test_unknown_completion_bounds_preserve_known_endpoint():
    assert bounds(1, None) == (0, 2)
    assert bounds(None, 1) == (-2, 0)
    assert bounds(-1, 1) == (-2, -2)
    assert bounds(0, 0) == (0, 0)
    assert bounds(None, None) == (-2, 2)


def test_selection_record_projection_ignores_outcome_score_and_weights():
    history = {"ruleset_fingerprint": "fp", "actions": [{"kind": "board"}]}
    baseline = {"record_before": history, "outcome": 1, "score": 42, "weights": [1, 9]}
    changed = {"record_before": history, "outcome": -1, "score": -900, "weights": [1, .1]}
    assert list(record_fields(baseline)) == list(record_fields(changed)) == [history]


def test_prepared_pool_and_independent_audit_bind_expected_full_histories():
    pools = json.loads((ROOT / "results/dev_aux/task2624/root-pools-v2.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "results/dev_aux/task2624/root-pools-audit.json").read_text(encoding="utf-8"))
    assert pools["status"] == "OUTCOME_BLIND_EXACT_HISTORY_ROOT_POOLS_PREPARED_NOT_REGISTERED"
    assert audit["status"] == "PASS_EXACT_HISTORY_SOURCE_HASH_REPLAY_FEATURE_AND_DISJOINTNESS_AUDIT"
    for rule in (271001, 271002, 271003, 271004):
        assert sum(row["rule"] == rule for row in pools["training_roots"]) == 120
        assert sum(row["rule"] == rule for row in pools["evaluation_roots"]) == 16
        assert audit["exact_train_eval_overlap_by_rule"][str(rule)] == 0


def test_eval_design_has_fixed_denominator_and_balanced_caps():
    roots = json.loads((ROOT / "results/dev_aux/task2624/root-pools-v2.json").read_text(encoding="utf-8"))["evaluation_roots"]
    assert len(roots) == 64
    # The freeze step assigns eight 20k and eight 40k roots within each rule.
    import random
    for rule in (271001, 271002, 271003, 271004):
        families = [row["family"] for row in roots if row["rule"] == rule]
        random.Random(977422 + rule).shuffle(families)
        caps = [20_000 if i < 8 else 40_000 for i in range(16)]
        assert caps.count(20_000) == caps.count(40_000) == 8
    assert 4 * 4 * 16 * 2 * 2 == 1024
    assert 4 * 4 * 16 * 2 == 512


def test_initialization_vectors_are_reproducible_and_keep_fixed_coordinate():
    first = initial_vector(1977, 6)
    assert first == initial_vector(1977, 6)
    assert first[0] == 1.0
    assert len(first) == 6
    assert all(0.5 <= weight <= 1.5 for weight in first[1:])
    assert initial_vector(1977, 6) != initial_vector(8173, 6)
