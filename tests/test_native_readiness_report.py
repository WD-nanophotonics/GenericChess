"""Report writers and aggregation correctness."""

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.ai.benchmark.audit_report import (
    merge_summaries,
    render_markdown,
    write_reports,
    write_csv_detail,
)
from generic_chess.ai.benchmark.audit_schema import medians_min_max
from generic_chess.ai.benchmark.audit_schema import validate_latest_summary
from generic_chess.ai.benchmark.native_readiness import _aggregate_budget


def test_medians_min_max():
    assert medians_min_max([])["count"] == 0
    assert medians_min_max([3, 1, 2])["median"] == 2
    assert medians_min_max([4, 1, 2, 3])["median"] == 2.5
    assert medians_min_max([5, 1, 9])["min"] == 1
    assert medians_min_max([5, 1, 9])["max"] == 9


def test_markdown_generated_without_optional_blocks():
    summary = {
        "environment": {"os": "test", "python": "3.x", "cpu": "x", "logical_cpus": 2, "commit": "x", "debug_build": False},
        "suite": {
            "name": "smoke-v1",
            "ruleset_count": 2,
            "position_count": 5,
            "board_sizes": [4, 6],
            "movement_buckets": [],
            "promotion_buckets": [],
            "drop_buckets": [],
            "categories_covered": [],
            "categories_missing": [],
        },
        "node_budget": {
            "1000": {
                "fixtures": 5,
                "results": [
                    {
                        "fixture_id": "f",
                        "nodes_per_second": 100.0,
                        "completed_depth": 2,
                        "qnode_ratio": 0.5,
                        "tt_probes": 10,
                        "tt_hits": 5,
                        "fallback": False,
                        "board_size": 4,
                        "movement_buckets": [],
                    }
                ],
                "summary": {
                    "runs": 1,
                    "nodes_per_second": {"median": 100.0},
                    "completed_depth": {"median": 2.0},
                    "qnode_ratio": {"median": 0.5},
                    "tt_hit_rate": {"median": 0.5},
                    "fallback_runs": 0,
                    "by_board_size": {},
                    "by_movement_bucket": {},
                },
            }
        },
        "instrumented": [],
        "core_profiling": [],
        "cache": [],
        "conclusions": {},
    }
    text = render_markdown(summary)
    assert "## 1. 环境" in text
    assert "smoke-v1" in text
    assert "instrumentation" in text


def test_write_reports_and_csv():
    base = Path(__file__).resolve().parent.parent
    tmp_path = base / f".gc_report_tmp_{uuid.uuid4().hex}"
    os.makedirs(tmp_path, mode=0o777)
    summary = {
        "environment": {},
        "suite": {},
        "node_budget": {
            "1000": {
                "fixtures": 1,
                "results": [{"fixture_id": "f", "nodes_per_second": 1.0}],
                "summary": {},
            }
        },
        "instrumented": [],
        "core_profiling": [],
        "cache": [],
        "conclusions": {},
    }
    out = tmp_path / "report"
    write_reports(summary, out)
    assert (out / "native_readiness_latest.json").exists()
    assert (out / "native_readiness_latest.md").exists()
    csv_path = tmp_path / "detail.csv"
    write_csv_detail(summary, csv_path)
    assert csv_path.exists()
    assert json.loads((out / "native_readiness_latest.json").read_text(encoding="utf-8"))
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_merge_summaries_combines_budgets():
    base = {
        "node_budget": {"10000": {"fixtures": 5, "results": [], "summary": {}}},
        "instrumented": [],
        "conclusions": {"a": 1},
    }
    extra = {
        "node_budget": {"100000": {"fixtures": 3, "results": [], "summary": {}}},
        "instrumented": [{"fixture_id": "x"}],
        "conclusions": {"a": 2},
    }
    merged = merge_summaries(base, extra)
    assert set(merged["node_budget"]) == {"10000", "100000"}
    assert merged["instrumented"][0]["fixture_id"] == "x"
    assert merged["conclusions"]["a"] == 2


def test_merge_keeps_base_budget_when_present():
    base = {
        "node_budget": {"10000": {"fixtures": 15, "results": [], "summary": {}}},
        "instrumented": [],
        "conclusions": {},
    }
    extra = {
        "node_budget": {"10000": {"fixtures": 4, "results": [], "summary": {}}},
        "instrumented": [{"fixture_id": "x"}],
        "conclusions": {},
    }
    merged = merge_summaries(base, extra)
    assert merged["node_budget"]["10000"]["fixtures"] == 15  # base wins
    assert merged["instrumented"][0]["fixture_id"] == "x"


def test_latest_summary_schema_v2_required():
    v1 = {"schema_version": 1, "environment": {}, "suite": {}, "node_budget": {}}
    with pytest.raises(ValueError, match="schema_version"):
        validate_latest_summary(v1)
    v2 = {
        "schema_version": 2,
        "environment": {},
        "suite": {
            "executed_ruleset_count": 2,
            "executed_position_count": 5,
        },
        "requested_budget_tiers": [1000],
        "completed_budget_tiers": [1000],
        "node_budget": {
            "1000": {
                "results": [
                    {
                        "main_nodes": 100,
                        "qnodes": 50,
                        "total_nodes": 150,
                        "main_nps": 10.0,
                        "q_nps": 5.0,
                        "total_nps": 15.0,
                    }
                ]
            }
        },
    }
    validate_latest_summary(v2)


def test_aggregate_budget_reports_all_nps_metrics():
    rows = [
        {
            "fixture_id": "f",
            "main_nodes": 100,
            "qnodes": 900,
            "total_nodes": 1000,
            "main_nps": 10.0,
            "q_nps": 90.0,
            "total_nps": 100.0,
            "nodes_per_second": 100.0,
            "qnode_ratio": 9.0,
            "qnode_share": 0.9,
            "completed_depth": 3,
            "tt_probes": 100,
            "tt_hits": 10,
            "fallback": False,
            "board_size": 4,
            "movement_buckets": ["ray_heavy"],
        }
    ]
    agg = _aggregate_budget(rows)
    assert agg["total_nps"]["median"] == 100.0
    assert agg["main_nps"]["median"] == 10.0
    assert agg["q_nps"]["median"] == 90.0
    assert agg["qnode_share"]["median"] == 0.9
    assert agg["qnode_ratio"]["median"] == 9.0
