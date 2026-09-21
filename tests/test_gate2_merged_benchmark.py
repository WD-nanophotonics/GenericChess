"""Regression coverage for the single merged Gate 2 benchmark."""

from scripts.gate2_merged_benchmark import run_merged


def test_merged_gate2_benchmark_supports_basic_competence():
    result = run_merged()

    assert result["status"] == "PASS"
    assert result["classification"] == "RULE_PRIOR_ABP_BASIC_COMPETENCE_SUPPORTED"
    assert result["gate1"]["games"] == ["chess", "shogi"]
    assert len(result["generated_rulesets"]) == 5
    assert sum(len(row["trials"]) for row in result["generated_rulesets"]) == 10
    assert result["review"]["decision_count"] >= 105
    assert result["review"]["reviewed_count"] == result["review"]["decision_count"]
    assert result["first_hard_failure"] is None
