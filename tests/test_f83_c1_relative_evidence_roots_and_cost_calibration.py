"""Contract tests for the F83 root and teacher-cost calibration work order."""

import hashlib
import json
from pathlib import Path

from scripts import f83_c1_relative_evidence_roots_and_cost_calibration as f83


ROOT = Path(__file__).resolve().parents[1]
ROOT_CORPUS = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
PROBE = ROOT / "artifacts/f83_c1_relative_evidence/teacher_cost_probe.json"


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
    assert f83.PV_OFFSET_RULE == "max(1, min(len(pv)-1, len(pv)//2))"


def test_f83_root_corpus_contract_after_generation():
    payload = json.loads(ROOT_CORPUS.read_text(encoding="utf-8"))
    roots = payload["roots"]
    assert payload["schema"] == "generic-chess-f83-c1-relative-root-corpus-v1"
    assert payload["c1_authority"]["c1_checkpoint_id"] == f83.C1_ID
    assert payload["role_counts"] == {"train": 36, "dev": 12, "resource_estimation_only": 6}
    assert payload["stratum_counts"] == {"reachable_random": 18, "c1_on_policy": 18, "c1_pv_corridor": 18}
    assert len(roots) == 54
    assert payload["corpus_id"] == "37a323abe5935720463a8e544a23f0d5d4ce58ee14f6a75b4cece178dc8c0b0a"
    assert len({root["position_key"] for root in roots}) == 54
    assert all(value == 0 for value in payload["overlap_counts"].values())
    assert sorted(root["role"] for root in roots).count("resource_estimation_only") == 6
    assert all(root["role"] != "resource_estimation_only" or root["root_id"].endswith(("-r-00", "-r-01")) for root in roots)
    assert payload["generation_contract"]["c1_pv_corridor"]["pv_offset_rule"] == f83.PV_OFFSET_RULE
    assert ".generic_chess_flow" not in ROOT_CORPUS.read_text(encoding="utf-8")


def test_f83_teacher_probe_is_resource_only_and_binds_f62_contract():
    payload = json.loads(PROBE.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f83-teacher-cost-probe-v1"
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
    assert payload["estimate_for_48_acquisition_roots"]["estimated_wall_minutes_by_lanes"]["2"] > 30
    assert payload["classification"] in {
        "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_CALIBRATED",
        "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY",
        "HARNESS_MISMATCH",
    }
    assert "C2" not in PROBE.read_text(encoding="utf-8")
    assert ".generic_chess_flow" not in PROBE.read_text(encoding="utf-8")
