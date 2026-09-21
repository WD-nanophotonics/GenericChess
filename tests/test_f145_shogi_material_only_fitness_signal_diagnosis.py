from __future__ import annotations

from scripts.f145_shogi_material_only_fitness_signal_diagnosis import (
    _classification,
    diagnostic_vectors,
    summarize_pairs,
)


def test_f145_reproduces_f144_mutant_and_scales_same_direction():
    vectors = diagnostic_vectors()
    assert vectors["Gen0"] == (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    assert vectors["M035"] == (315, 988, 1000, 5084, 310, 1037, 4658, 723, 2043, 3198, 1905, 975, 214)
    assert vectors["M070"] != vectors["M035"]
    assert vectors["M140"] != vectors["M070"]


def test_f145_summary_keeps_no_contest_non_scoring_and_reports_terminal_stats():
    rows = [
        {
            "pair_index": 0,
            "opening_id": "a",
            "games": [
                {"child_owner": 0, "winner": None, "result": "repetition", "plies": 120},
                {"child_owner": 1, "winner": None, "result": "no_contest", "plies": 500},
            ],
            "pair_score": None,
        },
        {
            "pair_index": 1,
            "opening_id": "b",
            "games": [
                {"child_owner": 0, "winner": 0, "result": "checkmate", "plies": 80},
                {"child_owner": 1, "winner": 0, "result": "checkmate", "plies": 81},
            ],
            "pair_score": 0.5,
        },
    ]
    summary = summarize_pairs(rows)
    assert summary["no_contests"] == 1
    assert summary["non_scoring_pair_count"] == 1
    assert summary["terminal_status_histogram"] == {
        "checkmate": 2,
        "no_contest": 1,
        "repetition": 1,
    }
    assert summary["non_0_5_scoring_pair_count"] == 0
    assert summary["games_reaching_plies"]["100"] == 0.5


def test_f145_routing_prefers_first_supported_cause():
    probes = {
        "1000": {"comparisons": {"M140": {"best_action_disagreement_rate": 0.01}}},
        "4000": {"comparisons": {"M140": {"best_action_disagreement_rate": 0.01}}},
    }
    assert _classification(True, False, False, probes) == "MATERIAL_ONLY_F144_FAILURE_MUTATION_SIGNAL_TOO_WEAK"
    assert _classification(False, True, False, probes) == "MATERIAL_ONLY_F144_FAILURE_SEARCH_BUDGET_TOO_SHALLOW"
    assert _classification(False, False, True, probes) == "MATERIAL_ONLY_F144_FAILURE_OPENING_DISTRIBUTION_TOO_QUIET"
    assert _classification(False, False, False, {"1000": {"comparisons": {"M140": {"best_action_disagreement_rate": 0.2}}}, "4000": {"comparisons": {"M140": {"best_action_disagreement_rate": 0.0}}}}) == "MATERIAL_ONLY_DECISIONS_CHANGE_BUT_STRENGTH_SIGNAL_DOES_NOT_CONVERT"
    assert _classification(False, False, False, probes) == "MATERIAL_ONLY_EVALUATOR_HAS_INSUFFICIENT_ABP_DECISION_LEVERAGE"
