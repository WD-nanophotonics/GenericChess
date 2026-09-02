"""Contract tests for the resumed F48 execution boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.f48_protocol import partition_input_hash, preflight


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "tests" / "fixtures" / "f48_learnable_material_recovery_results.json"
H48C = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_resolution.json"
DRIVER = ROOT / "scripts" / "audit_f48_learnable_material_recovery.py"
H48C_SHA = "742bc536f0ae2ed44e28c23b43b71a3ca859fb9f"


def test_f48_result_binds_h48c_and_preserves_early_stop():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["baseline_sha"] == H48C_SHA
    assert result["protocol"] == "H48R2A+H48R3A+H48C"
    assert result["h48c_checkpoint_sha"] == H48C_SHA
    assert result["h48c_resolved_seed_triple"] == {"training": 480700, "holdout": 480703, "arena": 480708}
    assert result["final_classification"] == "MIXED_OR_UNRESOLVED"
    assert result["production_diff"] == "ZERO"
    assert all(row["status"] == "NOT_RUN_PREREQUISITE_INVALID" for row in result["rulesets"])
    assert all(not learner["generations"] for row in result["rulesets"] for learner in row["learners"].values() for learner in learner["by_prior"].values())


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
