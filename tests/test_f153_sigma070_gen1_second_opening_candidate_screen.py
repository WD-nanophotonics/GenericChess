import ast
import hashlib
import json
from pathlib import Path

from scripts import f153_sigma070_gen1_second_opening_candidate_screen as screen
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts import f153_sigma070_gen1_single_opening_population_screen as first
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector
from tools.generic_chess_flow import _validate_resource_envelope


ROOT = Path(screen.__file__).resolve().parents[1]
ENVELOPE = ROOT / ".generic_chess_flow/compute-plans/f153-sigma070-gen1-second-opening-candidate-envelope.json"


def _pair(mutant_index, score, delta=0):
    if score == 0.5:
        outcomes = {0: 1.0, 1: 0.0}
    elif score == 0.75:
        outcomes = {0: 1.0, 1: 0.5}
    else:
        outcomes = {0: score, 1: score}
    games = []
    for owner in (0, 1):
        outcome = outcomes[owner]
        if outcome == 0.5:
            winner, reason = None, "score_draw"
        else:
            winner = owner if outcome == 1.0 else 1 - owner
            reason = "score_threshold"
        games.append({
            "child_owner": owner,
            "winner": winner,
            "valid": True,
            "completed": True,
            "decisive_reason": reason,
            "mutant_points": delta if owner == 0 else 0,
            "gen0_points": 0,
            "threshold_ply": 10 if reason == "score_threshold" else None,
        })
    return screen._pair_record(mutant_index, games)


def test_exact_gen0_and_four_selected_sigma070_vectors_and_hashes():
    gen0, candidates = screen._vectors()
    all_mutants = tuple(f153.mutation_vectors_at_sigma(gen0, 0.70))
    assert gen0 == screen.GEN0_VALUES == tuple(gen0_vector(GEN0_SEED))
    assert tuple(candidates) == screen.CANDIDATE_INDICES == (0, 1, 4, 5)
    for index, vector in candidates.items():
        assert vector == all_mutants[index] == first.EXPECTED_MUTANTS[index]
        assert f153._sha(vector) == first.EXPECTED_MUTANT_HASHES[index]


def test_pinned_second_opening_is_new_and_exact_resource_envelope_validates():
    assert screen.OPENING_SEED == 1_590_301
    assert screen.OPENING_COUNT == 1
    assert screen.OPENING_ID not in screen.PREVIOUS_OPENING_IDS
    assert 16 <= screen.OPENING_PLIES <= 32
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    _validate_resource_envelope(envelope)
    assert envelope == screen.resource_envelope(23, screen.OPENING_ID)
    assert envelope["maximum_games"] == 8
    assert envelope["maximum_concurrent_games"] == 1
    assert envelope["maximum_total_plies_per_game_including_opening"] == 128
    assert envelope["maximum_searched_plies_per_game"] == 105
    assert envelope["maximum_nodes_per_game"] == 105_000
    assert envelope["maximum_nodes"] == 840_000
    assert envelope["maximum_game_wall_seconds"] == 420
    assert envelope["maximum_internal_wall_seconds"] == 3_360
    assert envelope["external_hard_wall_seconds"] == 3_600


def test_first_screen_is_pinned_and_only_the_four_positive_leaders_advance():
    first_result = {
        "git_sha": screen.FIRST_SCREEN_SHA,
        "opening": {"seed": first.OPENING_SEED, "opening_id": first.OPENING_ID},
        "games_attempted": 12,
        "games_completed_valid": 12,
        "pairs": [
            {"mutant_index": i, "valid": True, "pair_score": score}
            for i, score in enumerate((0.75, 0.75, 0.5, 0.5, 0.75, 0.75))
        ],
    }
    screen._verify_first_screen(first_result)
    first_result["pairs"][0]["pair_score"] = 0.5
    try:
        screen._verify_first_screen(first_result)
    except AssertionError:
        pass
    else:
        raise AssertionError("changed first-screen evidence must fail closed")


def test_first_screen_bytes_are_digest_pinned(monkeypatch):
    payload = b'{"git_sha":"pinned"}'
    expected = hashlib.sha256(payload).hexdigest().upper()
    monkeypatch.setattr(screen, "FIRST_SCREEN_RESULT_SHA256", expected)
    parsed, actual = screen._decode_first_screen(payload)
    assert actual == expected
    assert parsed == {"git_sha": "pinned"}
    try:
        screen._decode_first_screen(payload + b" ")
    except AssertionError:
        pass
    else:
        raise AssertionError("mutated first-screen evidence bytes must fail closed")


def test_candidate_ranking_uses_only_two_opening_fitness_and_declared_tiebreaks():
    pairs = [
        _pair(0, 0.5, delta=1000),
        _pair(1, 1.0, delta=-1000),
        _pair(4, 0.75, delta=-9999),
        _pair(5, 0.75, delta=9999),
    ]
    ranking = screen._rank_candidates(pairs)
    assert [row["mutant_index"] for row in ranking] == [1, 4, 5, 0]
    assert ranking[0]["two_opening_mean_pair_score"] == 0.875
    assert ranking[0]["openings_above_0_5"] == 2
    assert ranking[0]["eligible"] is True
    assert ranking[1]["two_opening_mean_pair_score"] == ranking[2]["two_opening_mean_pair_score"] == 0.75
    assert ranking[-1]["two_opening_mean_pair_score"] == 0.625
    assert ranking[-1]["eligible"] is False
    assert screen._result_classification(pairs) == (
        "SIGMA070_GEN1_SECOND_OPENING_CANDIDATE_SELECTED", ranking[0]
    )


def test_no_positive_candidate_and_incomplete_classification():
    second_opening_draws = [_pair(index, 0.5) for index in screen.CANDIDATE_INDICES]
    assert all(row["two_opening_mean_pair_score"] == 0.625 for row in screen._rank_candidates(second_opening_draws))
    assert screen._result_classification(second_opening_draws) == (
        "SIGMA070_GEN1_SECOND_OPENING_NO_POSITIVE_CANDIDATE", None
    )

    losses = [_pair(index, 0.0) for index in screen.CANDIDATE_INDICES]
    assert screen._result_classification(losses) == (
        "SIGMA070_GEN1_SECOND_OPENING_NO_POSITIVE_CANDIDATE", None
    )
    assert screen._result_classification(losses[:3]) == (
        "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE", None
    )
    losses[-1]["valid"] = False
    assert screen._result_classification(losses) == (
        "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE", None
    )


def test_pair_requires_two_distinct_valid_roles_and_runner_is_serial():
    duplicate_roles = [
        {"child_owner": 0, "valid": True, "completed": True,
         "decisive_reason": "score_threshold", "winner": 0,
         "mutant_points": 1, "gen0_points": 0, "threshold_ply": 10}
        for _ in range(2)
    ]
    assert screen._pair_record(0, duplicate_roles)["valid"] is False
    tree = ast.parse(Path(screen.__file__).read_text(encoding="utf-8"))
    calls = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "ProcessPoolExecutor" not in calls
    assert "play_capped_game" in calls
    assert screen.CANDIDATE_INDICES == (0, 1, 4, 5)
    assert screen.ROLE_ORDER == (0, 1)
    assert screen.MAX_GAMES == 8
