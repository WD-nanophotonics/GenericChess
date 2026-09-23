import ast
from pathlib import Path

from scripts import f158_fixed_root_material_event_causal_probe as probe


def _root(action0, event0, action1, event1):
    return {
        "decisions": {
            "gen0": {
                "selected_action": action0,
                "selected_action_capture": event0[0],
                "selected_action_check": event0[1],
                "selected_action_score_race_points": event0[2],
            },
            "mutant0": {
                "selected_action": action1,
                "selected_action_capture": event1[0],
                "selected_action_check": event1[1],
                "selected_action_score_race_points": event1[2],
            },
        }
    }


def test_category_is_exclusive_and_score_consistent():
    assert probe._category({"capture": 1, "check": 0}) == "capture_only"
    assert probe._category({"capture": 0, "check": 1}) == "check_only"
    assert probe._category({"capture": 1, "check": 1}) == "capture_plus_check"
    assert probe._category({"capture": 0, "check": 0}) == "zero"


def test_classification_prioritizes_event_changes_over_move_changes():
    roots = [
        _root({"m": 1}, (0, 0, 0), {"m": 2}, (0, 1, 1)),
        _root({"m": 3}, (0, 0, 0), {"m": 3}, (0, 0, 0)),
        _root({"m": 4}, (1, 0, 1), {"m": 5}, (1, 0, 1)),
        _root({"m": 6}, (0, 0, 0), {"m": 7}, (0, 0, 0)),
    ]
    result = probe._classify(roots)
    assert result == {
        "classification": "MATERIAL_PERTURBATION_CHANGES_SCORE_EVENT_BEHAVIOR",
        "action_divergent_roots": 3,
        "event_divergent_roots": 1,
        "point_divergent_roots": 1,
        "roots_where_mutant_gains_points": 1,
        "roots_where_mutant_loses_points": 0,
        "roots_with_different_action_but_identical_event": 2,
    }


def test_classification_move_only_and_no_change_cases():
    move_only = [_root(i, (0, 0, 0), i + 1, (0, 0, 0)) for i in range(4)]
    unchanged = [_root(i, (0, 0, 0), i, (0, 0, 0)) for i in range(4)]
    assert probe._classify(move_only)["classification"] == "MATERIAL_PERTURBATION_CHANGES_MOVE_ONLY"
    assert probe._classify(unchanged)["classification"] == "MATERIAL_PERTURBATION_NO_FIXED_ROOT_BEHAVIOR_CHANGE"


def test_probe_uses_no_proxy_evaluator_or_game_loop():
    tree = ast.parse(Path(probe.__file__).read_text(encoding="utf-8"))
    called_names = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert not {"F122", "play_capped_game", "play_score_race"} & called_names
