import json
from pathlib import Path

from scripts.f87a_r6_termination_control import (
    BASELINE_SHA,
    MAX_PLY,
    PAIR_COUNT,
    POLICIES,
    ROOT_NODE_CAP_PER_PLY,
    build_prep,
    run,
)


ROOT = Path(__file__).resolve().parents[1]


def test_f87a_r6_prep_freezes_complete_root_budget(tmp_path):
    path = tmp_path / "manifest.json"
    build_prep(ROOT, path)
    prep = json.loads(path.read_text(encoding="utf-8"))
    assert prep["baseline_sha"] == BASELINE_SHA
    assert tuple(prep["policies"]) == POLICIES
    assert prep["pair_count"] == PAIR_COUNT == 2
    assert prep["max_ply"] == MAX_PLY == 128
    assert prep["root_node_cap_per_ply"] == ROOT_NODE_CAP_PER_PLY == 64
    assert "complete root set" in prep["budget_rule"]


def test_f87a_r6_separates_budget_censoring_terminals_and_pure_sequences(tmp_path):
    prep_path = tmp_path / "manifest.json"
    result_dir = tmp_path / "result"
    build_prep(ROOT, prep_path)
    run(ROOT, prep_path, result_dir)
    summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
    reports = json.loads((result_dir / "reports.json").read_text(encoding="utf-8"))
    assert summary["compute_usage"]["new_games"] == 16
    assert summary["compute_usage"]["new_games"] == sum(
        report["dynamic"]["game_count"] for report in reports.values()
    )
    for report in reports.values():
        assert report["pure_sequence_diversity"]["unique_action_sequence_count"] == 2
        assert report["pure_sequence_diversity"]["control_distinct_sequence_count"] == 2
        assert report["search_budget_censorship"] == {policy: 0 for policy in POLICIES}
        assert report["dynamic"]["game_count"] == 8
        for policy in POLICIES:
            dynamic = report["dynamic"]["policies"][policy]
            assert all("move_sequence_sha256" in row and "execution_trace_sha256" in row for row in dynamic["records"])
            assert all(row["terminal_utility"] in {None, -1.0, 0.0, 1.0} for row in dynamic["records"])
    assert reports["Built-in Standard Shogi"]["termination_viability"]["deterministic_complete_root_material_search"]["status"] == "PASS"
    assert reports["Built-in Western Chess"]["termination_viability"]["deterministic_complete_root_material_search"]["status"] == "DEFER"
    assert reports["Built-in Western Chess"]["search_coverage"]["deterministic_complete_root_material_search"]["fraction"] == 1.0
