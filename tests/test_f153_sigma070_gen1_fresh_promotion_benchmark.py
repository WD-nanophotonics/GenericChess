import json
from types import SimpleNamespace

from scripts import f153_sigma070_gen1_fresh_promotion_benchmark as benchmark
from scripts import f153_shogi_material_mutation_root_sensitivity as mutations
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector
from tools.generic_chess_flow import _validate_resource_envelope


def _pair(score, index):
    return {
        "opening_seed": benchmark.OPENINGS[index]["seed"],
        "opening_id": benchmark.OPENINGS[index]["opening_id"],
        "opening_plies": benchmark.OPENINGS[index]["plies"],
        "valid": True,
        "pair_score": score,
        "aggregate_candidate_minus_gen0_event_point_differential": 999_999 if index % 2 else -999_999,
        "games": [],
    }


def _raw_game(owner, opening, *, completed=True, valid=True, elapsed=100.0,
              nodes=None, plies=None, scored_plies=None, inconclusive_reason=None):
    searched = 128 - opening["plies"]
    if nodes is None:
        nodes = searched * benchmark.MAX_NODES_PER_MOVE
    if plies is None:
        plies = 128
    if scored_plies is None:
        scored_plies = plies - opening["plies"]
    winner = owner if completed and valid else None
    scores = [10, 0] if winner == 0 else [0, 10] if winner == 1 else [0, 0]
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
        "scores": scores,
        "capture_points": [6, 2] if owner == 0 else [2, 6],
        "check_points": [4, 0] if owner == 0 else [0, 4],
        "total_points": sum(scores),
        "nodes": nodes,
        "elapsed_seconds": elapsed,
        "completed": completed,
        "inconclusive_reason": inconclusive_reason,
        "valid": valid,
        "actions": [{"actor": owner, "points": 2, "capture": 1, "check": 1}],
    }


def _stubbed_run(tmp_path, monkeypatch, raw_games):
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    monkeypatch.setattr(
        benchmark.subprocess, "check_output",
        lambda command, **kwargs: benchmark.BASE_SHA if command[-1] == "HEAD^" else "c" * 40,
    )
    monkeypatch.setattr(benchmark.race, "_compile", lambda: object())
    openings = [SimpleNamespace(
        index=0,
        target_plies=row["target_plies"],
        actions=[None] * row["plies"],
        final_position_key=row["opening_id"],
    ) for row in benchmark.OPENINGS]
    calls = {"seeds": [], "games": []}

    def opening_corpus(compiled, seed, count):
        calls["seeds"].append((seed, count))
        return [openings[len(calls["seeds"]) - 1]]

    monkeypatch.setattr(benchmark.race, "opening_corpus", opening_corpus)
    monkeypatch.setattr(benchmark, "_ordering_values", lambda compiled: {"fixed": 1})

    def play(compiled, opening, gen0, candidate, owner, ordering, *, deadline, game_timeout):
        calls["games"].append((opening.final_position_key, candidate, owner, game_timeout))
        return raw_games[len(calls["games"]) - 1]

    monkeypatch.setattr(benchmark.bounded_game, "play_capped_game", play)
    output = tmp_path / "promotion-output"
    return output, calls


def test_candidate_vector_and_resource_envelope_are_exact_and_valid():
    gen0, candidate = benchmark._candidate()
    assert gen0 == tuple(gen0_vector(GEN0_SEED)) == benchmark.GEN0_VALUES
    assert candidate == benchmark.GEN1_VECTOR
    assert mutations._sha(candidate) == benchmark.GEN1_SEQUENCE_SHA256

    envelope = benchmark.resource_envelope()
    _validate_resource_envelope(envelope)
    assert envelope["maximum_games"] == 8
    assert envelope["maximum_nodes"] == 842_000
    assert envelope["maximum_concurrent_games"] == 1
    assert envelope["searched_plies_by_seed"] == {
        "1590401": 103, "1590402": 106, "1590403": 100, "1590404": 112,
    }
    assert envelope["maximum_nodes_per_game"] == 112_000
    assert envelope["maximum_game_wall_seconds"] == 480
    assert envelope["maximum_internal_wall_seconds"] == 4_200
    assert envelope["external_hard_wall_seconds"] == 4_500


def test_opening_ids_are_fresh_and_first_seed_records_are_fixed():
    ids = [row["opening_id"] for row in benchmark.OPENINGS]
    assert ids == [
        "aa1404a624da9ab33da03b018d55c1446e5c8d87fa5f9d32cc1b7f6955a6e6c9",
        "55c88a8fe6da49131e9af2eb53bc533b85a0e90e74454c93b1106f5f245cf29e",
        "7aed7c89773a348adf45e5cdf1803289190af2140b44415fe78f61c2970023ca",
        "8c47ed2f29aca51e607df59766dd05d57d6ddb521cb0569e8a7180ba2c287753",
    ]
    assert len(ids) == len(set(ids)) == 4
    assert not set(ids) & benchmark.PREVIOUS_OPENING_IDS
    assert [row["plies"] for row in benchmark.OPENINGS] == [25, 22, 28, 16]


def test_preregistered_pass_fail_and_inconclusive_rules_use_pair_scores_only():
    passed, stats = benchmark._classify([_pair(score, i) for i, score in enumerate((0.75, 0.75, 0.5, 0.5))])
    assert passed == benchmark.PASS_CLASSIFICATION
    assert stats == {
        "promotion_mean_pair_score": 0.625,
        "positive_pairs": 2,
        "tied_pairs": 2,
        "negative_pairs": 0,
        "pass_conditions": {
            "mean_gt_0_5": True,
            "positive_pairs_at_least_2": True,
            "positive_pairs_exceed_negative": True,
        },
    }
    failed, stats = benchmark._classify([_pair(0.5, i) for i in range(4)])
    assert failed == benchmark.FAIL_CLASSIFICATION
    assert stats["promotion_mean_pair_score"] == 0.5
    assert stats["positive_pairs"] == 0 and stats["tied_pairs"] == 4
    assert benchmark._classify([_pair(1.0, 0), _pair(0.0, 1)])[0] == benchmark.INCONCLUSIVE_CLASSIFICATION


def test_eight_stub_games_run_only_pinned_pairs_and_produce_score_race_pass(tmp_path, monkeypatch):
    raw = [
        _raw_game(owner, opening)
        for opening in benchmark.OPENINGS
        for owner in benchmark.ROLE_ORDER
    ]
    output, calls = _stubbed_run(tmp_path, monkeypatch, raw)
    result = benchmark.run(output_dir=output)

    assert calls["seeds"] == [(row["seed"], 1) for row in benchmark.OPENINGS]
    assert len(calls["games"]) == 8
    assert [(call[0], call[2], call[3]) for call in calls["games"]] == [
        (row["opening_id"], owner, 480)
        for row in benchmark.OPENINGS for owner in (0, 1)
    ]
    assert result["classification"] == benchmark.PASS_CLASSIFICATION
    assert result["games_attempted"] == result["games_completed_valid"] == 8
    assert [pair["pair_score"] for pair in result["pairs"]] == [1.0] * 4
    assert result["promotion_mean_pair_score"] == 1.0
    assert result["positive_pairs"] == 4
    assert result["total_nodes"] == 842_000
    assert all(game["first_scoring_event"]["points"] == 2
               for pair in result["pairs"] for game in pair["games"])


def test_first_overrun_is_persisted_and_stops_remaining_games(tmp_path, monkeypatch):
    opening = benchmark.OPENINGS[0]
    timed_out = _raw_game(0, opening, completed=False, valid=False,
                          elapsed=481.25, inconclusive_reason="wall_clock_cap")
    output, calls = _stubbed_run(tmp_path, monkeypatch, [timed_out])
    original_assess = benchmark._resource_bound_violations
    first_game_path = output / f"seed-{opening['seed']}-candidate-owner-0.json"

    def assess_after_durable_write(game, envelope):
        assert first_game_path.is_file()
        on_disk = json.loads(first_game_path.read_text(encoding="utf-8"))
        assert on_disk["resource_envelope_compliant"] is None
        assert "actions" in on_disk
        return original_assess(game, envelope)

    monkeypatch.setattr(benchmark, "_resource_bound_violations", assess_after_durable_write)
    result = benchmark.run(output_dir=output)

    game = json.loads(first_game_path.read_text(encoding="utf-8"))
    assert calls["games"] and len(calls["games"]) == 1
    assert game["completed"] is False and game["valid"] is False
    assert game["resource_bound_violations"] == [{
        "metric": "elapsed_seconds", "observed": 481.25, "approved_limit": 480,
    }]
    assert result["classification"] == benchmark.INCONCLUSIVE_CLASSIFICATION
    assert result["candidate_index"] == 1
    assert "selected_candidate" not in result
    assert result["games_attempted"] == 1
    assert "wall_clock_cap" in result["incomplete_reason"]
    assert not (output / f"seed-{opening['seed']}-candidate-owner-1.json").exists()


def test_incomplete_cli_status_is_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark.sys, "argv", ["benchmark", "--output-dir", str(tmp_path / "out")])
    monkeypatch.setattr(benchmark, "run", lambda output_dir: {
        "classification": benchmark.INCONCLUSIVE_CLASSIFICATION,
        "promotion_mean_pair_score": None,
        "positive_pairs": None,
        "negative_pairs": None,
        "games_attempted": 1,
    })
    assert benchmark.main() != 0
