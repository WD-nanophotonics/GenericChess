"""Contract tests for the bounded F84 extended calibration."""

import json
from pathlib import Path

import pytest

from scripts import f84_c1_teacher_extended_cost_calibration as f84


ROOT = Path(__file__).resolve().parents[1]
ROOT_CORPUS = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
CALIBRATION = ROOT / "artifacts/f84_c1_teacher_extended_calibration/calibration.json"


def test_f84_source_is_bounded_and_does_not_change_science_route():
    source = (ROOT / "scripts/f84_c1_teacher_extended_cost_calibration.py").read_text(encoding="utf-8")
    assert f84.WORK_ORDER == "GENERICCHESS-F84-C1-TEACHER-EXTENDED-COST-CALIBRATION"
    assert f84.ROOT_IDS == ("reachable_random-r-00", "c1_on_policy-r-00", "c1_pv_corridor-r-00")
    assert f84.MAX_CONCURRENT_ROOTS == 2
    assert f84.PER_ROOT_WALL_SECONDS == 720
    assert f84.WHOLE_STAGE_HARD_WALL_SECONDS == 1500
    assert "training" not in source.lower()
    assert "optimizer" not in source.lower()
    assert "Arena" not in source
    assert "selfplay" not in source.lower()
    assert "external engine" not in source.lower()
    assert ".generic_chess_flow" not in source


def test_f84_selects_only_frozen_resource_roots_and_reuses_identity():
    payload = json.loads(ROOT_CORPUS.read_text(encoding="utf-8"))
    roots = [root for root in payload["roots"] if root["root_id"] in f84.ROOT_IDS]
    assert [root["root_id"] for root in roots] == list(f84.ROOT_IDS)
    assert all(root["role"] == "resource_estimation_only" for root in roots)
    assert payload["root_set_identity_sha256"] == f84.F83_ROOT_SET_ID
    assert len({root["position_key"] for root in roots}) == 3


def test_f84_calibration_artifact_contract_after_single_stage():
    if not CALIBRATION.exists():
        pytest.skip("F84 Heavy stage has not run yet")
    payload = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f84-c1-teacher-extended-calibration-v1"
    assert payload["work_order"] == f84.WORK_ORDER
    assert payload["f83_authority"]["root_set_identity_sha256"] == f84.F83_ROOT_SET_ID
    assert payload["execution_contract"]["root_ids"] == list(f84.ROOT_IDS)
    assert payload["execution_contract"]["max_concurrent_roots"] == 2
    assert payload["execution_contract"]["per_root_wall_cap_seconds"] == 720
    assert payload["execution_contract"]["whole_stage_hard_wall_seconds"] == 1500
    assert payload["execution_contract"]["no_retry"] is True
    assert payload["execution_contract"]["no_persisted_teacher_targets"] is True
    assert len(payload["results"]) == 3
    assert [row["root_id"] for row in payload["results"]] == list(f84.ROOT_IDS)
    assert all(row["role"] == "resource_estimation_only" for row in payload["results"])
    assert payload["completed_count"] + payload["capped_count"] + payload["failed_count"] == 3
    assert payload["classification"] in {
        "C1_TEACHER_COST_EXTENDED_CALIBRATED",
        "C1_TEACHER_COST_PARTIALLY_CALIBRATED",
        "C1_TEACHER_COST_EXTENDED_LOWER_BOUND_ONLY",
        "HARNESS_MISMATCH",
    }
    for row in payload["results"]:
        assert row["legal_action_count"] > 0
        if row["status"] == "COMPLETE":
            assert 0 < row["selected_action_count"] <= f84.MAX_SELECTED_ACTIONS
            assert row["actual_teacher_calls"] == 2 * row["selected_action_count"]
            assert row["actual_search_calls"] == 4 + row["legal_action_count"] + 2 * row["selected_action_count"]
            assert set(row["root_search_summaries"]) == {"root_2k", "root_40k", "root_80k", "observer_2k"}
            assert row["declared_total_search_node_budget"] <= f84.MAX_ROOT_NODE_BUDGETS[row["stratum"]]
        elif row["status"] == "TIME_CAP":
            assert row["selected_action_count"] is None
            assert row["actual_teacher_calls"] is None
            assert row["actual_search_calls"] is None
            assert row["root_search_summaries"] is None
            assert row["telemetry_unavailable_reason"]
    assert "q_20k" not in CALIBRATION.read_text(encoding="utf-8")
    assert ".generic_chess_flow" not in CALIBRATION.read_text(encoding="utf-8")
