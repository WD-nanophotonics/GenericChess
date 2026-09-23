import ast
from pathlib import Path

from scripts import f158_shogi_score_race_material_objective_alignment as diagnostic


def test_event_categories_are_mutually_exclusive():
    assert diagnostic._category({"capture": 1, "check": 0}) == "capture_only"
    assert diagnostic._category({"capture": 0, "check": 1}) == "check_only"
    assert diagnostic._category({"capture": 1, "check": 1}) == "capture_plus_check"
    assert diagnostic._category({"capture": 0, "check": 0}) == "zero"


def test_delta_distribution_is_exact_and_keeps_ties():
    result = diagnostic._stats([-4, 0, 0, 6])
    assert result["count"] == 4
    assert result["min"] == -4
    assert result["median"] == 0
    assert result["max"] == 6
    assert result["values"] == {"-4": 1, "0": 2, "6": 1}


def test_alignment_classification_identifies_unlearnable_check_reward():
    summary = {
        "missed_zero_scoring_opportunities": {
            "root_count": 10,
            "capture_or_combo_best_materially_better_under_either_root_count": 0,
            "by_best_scoring_action_category": {
                "check_only": {
                    "best_action_material_neutral_under_both": 7,
                    "per_evaluator": {
                        "gen0": {"best_action_material_neutral_count": 7},
                        "mutant0": {"best_action_material_neutral_count": 7},
                    },
                },
                "capture_only": {"per_evaluator": {}},
                "capture_plus_check": {"per_evaluator": {}},
            },
        }
    }
    assert diagnostic._classify(summary)["label"] == "SCORE_RACE_CHECK_REWARD_OUTSIDE_MATERIAL_LEARNABLE_SURFACE"


def test_alignment_classification_reports_mixed_when_capture_is_materially_ranked():
    summary = {
        "missed_zero_scoring_opportunities": {
            "root_count": 10,
            "capture_or_combo_best_materially_better_under_either_root_count": 1,
            "by_best_scoring_action_category": {
                "check_only": {"best_action_material_neutral_under_both": 9},
                "capture_only": {},
                "capture_plus_check": {},
            },
        }
    }
    assert diagnostic._classify(summary)["label"] == "SCORE_RACE_MIXED_ALIGNMENT"


def test_analysis_module_does_not_invoke_search_or_start_games():
    tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
    called_names = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert not {"choose_action", "AlphaBetaPlayer", "_player", "play_score_race"} & called_names
