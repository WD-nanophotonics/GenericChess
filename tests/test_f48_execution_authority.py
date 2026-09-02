"""Contract tests for the resumed F48 execution boundary."""

from __future__ import annotations

import json
import copy
import subprocess
from pathlib import Path

import pytest

from scripts.f48_protocol import partition_input_hash, preflight, validate_raw_result


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "tests" / "fixtures" / "f48_learnable_material_recovery_results.json"
H48C = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_resolution.json"
DRIVER = ROOT / "scripts" / "audit_f48_learnable_material_recovery.py"
H48C_SHA = "742bc536f0ae2ed44e28c23b43b71a3ca859fb9f"


def test_f48_result_binds_h48c_and_preserves_early_stop():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["baseline_sha"] == H48C_SHA
    assert result["protocol"] == "H48R2A+H48R3A+H48C+R4"
    assert result["h48c_checkpoint_sha"] == H48C_SHA
    assert result["h48c_resolved_seed_triple"] == {"training": 480700, "holdout": 480703, "arena": 480708}
    assert result["final_classification"] == "MIXED_OR_UNRESOLVED"
    assert result["next_boundary"] == "F49_LEARNING_ARCHITECTURE_REASSESSMENT"
    assert result["admissible_ruleset_count"] == 0
    assert result["early_stop_status"] == "NOT_RUN_GLOBAL_PREREQUISITE_EARLY_STOP"
    assert result["execution_mode"] == "GLOBAL_PREREQUISITE_ONLY"
    assert result["F49_status"] == "NOT_STARTED"
    assert len(result["authoritative_partition_inventory"]) == 6
    assert all(item["sha256"] and item["input_hash"] for item in result["authoritative_partition_inventory"])
    assert result["production_diff"] == "ZERO"
    assert all(row["status"] == "NOT_RUN_GLOBAL_PREREQUISITE_EARLY_STOP" for row in result["rulesets"])
    assert all(row["initial_competence_status"] == "NOT_RUN_GLOBAL_PREREQUISITE_EARLY_STOP" for row in result["rulesets"])
    assert all(all(value == "NOT_RUN_PREREQUISITE_SHORTAGE" for value in row["learner_statuses"].values()) for row in result["rulesets"])
    assert all(not prior["generations"] for row in result["rulesets"] for learner in row["learners"].values() for prior in learner["by_prior"].values())


def test_f48_actual_path_equivalence_is_persisted_for_all_rulesets():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    h48c = json.loads(H48C.read_text(encoding="utf-8"))
    assert set(result["h48c_execution_equivalence"]) == set(h48c["final_corpora"])
    for ruleset_id, equivalence in result["h48c_execution_equivalence"].items():
        assert equivalence["passed"] is True
        assert equivalence["corpora"] == {
            name: {
                field: h48c["final_corpora"][ruleset_id][name][field]
                for field in ("corpus_id", "identity_set_hash", "identity_set_count")
            }
            for name in ("training", "holdout", "arena")
        }
        assert equivalence["pairwise_intersections"] == {
            "training_holdout": [],
            "training_arena": [],
            "holdout_arena": [],
        }


def test_f48_clean_prerequisite_efficiency_is_total_and_derived():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    expected = {
        "A_CANONICAL_WESTERN_CHESS": (832, 13, 832, 704),
        "B_CANONICAL_STANDARD_SHOGI": (1856, 29, 1856, 1728),
        "C_H48B_SELECTED_GENERATED": (704, 11, 704, 576),
    }
    for row in result["rulesets"]:
        search_count, table_count, engine_count, student_budget_count = expected[row["ruleset_id"]]
        efficiency = row["efficiency"]
        assert (efficiency["search_count"], efficiency["evaluation_table_compile_count"], efficiency["engine_creation_count"]) == (search_count, table_count, engine_count)
        assert efficiency["requested_node_budgets"] == {"2000": student_budget_count, "20000": 64, "40000": 64}
        assert efficiency["ledger_scope"] == "TOTAL_AUTHORITATIVE_PREREQUISITE_COST"
        assert efficiency["authoritative_total_work"] is True
        assert efficiency["current_process_execution_cost_seconds"] == efficiency["total_authoritative_prerequisite_cost_seconds"] == efficiency["total_prerequisite_wall_seconds"]
        assert efficiency["nodes_per_second"] > 0
        assert efficiency["learning_fraction_status"] == "NOT_APPLICABLE_PREREQUISITE_ONLY"
        assert efficiency["non_native_learning_fraction"] == 0.0
        assert efficiency["fraction_outside_native_search"] >= 0.0


def test_f48_preflight_binds_h48c_and_invalid_old_partitions_cannot_reuse():
    plan = preflight()
    assert plan["authority"]["artifacts"]["h48c"]["commit"] == H48C_SHA
    corpus_partition = next(row for row in plan["partitions"] if row["phase"] == "corpus")
    old_config = {
        "search": plan["config"]["search"],
        "corpora": {
            "training": [64, 480700, 2, 6],
            "holdout": [64, 480701, 2, 6],
            "arena": [16, 480702, 2, 6],
        },
        "holdout_in_ranking": False,
    }
    assert corpus_partition["input_hash"] != partition_input_hash(corpus_partition, config=old_config)


def test_f48_driver_uses_h48c_config_and_keeps_production_immutable():
    source = DRIVER.read_text(encoding="utf-8")
    assert "load_h48c_resolution" in source
    assert "_verify_h48c_execution_equivalence" in source
    assert "generate_arena_openings" in source
    assert "generate_diagnostic_corpus" in source
    assert "STOP_ON_H48C_EXECUTION_DISCREPANCY" in source
    assert "seed=480701" not in source and "seed=480702" not in source
    assert subprocess.run(["git", "diff", "--quiet", H48C_SHA, "HEAD", "--", "generic_chess"], cwd=ROOT).returncode == 0


def test_f48_validation_rejects_boundary_and_early_stop_drift():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    boundary_drift = copy.deepcopy(result)
    boundary_drift["next_boundary"] = "F49_LEARNABLE_MATERIAL_CALIBRATION_INTEGRATION"
    with pytest.raises(RuntimeError, match="classification-to-boundary"):
        validate_raw_result(boundary_drift)
    early_stop_drift = copy.deepcopy(result)
    early_stop_drift["rulesets"][0]["initial_competence_status"] = "EXECUTED"
    with pytest.raises(RuntimeError, match="initial competence"):
        validate_raw_result(early_stop_drift)


def test_f48_validation_rejects_efficiency_and_inventory_drift():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    efficiency_drift = copy.deepcopy(result)
    efficiency_drift["rulesets"][0]["efficiency"]["search_count"] += 1
    with pytest.raises(RuntimeError, match="search count"):
        validate_raw_result(efficiency_drift)
    inventory_drift = copy.deepcopy(result)
    inventory_drift["authoritative_partition_inventory"][0]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="partition hash"):
        validate_raw_result(inventory_drift)
