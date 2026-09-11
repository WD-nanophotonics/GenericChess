"""Contract tests for the F83 root and teacher-cost calibration work order."""

import hashlib
import json
from pathlib import Path

from scripts import f83_c1_relative_evidence_roots_and_cost_calibration as f83


ROOT = Path(__file__).resolve().parents[1]
ROOT_CORPUS = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
PROBE = ROOT / "artifacts/f83_c1_relative_evidence/teacher_cost_probe.json"
F62_MANIFEST = ROOT / "artifacts/f83_c1_relative_evidence/f62_historical_root_identity_manifest.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f83_source_freezes_authority_and_forbids_training():
    source = (ROOT / "scripts/f83_c1_relative_evidence_roots_and_cost_calibration.py").read_text(encoding="utf-8")
    assert f83.WORK_ORDER == "GENERICCHESS-F83-C1-RELATIVE-EVIDENCE-ROOTS-AND-COST-CALIBRATION"
    assert f83.C1_ID == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert "_fit_model" not in source
    assert "optimizer" not in source.lower()
    assert "Arena" not in source
    assert "selfplay" not in source.lower()
    assert ".generic_chess_flow" not in source
    assert "estimated_teacher_calls" not in source
    assert "estimated_cpu_hours_upper_proxy" not in source
    assert f83.PV_OFFSET_RULE == "max(1, min(len(pv)-1, len(pv)//2))"


def test_f83_root_corpus_contract_after_generation():
    payload = json.loads(ROOT_CORPUS.read_text(encoding="utf-8"))
    roots = payload["roots"]
    assert payload["schema"] == "generic-chess-f83-c1-relative-root-corpus-v1"
    assert payload["c1_authority"]["c1_checkpoint_id"] == f83.C1_ID
    assert payload["role_counts"] == {"train": 36, "dev": 12, "resource_estimation_only": 6}
    assert payload["stratum_counts"] == {"reachable_random": 18, "c1_on_policy": 18, "c1_pv_corridor": 18}
    assert len(roots) == 54
    assert payload["previous_corpus_id"] == "37a323abe5935720463a8e544a23f0d5d4ce58ee14f6a75b4cece178dc8c0b0a"
    assert len(payload["root_set_identity_sha256"]) == 64
    assert payload["replay_validation"] == {
        "validated_root_count": 54,
        "all_ongoing": True,
        "all_canonical_position_keys_match": True,
        "all_position_keys_unique": True,
    }
    assert payload["f62_historical_root_identity_manifest"]["path"] == "artifacts/f83_c1_relative_evidence/f62_historical_root_identity_manifest.json"
    assert len({root["position_key"] for root in roots}) == 54
    assert all(value == 0 for value in payload["overlap_counts"].values())
    assert sorted(root["role"] for root in roots).count("resource_estimation_only") == 6
    assert all(root["role"] != "resource_estimation_only" or root["root_id"].endswith(("-r-00", "-r-01")) for root in roots)
    assert payload["generation_contract"]["c1_pv_corridor"]["pv_offset_rule"] == f83.PV_OFFSET_RULE
    assert ".generic_chess_flow" not in ROOT_CORPUS.read_text(encoding="utf-8")
    assert all("\\" not in value for key, value in payload["c1_authority"].items() if key.endswith("_path"))


def test_f83_f62_manifest_reconstructs_tracked_historical_contract():
    payload = json.loads(F62_MANIFEST.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f83-f62-historical-root-identity-v1"
    assert payload["f62_stage_identity_sha256"] == f83.F62_STAGE_SHA
    assert payload["f62_records_sha256"] == f83.F62_RECORDS_SHA
    assert payload["generation_contract"] == {
        "opening_seed": 630101,
        "corpus_seed": 630102,
        "root_count": 96,
        "source_group_count": 32,
        "roots_per_source_group": 3,
        "split_root_counts": {"fit": 48, "development": 24, "final_holdout": 24},
    }
    assert len(payload["position_keys"]) == 96
    assert len(set(payload["position_keys"])) == 96
    assert all("\\" not in value for key, value in payload["source_paths"].items() if key.endswith("_path"))
    assert ".generic_chess_flow" not in F62_MANIFEST.read_text(encoding="utf-8")


def test_f83_teacher_probe_is_resource_only_and_binds_f62_contract():
    payload = json.loads(PROBE.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f83-teacher-cost-probe-v2-lower-bound"
    assert payload["probe_contract"] == {"root_count": 6, "max_concurrent_roots": 2, "per_root_wall_cap_seconds": 180, "whole_probe_hard_wall_seconds": 720, "role": "RESOURCE_ESTIMATION_ONLY"}
    assert payload["teacher_contract"]["f62_stage_sha256"] == f83.F62_STAGE_SHA
    assert payload["teacher_contract"]["f62_records_sha256"] == f83.F62_RECORDS_SHA
    assert payload["teacher_contract"]["root_budgets"] == [2000, 40000, 80000]
    assert payload["teacher_contract"]["teacher_child_budgets"] == [1000, 10000, 20000]
    assert payload["teacher_contract"]["max_depth"] == 12
    assert payload["teacher_contract"]["tt_megabytes"] == 8
    assert payload["teacher_contract"]["root_window_pruning"] is False
    assert payload["completed_count"] + payload["capped_count"] + payload["failed_count"] == 6
    assert payload["completed_count"] == 0
    assert payload["capped_count"] == 6
    assert payload["failed_count"] == 0
    assert payload["classification"] == "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY"
    assert payload["teacher_calls"] is None
    assert payload["teacher_calls_status"] == "UNKNOWN_BECAUSE_ALL_PROBES_WERE_TERMINATED_AT_WALL_CAP"
    assert payload["lower_bound_for_48_acquisition"] == {
        "cpu_hours_lower_bound_for_48": 2.4,
        "wall_minutes_lower_bound_by_lanes": {"1": 144.0, "2": 72.0, "4": 36.0, "8": 18.0},
        "calibration_geometry_max_concurrent_roots": 2,
        "large_work_under_calibration_geometry": True,
        "higher_concurrency_unmeasured": True,
        "method": "48 roots multiplied by the 180-second per-root cap; capped samples are lower bounds, not completions",
    }
    assert all(result["status"] == "TIME_CAP" for result in payload["results"])
    assert all(result["legal_action_count"] > 0 for result in payload["results"])
    assert all(result["candidate_action_count"] is None for result in payload["results"])
    assert all(result["actual_teacher_calls"] is None for result in payload["results"])
    assert all(result["search_phase_telemetry"] is None for result in payload["results"])
    assert all(result["telemetry_unavailable_reason"] == "probe_process_terminated_at_wall_cap_before_metadata_return" for result in payload["results"])
    assert payload["classification"] in {
        "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_CALIBRATED",
        "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY",
        "HARNESS_MISMATCH",
    }
    assert "C2" not in PROBE.read_text(encoding="utf-8")
    assert ".generic_chess_flow" not in PROBE.read_text(encoding="utf-8")
