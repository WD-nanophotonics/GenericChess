from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from scripts.f94_r6_fallback_forensics import (
    EXPECTED_PROGRESS_EVIDENCE_SHA256,
    EXPECTED_RESULT_SHA256,
    FORENSICS_SCHEMA,
    classify_fallback,
    extract,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
PROGRESS = ROOT / ".generic_chess_flow/f94-r6-progress"


def test_fallback_forensics_is_deterministic_and_bound_to_r6_evidence():
    first = extract(RESULT, PROGRESS)
    second = extract(RESULT, PROGRESS)
    assert first == second
    assert first["schema"] == FORENSICS_SCHEMA
    assert first["source_result_sha256"] == EXPECTED_RESULT_SHA256
    assert first["progress_evidence_sha256"] == EXPECTED_PROGRESS_EVIDENCE_SHA256
    assert first["fallback_count"] == 29
    assert first["fallback_category_counts"] == {
        "LOW_BUDGET_PRE_ITERATION_NODE_FALLBACK": 29,
    }
    assert first["fallback_role_counts"] == {"parent": 29}
    assert first["fallback_matchup_counts"] == {"1024_vs_256": 29}
    assert first["blocking_or_review_count"] == 0
    assert first["all_observed_fallbacks_are_low_budget_pre_iteration"] is True
    assert set(first["invocation_counts"]) == {
        "standard_shogi-1024_vs_256-9801-b4412a283291e4d1",
        "standard_shogi-1024_vs_256-9802-ea38e5d456cb931c",
    }


def test_fallback_records_have_required_identity_and_search_fields():
    payload = extract(RESULT, PROGRESS)
    required = {
        "control", "matchup", "tape_seed", "pair_index", "child_owner",
        "decision_index", "ply", "engine_role", "nodes_budget", "nodes",
        "completed_depth", "termination_reason", "decision_kind",
    }
    for row in payload["fallback_records"]:
        assert required <= row.keys()
        assert row["used_fallback"] is True
        assert row["decision_kind"] == "action"
        assert row["ply"] == row["decision_index"]
        assert row["nodes_budget"] == 256
        assert row["completed_depth"] == 0
        assert row["termination_reason"] == "node_budget"
        assert row["source_result_sha256"] == EXPECTED_RESULT_SHA256
        assert row["progress_evidence_sha256"] == EXPECTED_PROGRESS_EVIDENCE_SHA256


def test_response_matrix_is_aligned_and_reversal_summary_is_explicit():
    payload = extract(RESULT, PROGRESS)
    matrix = payload["response_matrix"]
    assert len(matrix) == 36
    assert {(row["control"], row["tape_seed"], row["pair_index"]) for row in matrix}.__len__() == 36
    summary = payload["western_response_summary"]
    assert summary["rows"] == 18
    assert summary["scores_le_half"] == 11
    assert summary["strict_negative_scores"] == 2
    assert summary["score_le_half_pair_indices"] == [0, 1, 2, 3, 4, 5]
    assert summary["strict_negative_tape_seeds"] == [9803]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            dict(engine_role="parent", nodes_budget=256, completed_depth=0, termination_reason="node_budget", decision_kind="action"),
            "LOW_BUDGET_PRE_ITERATION_NODE_FALLBACK",
        ),
        (
            dict(engine_role="child", nodes_budget=4096, completed_depth=0, termination_reason="node_budget", decision_kind="action"),
            "HIGH_BUDGET_PRE_ITERATION_NODE_FALLBACK",
        ),
        (
            dict(engine_role="child", nodes_budget=1024, completed_depth=0, termination_reason="internal_error", decision_kind="action"),
            "OPERATIONAL_OR_ABORT_FALLBACK",
        ),
        (
            dict(engine_role="child", nodes_budget=1024, completed_depth=1, termination_reason="node_budget", decision_kind="action"),
            "POST_ITERATION_FALLBACK_REQUIRES_REVIEW",
        ),
    ],
)
def test_fallback_classification_keeps_operational_and_budget_cases_separate(kwargs, expected):
    assert classify_fallback(**kwargs) == expected


def test_fallback_forensics_rejects_progress_mutation(tmp_path: Path):
    copied = tmp_path / "progress"
    shutil.copytree(PROGRESS, copied)
    source = next(copied.glob("standard_shogi-1024_vs_256-9801-*/pair-000005.json"))
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["game_child_owner1"]["search_metrics"][55]["used_fallback"] = False
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="progress evidence SHA mismatch"):
        extract(RESULT, copied)


def test_fallback_forensics_rejects_result_mutation(tmp_path: Path):
    tampered = tmp_path / "result.json"
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    payload["authority"] = "tampered"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="source SHA mismatch"):
        extract(tampered, PROGRESS)
