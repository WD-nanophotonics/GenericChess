import ast
import json
from pathlib import Path

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_sigma070_mutant4_single_pair_score_signal as diagnostic


ROOT = Path(diagnostic.__file__).resolve().parents[1]
F153_RESULT = ROOT / ".generic_chess_flow/f153-shogi-material-mutation-root-sensitivity-result.json"
PROBE_RESULT = ROOT / ".generic_chess_flow/f153-divergent-root-score-event-result.json"
ENVELOPE = ROOT / ".generic_chess_flow/compute-plans/f153-sigma070-mutant4-single-pair-envelope.json"


def test_approved_static_pair_bounds_match_heavy_envelope():
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    assert diagnostic.MAX_GAMES == envelope["maximum_games"] == 2
    assert diagnostic.MAX_CONCURRENT_GAMES == envelope["maximum_concurrent_games"] == 1
    assert diagnostic.MAX_TOTAL_PLIES_PER_GAME == 128
    assert diagnostic.OPENING_PLIES == envelope["opening_plies"] == 30
    assert diagnostic.MAX_SEARCHED_PLIES_PER_GAME == envelope["maximum_searched_plies_per_game"] == 98
    assert diagnostic.MAX_TOTAL_PLIES_PER_GAME * diagnostic.MAX_GAMES == envelope["maximum_plies"] == 256
    assert diagnostic.MAX_NODES_PER_MOVE == envelope["nodes_per_move"] == 1000
    assert diagnostic.MAX_NODES_PER_GAME == 98_000
    assert diagnostic.MAX_TOTAL_NODES == envelope["maximum_nodes"] == 196_000
    assert diagnostic.MAX_GAME_SECONDS == envelope["maximum_game_wall_seconds"] == 420
    assert diagnostic.MAX_WALL_SECONDS == envelope["maximum_internal_wall_seconds"] == 840
    assert diagnostic.EXTERNAL_HARD_WALL_SECONDS == envelope["external_hard_wall_seconds"] == 900
    assert envelope["hard_wall_minutes"] * 60 == diagnostic.EXTERNAL_HARD_WALL_SECONDS
    assert diagnostic.CHILD_OWNER_ORDER == (0, 1)


def test_exact_sigma070_child_identity_matches_both_published_records():
    gen0, child, evidence = diagnostic._verify_identity(
        f153_result_path=F153_RESULT, probe_result_path=PROBE_RESULT
    )
    assert gen0 == diagnostic.EXPECTED_GEN0
    assert child == diagnostic.EXPECTED_CHILD
    assert diagnostic.f153._sha(child) == diagnostic.EXPECTED_RULES_SHA
    assert evidence["root_record"]["mutant_4"]["search"]["best_action_key"] == diagnostic.ROOT_MUTANT_ACTION_KEY


def test_approved_f151_root_identity_and_30_ply_opening_reconstruct():
    compiled = race._compile()
    openings = race.opening_corpus(compiled, diagnostic.F151_SEED, 32)
    matches = [row for row in openings if row.index == diagnostic.OPENING_INDEX]
    assert len(matches) == 1
    assert matches[0].final_position_key == diagnostic.OPENING_ID
    assert len(matches[0].actions) == diagnostic.OPENING_PLIES
    assert diagnostic.MAX_TOTAL_PLIES_PER_GAME - len(matches[0].actions) == 98


def test_pair_classification_obeys_only_the_approved_point_rule():
    complete = lambda owner, mut, gen: {
        "completed": True, "valid": True, "first_root_action_reproduced": True,
        "child_owner": owner, "mutant_points": mut, "gen0_points": gen,
        "winner": owner, "threshold_ply": None,
    }
    assert diagnostic._classify_pair([complete(0, 4, 2), complete(1, 3, 3)])["classification"] == (
        "MUTANT4_SCORE_SIGNAL_PERSISTS_AT_PAIR_LEVEL"
    )
    assert diagnostic._classify_pair([complete(0, 4, 2), complete(1, 2, 4)])["classification"] == (
        "MUTANT4_SCORE_SIGNAL_ROLE_DEPENDENT_OR_CANCELLED"
    )
    assert diagnostic._classify_pair([complete(0, 2, 4), complete(1, 2, 4)])["classification"] == (
        "MUTANT4_SCORE_SIGNAL_REVERSES"
    )
    incomplete = complete(0, 4, 2)
    incomplete["valid"] = False
    assert diagnostic._classify_pair([incomplete])["classification"] == "MUTANT4_SINGLE_PAIR_INCONCLUSIVE"


def test_runner_has_no_parallel_game_or_unapproved_vector_path():
    tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
    names = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "ProcessPoolExecutor" not in names
    assert "mutation_vectors_at_sigma" in names
    assert "choose_action" in names
    assert diagnostic.MAX_GAMES == 2
    assert diagnostic.MAX_CONCURRENT_GAMES == 1
