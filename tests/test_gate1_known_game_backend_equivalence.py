"""Tests for the Gate 1 known-game differential benchmark."""

from scripts.gate1_known_game_backend_equivalence import run_gate1


def test_gate1_covers_both_games_and_production_sanity():
    result = run_gate1()

    assert result["status"] == "PASS"
    assert result["first_hard_fork"] is None
    assert result["corpus_counts"] == {"chess": 12, "shogi": 12}
    assert result["depth_2_counts"] == {"chess": 12, "shogi": 12}
    assert result["depth_3_counts"] == {"chess": 4, "shogi": 4}
    assert all(
        row["hard_fork"] is None
        for rows in result["rows"].values()
        for row in rows
    )
    assert all(
        item["selected_is_legal"]
        for item in result["production_sanity"].values()
    )
