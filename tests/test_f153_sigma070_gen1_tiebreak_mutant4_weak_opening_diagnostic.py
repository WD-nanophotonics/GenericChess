import json
from types import SimpleNamespace

from scripts import f153_sigma070_gen1_tiebreak_mutant4_weak_opening_diagnostic as diagnostic
from scripts import f153_shogi_material_mutation_root_sensitivity as mutations
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector
from tools.generic_chess_flow import _validate_resource_envelope


def _pair(score, index):
    return {
        "opening_seed": diagnostic.OPENING["seed"],
        "valid": True,
        "pair_score": score,
    }


def _raw_game(owner, *, winner, elapsed=90.0, nodes=106_000, plies=128,
              scored_plies=106, valid=True, completed=True, reason=None):
    if winner is None:
        scores = [5, 5]
        decisive = "score_draw"
        terminal = "score_draw"
    else:
        scores = [10, 0] if winner == 0 else [0, 10]
        decisive = "score_threshold"
        terminal = "score_threshold"
    return {
        "started": True,
        "child_owner": owner,
        "winner": winner,
        "result": decisive if valid else "inconclusive",
        "decisive_reason": decisive if valid else "",
        "terminal_cause": terminal,
        "threshold_ply": 10 if winner is not None else None,
        "plies": plies,
        "opening_plies": 22,
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
    opening = SimpleNamespace(
        index=0,
        target_plies=diagnostic.OPENING["target_plies"],
        actions=[None] * diagnostic.OPENING["plies"],
        final_position_key=diagnostic.OPENING["opening_id"],
    )
    calls = {"seeds": [], "games": []}

    def opening_corpus(_compiled, seed, count):
        calls["seeds"].append((seed, count))
        return [opening]

    monkeypatch.setattr(diagnostic.race, "opening_corpus", opening_corpus)
    monkeypatch.setattr(diagnostic, "_ordering_values", lambda _compiled: {"fixed": 1})

    def play(_compiled, seen_opening, gen0, mutant, owner, ordering, *, deadline, game_timeout):
        calls["games"].append((seen_opening.final_position_key, gen0, mutant, owner, game_timeout))
        return raw_games[len(calls["games"]) - 1]

    monkeypatch.setattr(diagnostic.bounded_game, "play_capped_game", play)
    return tmp_path / "diagnostic-output", calls


def test_candidate_and_exact_envelope_validate():
    gen0, mutant = diagnostic._candidate()
    assert gen0 == tuple(gen0_vector(GEN0_SEED)) == diagnostic.GEN0_VALUES
    assert mutant == diagnostic.MUTANT_VALUES
    assert mutations._sha(mutant) == diagnostic.MUTANT_SEQUENCE_SHA256

    envelope = diagnostic.resource_envelope()
    _validate_resource_envelope(envelope)
    assert envelope["maximum_games"] == 2
    assert envelope["maximum_nodes"] == 212_000
    assert envelope["maximum_nodes_per_game"] == 106_000
    assert envelope["maximum_concurrent_games"] == 1
    assert envelope["opening_seeds"] == [1_590_402]
    assert envelope["opening_ids"] == [diagnostic.OPENING["opening_id"]]
    assert envelope["hard_wall_minutes"] == 20
    assert envelope["maximum_internal_wall_seconds"] == 1_100
    assert envelope["external_hard_wall_seconds"] == 1_200


def test_classification_compares_only_to_mutant1_prior_score():
    assert diagnostic._classify(0.5) == diagnostic.CLASSIFICATIONS["improves"]
    assert diagnostic._classify(0.25) == diagnostic.CLASSIFICATIONS["equals"]
    assert diagnostic._classify(0.0) == diagnostic.CLASSIFICATIONS["not_improved"]
    assert diagnostic._classify(None) == diagnostic.CLASSIFICATIONS["inconclusive"]


def test_two_role_games_use_only_pinned_opening_and_report_diagnostic(tmp_path, monkeypatch):
    raw = [_raw_game(0, winner=0), _raw_game(1, winner=None)]
    output, calls = _stubbed_run(tmp_path, monkeypatch, raw)
    result = diagnostic.run(output_dir=output)

    assert calls["seeds"] == [(diagnostic.OPENING["seed"], 1)]
    assert [(row[0], row[3], row[4]) for row in calls["games"]] == [
        (diagnostic.OPENING["opening_id"], 0, 480),
        (diagnostic.OPENING["opening_id"], 1, 480),
    ]
    assert all(row[1] == diagnostic.GEN0_VALUES and row[2] == diagnostic.MUTANT_VALUES
               for row in calls["games"])
    assert result["games_attempted"] == result["games_completed_valid"] == 2
    assert result["pair_score"] == 0.75
    assert result["classification"] == diagnostic.CLASSIFICATIONS["improves"]
    assert result["pair"]["pair_score_difference_vs_mutant_1"] == 0.5
    assert result["pair"]["aggregate_mutant_minus_gen0_event_points"] == 10
    assert [game["candidate_game_score"] for game in result["games"]] == [1.0, 0.5]
    assert result["strength_or_promotion_evidence"] is False
    assert result["total_nodes"] == 212_000


def test_first_overrun_is_persisted_and_stops_before_second_role(tmp_path, monkeypatch):
    raw = [_raw_game(0, winner=0, nodes=106_001)]
    output, calls = _stubbed_run(tmp_path, monkeypatch, raw)
    original_check = diagnostic._resource_bound_violations
    game_path = output / f"seed-{diagnostic.OPENING['seed']}-candidate-owner-0.json"

    def assess_after_durable_write(game, envelope):
        assert game_path.is_file()
        assert "actions" in json.loads(game_path.read_text(encoding="utf-8"))
        return original_check(game, envelope)

    monkeypatch.setattr(diagnostic, "_resource_bound_violations", assess_after_durable_write)
    result = diagnostic.run(output_dir=output)

    persisted = json.loads(game_path.read_text(encoding="utf-8"))
    assert len(calls["games"]) == 1
    assert persisted["resource_bound_violations"] == [{
        "metric": "nodes", "observed": 106_001, "approved_limit": 106_000,
    }]
    assert result["classification"] == diagnostic.CLASSIFICATIONS["inconclusive"]
    assert result["games_attempted"] == 1
    assert not (output / f"seed-{diagnostic.OPENING['seed']}-candidate-owner-1.json").exists()


def test_incomplete_game_is_inconclusive_and_nonzero_cli(tmp_path, monkeypatch):
    raw = [_raw_game(0, winner=None, valid=False, completed=False,
                     elapsed=481.0, reason="wall_clock_cap")]
    output, calls = _stubbed_run(tmp_path, monkeypatch, raw)
    result = diagnostic.run(output_dir=output)
    assert len(calls["games"]) == 1
    assert result["classification"] == diagnostic.CLASSIFICATIONS["inconclusive"]

    monkeypatch.setattr(diagnostic.sys, "argv", ["diagnostic", "--output-dir", str(tmp_path / "other")])
    monkeypatch.setattr(diagnostic, "run", lambda output_dir: {
        "classification": diagnostic.CLASSIFICATIONS["inconclusive"],
        "games_attempted": 1,
        "pair": {},
    })
    assert diagnostic.main() != 0
