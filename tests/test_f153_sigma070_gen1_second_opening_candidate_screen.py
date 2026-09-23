import ast
import hashlib
import json
from types import SimpleNamespace
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


def _raw_game(owner, *, completed=True, valid=True, elapsed=1.0, nodes=1_000,
              plies=33, scored_plies=10, inconclusive_reason=None):
    winner = owner if completed and valid else None
    return {
        "started": True,
        "child_owner": owner,
        "winner": winner,
        "result": "score_threshold" if winner is not None else "inconclusive",
        "decisive_reason": "score_threshold" if winner is not None else "",
        "terminal_cause": "score_threshold" if winner is not None else "ongoing",
        "threshold_ply": 10 if winner is not None else None,
        "plies": plies,
        "scored_plies": scored_plies,
        "scores": [10, 0] if winner == 0 else [0, 10] if winner == 1 else [0, 0],
        "capture_points": [0, 0],
        "check_points": [0, 0],
        "nodes": nodes,
        "elapsed_seconds": elapsed,
        "completed": completed,
        "inconclusive_reason": inconclusive_reason,
        "valid": valid,
        "actions": [],
    }


def _run_with_stubbed_games(tmp_path, monkeypatch, raw_games):
    calls = []
    monkeypatch.setattr(screen, "ROOT", tmp_path)
    monkeypatch.setattr(
        screen.subprocess, "check_output",
        lambda command, **kwargs: screen.BASE_SHA if command[-1] == "HEAD^" else "a" * 40,
    )
    source = (
        tmp_path / ".generic_chess_flow"
        / "f153-sigma070-gen1-single-opening-population-output" / "result.json"
    )
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        screen, "_decode_first_screen",
        lambda payload: ({"git_sha": screen.FIRST_SCREEN_SHA}, "pinned"),
    )
    monkeypatch.setattr(screen, "_verify_first_screen", lambda parsed: None)
    monkeypatch.setattr(screen.race, "_compile", lambda: object())
    opening = SimpleNamespace(
        actions=[None] * screen.OPENING_PLIES,
        final_position_key=screen.OPENING_ID,
    )
    monkeypatch.setattr(screen, "_opening", lambda compiled: opening)
    monkeypatch.setattr(screen, "_ordering_values", lambda compiled: {})
    monkeypatch.setattr(screen, "_run_metadata", lambda opening, ordering: {})
    monkeypatch.setattr(screen, "_vectors", lambda: (screen.GEN0_VALUES, {
        index: screen.first_screen.EXPECTED_MUTANTS[index]
        for index in screen.CANDIDATE_INDICES
    }))

    def play(*args, **kwargs):
        owner = args[4]
        calls.append((args[3] is not None, owner))
        return raw_games[len(calls) - 1]

    monkeypatch.setattr(screen.bounded_game, "play_capped_game", play)
    output = tmp_path / "screen-output"
    return screen.run(output_dir=output), output, calls


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
    assert all(row["eligible"] is False for row in screen._rank_candidates(second_opening_draws))
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


def test_completed_in_bounds_stub_games_remain_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(screen, "CANDIDATE_INDICES", (0,))
    monkeypatch.setattr(screen, "MAX_PAIRS", 1)
    monkeypatch.setattr(screen, "MAX_GAMES", 2)
    result, output, calls = _run_with_stubbed_games(
        tmp_path, monkeypatch, [_raw_game(0), _raw_game(1)],
    )

    assert calls == [(True, 0), (True, 1)]
    assert result["pairs"][0]["valid"] is True
    assert result["games_completed_valid"] == 2
    for owner in (0, 1):
        game = json.loads((output / f"mutant-0-owner-{owner}.json").read_text(encoding="utf-8"))
        assert game["resource_envelope_compliant"] is True
        assert game["resource_bound_violations"] == []
        assert game["valid"] is True


def test_wall_clock_cap_is_persisted_and_stops_without_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(screen, "CANDIDATE_INDICES", (0, 1))
    monkeypatch.setattr(screen, "MAX_PAIRS", 2)
    monkeypatch.setattr(screen, "MAX_GAMES", 4)
    timed_out = _raw_game(
        0, completed=False, valid=False, elapsed=421.25,
        inconclusive_reason="wall_clock_cap",
    )
    result, output, calls = _run_with_stubbed_games(tmp_path, monkeypatch, [timed_out])

    game_path = output / "mutant-0-owner-0.json"
    assert game_path.is_file()
    game = json.loads(game_path.read_text(encoding="utf-8"))
    assert game["completed"] is False and game["valid"] is False
    assert game["resource_envelope_compliant"] is False
    assert game["resource_bound_violations"] == [{
        "metric": "elapsed_seconds", "observed": 421.25, "approved_limit": 420,
    }]
    assert calls == [(True, 0)]
    assert not (output / "mutant-0-owner-1.json").exists()
    assert not (output / "mutant-1-owner-0.json").exists()
    assert result["classification"] == "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE"
    assert result["selected_candidate"] is None
    assert result["pairs"][0]["valid"] is False
    assert "mutant_0_owner_0_wall_clock_cap" in result["incomplete_reason"]
    persisted = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert persisted["pairs"][0]["games"][0]["resource_bound_violations"] == game["resource_bound_violations"]


def test_node_bound_violation_is_persisted_then_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(screen, "CANDIDATE_INDICES", (0, 1))
    monkeypatch.setattr(screen, "MAX_PAIRS", 2)
    monkeypatch.setattr(screen, "MAX_GAMES", 4)
    over_nodes = _raw_game(0, nodes=105_001)
    result, output, calls = _run_with_stubbed_games(tmp_path, monkeypatch, [over_nodes])

    game = json.loads((output / "mutant-0-owner-0.json").read_text(encoding="utf-8"))
    assert game["resource_bound_violations"] == [{
        "metric": "nodes", "observed": 105_001, "approved_limit": 105_000,
    }]
    assert game["resource_envelope_compliant"] is False
    assert game["completed"] is True and game["valid"] is False
    assert calls == [(True, 0)]
    assert result["classification"] == "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE"
    assert result["selected_candidate"] is None
    assert "resource_envelope_violation_nodes" in result["incomplete_reason"]


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
