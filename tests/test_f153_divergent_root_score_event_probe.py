import ast
from pathlib import Path

from scripts import f153_divergent_root_score_event_probe as probe


def _contrast(gen0_category, mutant_category, gen0_points, mutant_points):
    return {
        "gen0_event": {"category": gen0_category},
        "mutant_event": {"category": mutant_category},
        "comparison": {
            "action_divergence_reproduced": True,
            "event_tuple_same": gen0_category == mutant_category and gen0_points == mutant_points,
            "point_delta": mutant_points - gen0_points,
        }
    }


def test_classification_score_event_invariant_across_three_saved_divergences():
    rows = [
        _contrast("zero", "zero", 0, 0),
        _contrast("capture_only", "capture_only", 1, 1),
        _contrast("check_only", "check_only", 1, 1),
    ]
    result = probe._classify(rows)
    assert result["classification"] == "MATERIAL_DIVERGENCE_SCORE_EVENT_INVARIANT"
    assert result["action_divergences_reproduced_from_f153"] == 3
    assert result["event_divergent_contrasts"] == 0
    assert result["mutant_point_ties"] == 3


def test_classification_counts_exact_category_transition_and_point_delta():
    rows = [
        _contrast("zero", "check_only", 0, 1),
        _contrast("capture_only", "capture_only", 1, 1),
        _contrast("zero", "zero", 0, 0),
    ]
    result = probe._classify(rows)
    assert result["classification"] == "MATERIAL_DIVERGENCE_CHANGES_SCORE_EVENT"
    assert result["event_divergent_contrasts"] == 1
    assert result["point_divergent_contrasts"] == 1
    assert result["mutant_point_gains"] == 1
    assert result["event_transition_counts"] == {"zero -> check_only": 1}


def test_saved_root_selection_uses_f151_source_and_not_duplicate_index_zero():
    source = {
        "stages": [{
            "sigma": .70,
            "position_limit": 12,
            "root_rows": [
                {"position": {"source": "new_fixed_seed", "seed": 1530101, "opening_index": 0}},
                {"position": {"source": "F151", "seed": 1510101, "opening_index": 0}},
            ],
        }]
    }
    assert probe._find_saved_root(source, 0)["position"]["source"] == "F151"


def test_probe_reuses_saved_decisions_without_running_search_or_games():
    tree = ast.parse(Path(probe.__file__).read_text(encoding="utf-8"))
    called_names = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert not {"root_probe", "_player", "choose_action", "play_score_race", "play_game"} & called_names
