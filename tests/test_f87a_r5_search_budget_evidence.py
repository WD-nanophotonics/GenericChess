import json
from pathlib import Path

from scripts.f87a_r5_search_budget_evidence import (
    BASELINE_SHA,
    SEARCH_DEPTH,
    SEARCH_NODE_CAP,
    build_prep,
    run,
)


ROOT = Path(__file__).resolve().parents[1]


def test_f87a_r5_prep_freezes_budget_and_terminal_utility(tmp_path):
    path = tmp_path / "manifest.json"
    build_prep(ROOT, path)
    prep = json.loads(path.read_text(encoding="utf-8"))
    assert prep["baseline_sha"] == BASELINE_SHA
    assert prep["policy"]["search_depth"] == SEARCH_DEPTH == 1
    assert prep["policy"]["search_node_cap_per_game"] == SEARCH_NODE_CAP == 256
    assert "first_budget_exhausted_ply" in prep["required_evidence"]
    assert prep["policy"]["terminal_utility"].endswith("CENSORED null")


def test_f87a_r5_records_explicit_fallback_and_independence_evidence(tmp_path):
    prep_path = tmp_path / "manifest.json"
    result_dir = tmp_path / "result"
    build_prep(ROOT, prep_path)
    run(ROOT, prep_path, result_dir)
    summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
    reports = json.loads((result_dir / "reports.json").read_text(encoding="utf-8"))
    assert summary["compute_usage"]["new_games"] == 8
    assert summary["trajectory_independence"] == {"Built-in Standard Shogi": "DEFER", "Built-in Western Chess": "DEFER"}
    for report in reports.values():
        dynamic = report["dynamic"]
        assert dynamic["trajectory_independence"]["unique_action_sequence_count"] == 1
        assert report["search_budget"]["searched_ply_count"] > 0
        assert report["search_budget"]["fallback_ply_count"] > 0
        assert all(row["first_budget_exhausted_ply"] is not None for row in dynamic["records"])
        assert all(row["search_nodes"] <= SEARCH_NODE_CAP for row in dynamic["records"])
        assert report["terminal_utility_policy"] == "winner utility +/-1; terminal without winner 0.0; CENSORED null"
    shogi = reports["Built-in Standard Shogi"]
    assert all(row["terminal_status"] == "repetition" and row["terminal_utility"] == 0.0 for row in shogi["dynamic"]["records"])
    western = reports["Built-in Western Chess"]
    assert all(row["terminal_status"] == "CENSORED" and row["terminal_utility"] is None for row in western["dynamic"]["records"])
