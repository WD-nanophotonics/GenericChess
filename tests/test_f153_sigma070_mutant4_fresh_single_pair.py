import ast
import json
from pathlib import Path

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_sigma070_mutant4_fresh_single_pair as diagnostic
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector


ROOT = Path(diagnostic.__file__).resolve().parents[1]
ENVELOPE = ROOT / ".generic_chess_flow/compute-plans/f153-sigma070-mutant4-fresh-single-pair-envelope.json"


def test_resource_bounds_are_exactly_derived_from_the_opening_contract():
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    assert diagnostic.MAX_GAMES == envelope["maximum_games"] == 2
    assert diagnostic.MAX_CONCURRENT_GAMES == envelope["maximum_concurrent_games"] == 1
    assert diagnostic.MAX_TOTAL_PLIES_PER_GAME == 128
    assert diagnostic.OPENING_PLIES == envelope["opening_plies"] == 21
    assert diagnostic.MAX_SEARCHED_PLIES_PER_GAME == 107
    assert diagnostic.MAX_NODES_PER_GAME == 107_000
    assert diagnostic.MAX_TOTAL_NODES == envelope["maximum_nodes"] == 214_000
    assert diagnostic.MAX_NODES_PER_MOVE == envelope["nodes_per_move"] == 1000
    assert diagnostic.MAX_GAME_SECONDS == envelope["maximum_game_wall_seconds"] == 420
    assert diagnostic.MAX_INTERNAL_SECONDS == envelope["maximum_internal_wall_seconds"] == 840
    assert diagnostic.EXTERNAL_HARD_SECONDS == envelope["external_hard_wall_seconds"] == 900
    assert diagnostic.MAX_GAMES * diagnostic.MAX_TOTAL_PLIES_PER_GAME == envelope["maximum_plies"] == 256


def test_exact_gen0_and_sigma070_mutant4_vectors():
    gen0, mutant4 = diagnostic._vectors()
    assert gen0 == diagnostic.EXPECTED_GEN0 == tuple(gen0_vector(GEN0_SEED))
    assert mutant4 == diagnostic.EXPECTED_MUTANT4
    assert f153._sha(mutant4) == diagnostic.EXPECTED_MUTANT4_SHA


def test_prescribed_seed_yields_the_first_unselected_opening_without_search():
    compiled = race._compile()
    opening = diagnostic._fresh_opening(compiled)
    assert opening.final_position_key == diagnostic.EXPECTED_OPENING_ID
    assert opening.final_position_key not in diagnostic.HISTORICAL_OPENING_IDS
    assert len(opening.actions) == opening.target_plies == 21


def test_pair_classification_uses_mutant_win_fraction_not_event_point_sum():
    def game(owner, winner, *, valid=True, completed=True):
        return {"child_owner": owner, "winner": winner, "valid": valid, "completed": completed}

    assert diagnostic._classify([game(0, 0), game(1, 1)]) == ("FRESH_PAIR_MUTANT4_POSITIVE_SIGNAL", 1.0)
    assert diagnostic._classify([game(0, 0), game(1, 0)]) == ("FRESH_PAIR_MUTANT4_TIED_OR_CANCELLED", 0.5)
    assert diagnostic._classify([game(0, 1), game(1, 0)]) == ("FRESH_PAIR_MUTANT4_NEGATIVE_SIGNAL", 0.0)
    assert diagnostic._classify([game(0, 0, valid=False), game(1, 1)]) == (
        "FRESH_PAIR_MUTANT4_INCONCLUSIVE", None
    )


def test_runner_is_serial_and_does_not_search_or_select_openings():
    tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
    called = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "ProcessPoolExecutor" not in called
    assert "opening_corpus" in called
    assert "choose_action" not in called  # searches are delegated to the bounded F158 helper
    assert diagnostic.OPENING_SEED == 1_590_101
    assert diagnostic.OPENING_COUNT == 1
    assert diagnostic.ROLE_ORDER == (0, 1)
