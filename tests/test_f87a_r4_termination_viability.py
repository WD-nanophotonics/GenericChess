import json
from pathlib import Path

from scripts.f87a_r4_termination_viability import (
    BASELINE_SHA,
    MAX_PLY,
    SEARCH_NODE_CAP,
    build_prep,
    run,
)


ROOT = Path(__file__).resolve().parents[1]


def test_f87a_r4_prep_is_baseline_bound_and_capped(tmp_path):
    path = tmp_path / "manifest.json"
    build_prep(ROOT, path)
    prep = json.loads(path.read_text(encoding="utf-8"))
    assert prep["baseline_sha"] == BASELINE_SHA
    assert len(prep["controls"]) == 2
    assert prep["policy"]["game_count"] == 8
    assert prep["policy"]["max_ply"] == MAX_PLY == 128
    assert prep["policy"]["search_node_cap_per_game"] == SEARCH_NODE_CAP == 256
    assert prep["inherited_r3"]["scope"].startswith("semantic nondegeneracy")


def test_f87a_r4_keeps_censored_separate_and_records_exact_recurrence(tmp_path):
    prep_path = tmp_path / "manifest.json"
    result_dir = tmp_path / "result"
    build_prep(ROOT, prep_path)
    run(ROOT, prep_path, result_dir)
    summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
    reports = json.loads((result_dir / "reports.json").read_text(encoding="utf-8"))
    assert summary["termination_viability"]["Built-in Western Chess"] == "DEFER"
    assert summary["termination_viability"]["Built-in Standard Shogi"] == "PASS"
    assert summary["compute_usage"]["new_games"] == 8
    assert summary["compute_usage"]["search_nodes"] <= 8 * SEARCH_NODE_CAP
    for report in reports.values():
        dynamic = report["dynamic"]
        assert len(dynamic["records"]) == 4
        assert all(row["search_nodes"] <= SEARCH_NODE_CAP for row in dynamic["records"])
        assert all(row["first_player_score"] is None for row in dynamic["records"] if row["completion"] == "CENSORED")
        assert all("distinct_position_count" in row and "position_return_count" in row for row in dynamic["records"])
    western = reports["Built-in Western Chess"]
    assert western["termination_viability"]["reason"] == "ALL_TRAJECTORIES_CENSORED"
    shogi = reports["Built-in Standard Shogi"]
    assert shogi["dynamic"]["terminal_counts"] == {"repetition": 4}
    assert shogi["dynamic"]["recurrence"]["total_position_returns"] > 0
