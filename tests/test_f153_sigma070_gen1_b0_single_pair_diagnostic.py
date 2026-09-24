import json
from types import SimpleNamespace

import pytest

from scripts import f153_sigma070_gen1_b0_single_pair_diagnostic as diagnostic
from scripts import f153_sigma070_gen1_fresh_promotion_benchmark as promotion
from scripts import f153_sigma070_gen1_second_opening_candidate_screen as selection
from scripts import f153_sigma070_gen1_single_opening_population_screen as first_screen
from scripts import f153_sigma070_mutant4_fresh_single_pair as prior_single_pair
from scripts import f158_shogi_sigma070_single_pair_diagnostic as prior_bounded_diagnostic
from scripts import f153_shogi_material_mutation_root_sensitivity as mutations
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector
from tools.generic_chess_flow import _validate_resource_envelope


def _raw_game(owner, *, winner, elapsed=90.0, nodes=101_000, plies=128,
              scored_plies=101, valid=True, completed=True, reason=None):
    if winner is None:
        scores, decisive, terminal = [5, 5], "score_draw", "score_draw"
    else:
        scores = [10, 0] if winner == 0 else [0, 10]
        decisive = terminal = "score_threshold"
    return {
        "started": True,
        "child_owner": owner,
        "winner": winner,
        "result": decisive if valid else "inconclusive",
        "decisive_reason": decisive if valid else "",
        "terminal_cause": terminal,
        "threshold_ply": 10 if winner is not None else None,
        "plies": plies,
        "opening_plies": diagnostic.OPENING_PLIES,
        "scored_plies": scored_plies,
        "scores": scores,
        "capture_points": [6, 2] if owner == 0 else [2, 6],
        "check_points": [4, 0] if owner == 0 else [0, 4],
        "total_points": sum(scores),
        "nodes": nodes,
        "elapsed_seconds": elapsed,
        "completed": completed,
        "inconclusive_reason": reason,
        "valid": valid,
        "actions": [{"actor": owner, "points": 2, "capture": 1, "check": 1}],
    }


def _stubbed_run(tmp_path, monkeypatch, raw_games):
    monkeypatch.setattr(diagnostic, "ROOT", tmp_path)
    monkeypatch.setattr(
        diagnostic.subprocess, "check_output",
        lambda command, **kwargs: diagnostic.BASE_SHA if command[-1] == "HEAD^" else "c" * 40,
    )
    monkeypatch.setattr(diagnostic.race, "_compile", lambda: object())
    opening = SimpleNamespace(index=0, target_plies=diagnostic.OPENING_PLIES,
                              actions=[None] * diagnostic.OPENING_PLIES,
                              final_position_key=diagnostic.OPENING_ID)
    calls = {"seeds": [], "games": []}

    def opening_corpus(_compiled, seed, count):
        calls["seeds"].append((seed, count))
        return [opening]

    monkeypatch.setattr(diagnostic.race, "opening_corpus", opening_corpus)
    monkeypatch.setattr(diagnostic, "_ordering_values", lambda _compiled: {"fixed": 1})

    def play(_compiled, seen_opening, gen0, b0, owner, _ordering, *, deadline, game_timeout):
        calls["games"].append((seen_opening.final_position_key, gen0, b0, owner, game_timeout))
        return raw_games[len(calls["games"]) - 1]

    monkeypatch.setattr(diagnostic.bounded_game, "play_capped_game", play)
    return tmp_path / "diagnostic-output", calls


def test_candidate_and_15_minute_envelope_are_exact_and_valid():
    gen0, b0 = diagnostic._candidate()
    assert gen0 == tuple(gen0_vector(GEN0_SEED)) == diagnostic.GEN0_VALUES
    assert b0 == diagnostic.B0_VALUES
    assert mutations._sha(b0) == diagnostic.B0_SEQUENCE_SHA256
    assert diagnostic.B0_RNG_SEED == 1_440_301 + 200 + diagnostic.B0_INDEX

    envelope = diagnostic.resource_envelope()
    _validate_resource_envelope(envelope)
    assert envelope["maximum_games"] == 2
    assert envelope["maximum_nodes_per_game"] == 101_000
    assert envelope["maximum_nodes"] == 202_000
    assert envelope["maximum_concurrent_games"] == 1
    assert envelope["opening_seeds"] == [1_590_501]
    assert envelope["opening_ids"] == [diagnostic.OPENING_ID]
    assert envelope["hard_wall_minutes"] == 15
    assert envelope["maximum_internal_wall_seconds"] == 840
    assert envelope["external_hard_wall_seconds"] == 900


def test_prior_diagnostic_selection_and_promotion_roots_are_comprehensively_excluded():
    expected_root_sensitivity_ids = {
        "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b",
        "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
        "88f8c456be07973346e31075ff83271f28cb898ce1912755f566d41c591c6dbd",
        "8abe104fc6a2960e6ba2052484abbb61e0cd01aed79a0e6ae67f9818519e2439",
        "8e30c44f09ec4f5af088cbaaed6727a664f29af8abd12c38ab0c9d0561717c91",
        "a4397bb2b7538ae608cb0a19887348b68433d6e3ac77cdf29a713a68baee0716",
        "acf8ddb443682ab8c0db80e0c1172b33736e99a1f72471728230a06c637785f5",
        "b046dec8bd8675adfbbc6dc1c0d439ffbd878c8b08a433ab84abb200b119160b",
        "bddff5b4466c5b5c75faa8297d52524a78c618e7c298f0b6938e00568175cccf",
        "c081cff6ca9620e3588f5e0d2c61d4cbb4ede158e817a3debb964d9e4909061a",
        "d14e25b47a125dac58ebed2d3d74e2aef0fc32169ff18bfcad06a0a98d0c4bdd",
        "e06770317abac084ce7a3e9d4c4a513f5d45f4e9be47bd8d2d66ca4975509620",
    }
    selected_roots = (
        set(first_screen.PREVIOUS_OPENING_IDS) | {first_screen.OPENING_ID}
        | set(selection.PREVIOUS_OPENING_IDS) | {selection.OPENING_ID}
    )
    promotion_roots = set(promotion.PREVIOUS_OPENING_IDS) | {
        row["opening_id"] for row in promotion.OPENINGS
    }
    earlier_diagnostic_roots = (
        set(prior_single_pair.HISTORICAL_OPENING_IDS)
        | {prior_single_pair.EXPECTED_OPENING_ID}
        | set(prior_bounded_diagnostic.HISTORICAL_OPENING_IDS)
        | {prior_bounded_diagnostic.PRIOR_ROOT_DIVERGENCE["opening_id"]}
        | expected_root_sensitivity_ids
    )
    all_prior_roots = selected_roots | promotion_roots | earlier_diagnostic_roots

    assert all_prior_roots == diagnostic.PREVIOUS_OPENING_IDS
    assert set(diagnostic.PRIOR_ROOTS_BY_SOURCE) == diagnostic.PREVIOUS_OPENING_IDS
    assert diagnostic.OPENING_ID not in all_prior_roots
    assert all("F153" in source or "F151" in source or "F158" in source
               for source in diagnostic.PRIOR_ROOTS_BY_SOURCE.values())


def test_first_opening_is_used_once_and_must_be_fresh(monkeypatch):
    opening = SimpleNamespace(index=0, actions=[None] * diagnostic.OPENING_PLIES,
                              final_position_key=diagnostic.OPENING_ID)
    calls = []
    monkeypatch.setattr(diagnostic.race, "opening_corpus",
                        lambda _compiled, seed, count: calls.append((seed, count)) or [opening])
    assert diagnostic._opening(object()) is opening
    assert calls == [(diagnostic.OPENING_SEED, 1)]

    duplicate = SimpleNamespace(index=0, actions=[None] * 16,
                                 final_position_key=next(iter(diagnostic.PREVIOUS_OPENING_IDS)))
    monkeypatch.setattr(diagnostic.race, "opening_corpus", lambda *_: [duplicate])
    with pytest.raises(AssertionError, match="duplicates"):
        diagnostic._opening(object())


def test_pair_classification_requires_a_complete_role_swapped_pair():
    assert diagnostic.CLASSIFICATIONS == {
        "positive": "GEN1_RESTART_BATCH_B0_POSITIVE_SIGNAL",
        "tie": "GEN1_RESTART_BATCH_B0_TIED",
        "negative": "GEN1_RESTART_BATCH_B0_NEGATIVE_SIGNAL",
        "inconclusive": "GEN1_RESTART_BATCH_B0_INCONCLUSIVE",
    }
    assert diagnostic._classify(1.0) == diagnostic.CLASSIFICATIONS["positive"]
    assert diagnostic._classify(0.5) == diagnostic.CLASSIFICATIONS["tie"]
    assert diagnostic._classify(0.0) == diagnostic.CLASSIFICATIONS["negative"]
    assert diagnostic._classify(None) == diagnostic.CLASSIFICATIONS["inconclusive"]
    assert not diagnostic._pair([_raw_game(0, winner=0)])["valid"]


def test_exactly_one_role_swapped_pair_runs_and_is_descriptive_only(tmp_path, monkeypatch):
    raw = [_raw_game(0, winner=0), _raw_game(1, winner=None)]
    output, calls = _stubbed_run(tmp_path, monkeypatch, raw)
    result = diagnostic.run(output_dir=output)

    assert calls["seeds"] == [(diagnostic.OPENING_SEED, 1)]
    assert [(row[0], row[3], row[4]) for row in calls["games"]] == [
        (diagnostic.OPENING_ID, 0, 420),
        (diagnostic.OPENING_ID, 1, 420),
    ]
    assert all(row[1] == diagnostic.GEN0_VALUES and row[2] == diagnostic.B0_VALUES
               for row in calls["games"])
    assert result["games_attempted"] == result["games_completed_valid"] == 2
    assert result["pair_score"] == 0.75
    assert result["classification"] == "GEN1_RESTART_BATCH_B0_POSITIVE_SIGNAL"
    assert result["strength_or_promotion_evidence"] is False
    assert result["total_nodes"] == 202_000
    assert result["pair"]["aggregate_candidate_minus_gen0_event_points"] == 10
    assert result["pair"]["per_role_event_point_differential"] == [
        {"candidate_owner": 0, "candidate_minus_gen0_event_points": 10},
        {"candidate_owner": 1, "candidate_minus_gen0_event_points": 0},
    ]
    assert result["games"][0]["candidate_capture_events"] == 6
    assert result["games"][0]["gen0_capture_events"] == 2
    assert result["games"][0]["candidate_check_events"] == 4
    assert result["games"][0]["gen0_check_events"] == 0
    assert result["games"][0]["candidate_event_points"] == 10
    assert result["games"][0]["gen0_event_points"] == 0
    assert result["games"][0]["first_scoring_event"] == {
        "scored_ply": 1, "total_game_ply": diagnostic.OPENING_PLIES + 1,
        "actor": 0, "capture": 1, "check": 1, "points": 2,
    }
    assert result["games"][0]["threshold_10_reached"] is True
    assert result["games"][1]["threshold_10_reached"] is False


def test_raw_incomplete_game_is_saved_before_resource_check_and_stops(tmp_path, monkeypatch):
    raw = [_raw_game(0, winner=None, nodes=101_001, plies=129, scored_plies=102,
                     valid=False, completed=False, elapsed=421.0, reason="wall_clock_cap")]
    output, calls = _stubbed_run(tmp_path, monkeypatch, raw)
    game_path = output / f"seed-{diagnostic.OPENING_SEED}-candidate-owner-0.json"
    assess = diagnostic._resource_bound_violations

    def assess_after_save(game, envelope):
        assert game_path.is_file()
        saved = json.loads(game_path.read_text(encoding="utf-8"))
        assert saved["actions"] == raw[0]["actions"]
        assert "resource_envelope_compliant" not in saved
        return assess(game, envelope)

    monkeypatch.setattr(diagnostic, "_resource_bound_violations", assess_after_save)
    result = diagnostic.run(output_dir=output)

    saved = json.loads(game_path.read_text(encoding="utf-8"))
    assert len(calls["games"]) == 1
    assert [item["metric"] for item in saved["resource_bound_violations"]] == [
        "plies", "scored_plies", "nodes", "elapsed_seconds",
    ]
    assert result["classification"] == diagnostic.CLASSIFICATIONS["inconclusive"]
    assert result["games_attempted"] == 1
    assert not (output / f"seed-{diagnostic.OPENING_SEED}-candidate-owner-1.json").exists()
