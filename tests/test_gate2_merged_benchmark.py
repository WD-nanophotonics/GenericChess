"""Regression coverage for the single merged Gate 2 benchmark."""

from scripts.gate2_merged_benchmark import run_merged


def test_merged_gate2_benchmark_enforces_corrected_competence_contract():
    result = run_merged()

    assert result["gate1"]["games"] == ["chess", "shogi"]
    assert len(result["capability"]) >= 1
    assert result["review"]["primary_node_budget"] == 1000
    assert result["review"]["weak_node_budget"] == 128
    assert result["review"]["review_node_budget"] == 8000
    assert result["review"]["trend_plies"] == (10, 20, 30)

    first = result["first_hard_failure"]
    assert result["status"] in {"PASS", "FIRST_HARD_FAILURE"}
    if first is None:
        assert result["status"] == "PASS"
        assert result["classification"] == "RULE_PRIOR_ABP_BASIC_COMPETENCE_SUPPORTED"
        assert len(result["short_games"]) == 28
        assert result["review"]["decision_count"] > 0
        assert set(result["review"]["trends"]) == {"10", "20", "30"}
    else:
        assert result["status"] == "FIRST_HARD_FAILURE"
        assert result["classification"].startswith("RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_")
        assert first["layer"] in {"capability", "short_game", "review_metric"}

    task_names = {
        name
        for row in result["capability"]
        for name in row["capability"]["tasks"]
    }
    assert {"mate_in_one", "mate_in_three", "avoid_immediate_mate", "material_take", "mobility", "anchor_danger"} <= task_names
