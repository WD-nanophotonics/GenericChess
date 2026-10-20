"""Small contract tests for the one-rule rules15 comparison route."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from results.dev_aux.task2628.analyze import bounds
from results.dev_aux.task2628.evaluate import validate_plan_contract as validate_eval
from results.dev_aux.task2628.train import validate_plan_contract as validate_train

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2628"


def test_source_pinned_rules15_panel_contract():
    pool_path = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
    audit_path = ROOT / "results/dev_aux/task2627/rule15-successor-pool-audit.json"
    pool_raw, audit_raw = pool_path.read_bytes(), audit_path.read_bytes()
    pool, audit = json.loads(pool_raw), json.loads(audit_raw)
    assert pool["status"] == "OUTCOME_BLIND_MECHANISM_ACTIVE_ROOTS_PREPARED_NOT_REGISTERED"
    assert audit["status"] == "PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_MECHANISM_FEATURE_AND_SPLIT_AUDIT"
    assert audit["pool_sha256"] == hashlib.sha256(pool_raw).hexdigest()
    assert audit["training_roots"] == 120 and audit["evaluation_roots"] == 16
    assert audit["exact_prior_intersections"] == 0
    assert audit["exact_training_evaluation_intersections"] == 0
    assert audit["legal_unlock_action_availability"]["training"]["roots_with_legal_unlock_action"] == 120
    assert audit["legal_unlock_action_availability"]["evaluation"]["roots_with_legal_unlock_action"] == 16
    assert all(row["rule_index"] == 15 for row in pool["training_roots"] + pool["evaluation_roots"])


def test_one_rule_training_and_evaluation_slot_contract():
    training = {
        "nodes_per_arm_candidate_plus_foe": 250_000,
        "arms": 4,
        "roots_per_rule": 120,
        "H": 128,
        "max_episodes_per_arm": 512,
        "hard_seconds": 1800,
    }
    search = {"nodes_per_query": 2048, "depth": 2}
    initial = {f"15:{seed}": [1.0, 1.0] for seed in (1977, 8173, 27182, 31415)}
    validate_train({"training": training, "search": search, "initialization": {"weights_by_rule_seed": initial}})
    evaluation = {
        "slots": 256,
        "H": 128,
        "hard_seconds": 1800,
        "node_cap_by_rule_family": {f"15:{family}": 20_000 for family in range(16)},
    }
    validate_eval({"evaluation": evaluation, "search": {"nodes_per_query": 8192, "depth": 2}})


def test_unknown_is_never_imputed_as_draw():
    assert bounds(None, None) == (-2, 2)
    assert bounds(None, 0) == (-1, 1)
    assert bounds(1, 0) == (1, 1)
