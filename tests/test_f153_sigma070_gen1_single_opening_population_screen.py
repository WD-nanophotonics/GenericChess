import ast
import json
from pathlib import Path

from scripts import f153_sigma070_gen1_single_opening_population_screen as screen
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector
from tools.generic_chess_flow import _validate_resource_envelope


ROOT = Path(screen.__file__).resolve().parents[1]
ENVELOPE = ROOT / ".generic_chess_flow/compute-plans/f153-sigma070-gen1-single-opening-population-envelope.json"


def test_six_exact_sigma070_vectors_match_chat_hashes():
    gen0, mutants = screen._vectors()
    assert gen0 == screen.EXPECTED_GEN0 == tuple(gen0_vector(GEN0_SEED))
    assert len(mutants) == screen.MUTANT_COUNT == 6
    assert tuple(f153._sha(vector) for vector in mutants) == screen.EXPECTED_MUTANT_HASHES


def test_resource_envelope_is_exact_for_the_prescribed_16_ply_opening():
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    _validate_resource_envelope(envelope)
    assert screen.OPENING_SEED == envelope["opening_seed"] == 1_590_201
    assert screen.OPENING_COUNT == envelope["opening_count"] == 1
    assert screen.OPENING_ID == envelope["opening_id"] == "5af7d590672eb94fffc329ae6de806754e505e7f64be31d8470eb4799ca290a8"
    assert screen.OPENING_PLIES == envelope["opening_plies"] == 16
    assert screen.MAX_GAMES == envelope["maximum_games"] == 12
    assert screen.MAX_CONCURRENT_GAMES == envelope["maximum_concurrent_games"] == 1
    assert screen.MAX_GAMES * screen.MAX_TOTAL_PLIES_PER_GAME == envelope["maximum_plies"] == 1536
    assert screen.MAX_SEARCHED_PLIES_PER_GAME == envelope["maximum_searched_plies_per_game"] == 112
    assert screen.MAX_NODES_PER_GAME == envelope["maximum_nodes_per_game"] == 112_000
    assert screen.MAX_TOTAL_NODES == envelope["maximum_nodes"] == 1_344_000
    assert screen.MAX_TOTAL_PLIES_PER_GAME == envelope["maximum_total_plies_per_game_including_opening"] == 128
    assert screen.MAX_GAME_SECONDS == envelope["maximum_game_wall_seconds"] == 420
    assert screen.MAX_INTERNAL_SECONDS == envelope["maximum_internal_wall_seconds"] == 5_040
    assert screen.EXTERNAL_HARD_SECONDS == envelope["external_hard_wall_seconds"] == 5_400


def test_population_classification_and_counts_follow_chat_contract():
    assert screen._game_end_category({"terminal_cause": "max_plies", "decisive_reason": "score_draw"}) == "safety_cap"

    def pair(score, delta=0, valid=True, category="score_draw", nodes=100):
        games = [
            {"valid": valid, "completed": valid, "pair_score": score,
             "child_owner": owner, "terminal_cause": category,
             "decisive_reason": category, "end_category": category,
             "capture_points": [0, 0], "check_points": [0, 0], "nodes": nodes,
             "mutant4_points": delta if owner == 0 else 0,
             "gen0_points": 0, "threshold_ply": None}
            for owner in (0, 1)
        ]
        return {"valid": valid, "pair_score": score, "games": games,
                "aggregate_event_point_differential": delta}

    all_tied = screen._population_summary([pair(.5) for _ in range(6)])
    assert all_tied["classification"] == "SIGMA070_GEN1_FRESH_PAIR_ALL_TIED"
    assert all_tied["pair_score_counts"] == {"below_0_5": 0, "exactly_0_5": 6, "above_0_5": 0}
    found = screen._population_summary([pair(1.0, 2)] + [pair(.5) for _ in range(5)])
    assert found["classification"] == "SIGMA070_GEN1_FRESH_PAIR_DISCRIMINATION_FOUND"
    assert found["mutant_event_differential_counts"] == {"positive": 1, "zero": 5, "negative": 0}
    inconclusive = screen._population_summary([pair(.5) for _ in range(5)] + [pair(None, valid=False)])
    assert inconclusive["classification"] == "SIGMA070_GEN1_FRESH_PAIR_SCREEN_INCONCLUSIVE"


def test_runner_uses_only_one_opening_and_serial_role_swapped_games():
    tree = ast.parse(Path(screen.__file__).read_text(encoding="utf-8"))
    calls = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "ProcessPoolExecutor" not in calls
    assert "opening_corpus" in calls
    assert "play_capped_game" in calls
    assert screen.ROLE_ORDER == (0, 1)
    assert screen.MAX_GAMES == screen.MUTANT_COUNT * len(screen.ROLE_ORDER) == 12
