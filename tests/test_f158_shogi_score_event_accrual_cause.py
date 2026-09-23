import ast
from pathlib import Path

from scripts import f158_shogi_score_event_accrual_cause as diagnostic


def test_counterfactual_thresholds_follow_recorded_score_sequence():
    actions = [
        {"actor": 0, "points": 1},
        {"actor": 1, "points": 2},
        {"actor": 0, "points": 0},
        {"actor": 1, "points": 1},
    ]
    rows = diagnostic._counterfactual_thresholds(actions)
    assert rows[0]["first_reach"] == {"scored_ply": 1, "side": 0, "scores": [1, 0]}
    assert rows[1]["first_reach"] == {"scored_ply": 2, "side": 1, "scores": [1, 2]}
    assert rows[2]["first_reach"] == {"scored_ply": 4, "side": 1, "scores": [1, 3]}
    assert rows[3]["first_reach"] is None
    assert not rows[4]["reached_on_recorded_trajectory"]


def test_zero_intervals_quantiles_and_positive_ply_fraction():
    actions = [
        {"actor": 0, "points": 0, "capture": 0, "check": 0, "action": {"actor_type_id": "P", "from": [0, 0], "to": [0, 1]}},
        {"actor": 1, "points": 1, "capture": 1, "check": 0, "action": {"actor_type_id": "P", "from": [1, 1], "to": [0, 1]}},
        {"actor": 0, "points": 0, "capture": 0, "check": 0, "action": {"actor_type_id": "G", "from": [2, 2], "to": [2, 1]}},
        {"actor": 1, "points": 0, "capture": 0, "check": 0, "action": {"actor_type_id": "G", "from": [3, 3], "to": [3, 2]}},
    ]
    summary = diagnostic._summarize_trajectory(actions, opening_plies=21)
    assert summary["scored_ply_count"] == 4
    assert summary["positive_scored_ply_indices"] == [2]
    assert summary["positive_ply_fraction"] == 0.25
    assert summary["longest_zero_point_interval"] == {"start_ply": 3, "end_ply": 4, "length": 2}
    assert summary["cumulative_scores_at_trajectory_quartiles"]["100%"]["scores"] == [0, 1]


def test_replay_analysis_module_has_no_player_search_call_sites():
    source = Path(diagnostic.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_names = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "choose_action" not in called_names
    assert "AlphaBeta" not in called_names
    assert "_player" not in called_names


def test_mechanism_assessment_keeps_overlapping_causes_as_mixed():
    roots = [
        {"legal_any_score_action_count": 0, "chosen_action_points": 0,
         "chosen_zero_score_while_scoring_action_available": False}
        for _ in range(3)
    ]
    roots.append({
        "legal_any_score_action_count": 1,
        "chosen_action_points": 0,
        "chosen_zero_score_while_scoring_action_available": True,
    })
    summary = diagnostic._mechanism_assessment([{
        "legal_action_analysis": {"per_ply": roots},
        "zero_point_plies_in_repeated_move_or_reversal_pattern_indices": [2, 3, 4],
    }])
    assert summary["classification"] == "MIXED"
    assert summary["contributing_mechanisms"] == [
        "SCORING_OPPORTUNITY_SCARCITY",
        "AVAILABLE_SCORE_NOT_SELECTED",
        "REPETITIVE_ZERO_SCORE_CYCLING",
    ]
