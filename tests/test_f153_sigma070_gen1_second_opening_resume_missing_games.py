import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import f153_sigma070_gen1_second_opening_candidate_screen as screen
from scripts import f153_sigma070_gen1_second_opening_resume_missing_games as resume
from tools.generic_chess_flow import _validate_resource_envelope


def _game(owner, *, completed=True, valid=True, elapsed=1.0, nodes=1_000,
          inconclusive_reason=None):
    winner = owner if completed and valid else None
    return {
        "started": True,
        "child_owner": owner,
        "winner": winner,
        "result": "score_threshold" if winner is not None else "inconclusive",
        "decisive_reason": "score_threshold" if winner is not None else "",
        "terminal_cause": "score_threshold" if winner is not None else "ongoing",
        "threshold_ply": 10 if winner is not None else None,
        "plies": 33,
        "scored_plies": 10,
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


def _prior_fixture(root):
    prior = root / "prior"
    prior.mkdir()
    opening = {
        "seed": 1_590_301,
        "opening_seed": 1_590_301,
        "index": 0,
        "target_plies": 23,
        "plies": 23,
        "opening_id": resume.OPENING_ID,
        "actions": [{} for _ in range(23)],
    }
    pairs = []
    for mutant_index, score in ((0, 0.50), (1, 0.75)):
        outcomes = (1.0, 0.0) if score == 0.50 else (1.0, 0.5)
        games = []
        for owner, outcome in enumerate(outcomes):
            raw = _game(owner, valid=True)
            raw.update({
                "mutant_index": mutant_index,
                "opening_id": resume.OPENING_ID,
                "child_game_score": outcome,
                "mutant_points": 2 if outcome == 1.0 else 0,
                "gen0_points": 0 if outcome == 1.0 else 2,
            })
            if outcome == 0.5:
                raw.update({"winner": None, "decisive_reason": "score_draw", "terminal_cause": "score_draw", "threshold_ply": None})
            elif outcome == 0.0:
                raw["winner"] = 1 - owner
            games.append(raw)
            (prior / f"mutant-{mutant_index}-owner-{owner}.json").write_text(
                json.dumps(raw), encoding="utf-8",
            )
        pair = screen._pair_record(mutant_index, games)
        pair["pair_score"] = score
        pairs.append(pair)
        (prior / f"mutant-{mutant_index}-pair.json").write_text(
            json.dumps(pair), encoding="utf-8",
        )

    m4_owner0 = _game(0)
    m4_owner0.update({
        "mutant_index": 4,
        "opening_id": resume.OPENING_ID,
        "child_game_score": 1.0,
        "mutant_points": 2,
        "gen0_points": 0,
        "scored_plies": 105,
        "plies": 128,
        "nodes": 105_000,
    })
    (prior / "mutant-4-owner-0.json").write_text(json.dumps(m4_owner0), encoding="utf-8")
    result = {
        "git_sha": resume.PRIOR_SCREEN_SHA,
        "classification": "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE",
        "first_screen_result_sha256": screen.FIRST_SCREEN_RESULT_SHA256,
        "opening": opening,
        "pairs": pairs,
    }
    (prior / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return prior


def _stub_run(tmp_path, monkeypatch, raw_games):
    prior = _prior_fixture(tmp_path)
    monkeypatch.setattr(resume, "ROOT", tmp_path)
    monkeypatch.setattr(resume, "PRIOR_OUTPUT", prior)
    monkeypatch.setattr(
        resume, "PRIOR_RESULT_SHA256",
        hashlib.sha256((prior / "result.json").read_bytes()).hexdigest().upper(),
    )
    monkeypatch.setattr(
        resume, "PRIOR_M4_OWNER0_SHA256",
        hashlib.sha256((prior / "mutant-4-owner-0.json").read_bytes()).hexdigest().upper(),
    )
    monkeypatch.setattr(
        resume.subprocess, "check_output",
        lambda command, **kwargs: resume.BASE_SHA if command[-1] == "HEAD^" else "b" * 40,
    )
    opening = SimpleNamespace(actions=[None] * 23, final_position_key=resume.OPENING_ID)
    monkeypatch.setattr(resume.race, "_compile", lambda: object())
    monkeypatch.setattr(resume, "_load_opening", lambda payload: opening)
    monkeypatch.setattr(resume, "_ordering_values", lambda compiled: {})
    gen0 = screen.GEN0_VALUES
    mutants = {index: screen.first_screen.EXPECTED_MUTANTS[index] for index in (4, 5)}
    monkeypatch.setattr(screen, "_vectors", lambda: (gen0, mutants))
    calls = []

    def play(*args, **kwargs):
        calls.append((args[3], args[4], kwargs["game_timeout"]))
        return raw_games[len(calls) - 1]

    monkeypatch.setattr(resume.bounded_game, "play_capped_game", play)
    output = tmp_path / "resumed"
    return prior, output, calls


def test_three_game_envelope_matches_chat_caps_and_validates():
    envelope = resume.resource_envelope()
    _validate_resource_envelope(envelope)
    assert envelope["maximum_games"] == 3
    assert envelope["maximum_nodes"] == 315_000
    assert envelope["maximum_concurrent_games"] == 1
    assert envelope["maximum_total_plies_per_game_including_opening"] == 128
    assert envelope["maximum_searched_plies_per_game"] == 105
    assert envelope["maximum_nodes_per_game"] == 105_000
    assert envelope["maximum_game_wall_seconds"] == 480
    assert envelope["maximum_internal_wall_seconds"] == 1_500
    assert envelope["external_hard_wall_seconds"] == 1_800
    assert envelope["opening_id"] == resume.OPENING_ID


def test_resume_uses_only_three_missing_roles_and_reconstructs_full_pairs(tmp_path, monkeypatch):
    _, output, calls = _stub_run(tmp_path, monkeypatch, [_game(1), _game(0), _game(1)])
    result = resume.run(output_dir=output)

    assert calls == [
        (screen.first_screen.EXPECTED_MUTANTS[4], 1, 480),
        (screen.first_screen.EXPECTED_MUTANTS[5], 0, 480),
        (screen.first_screen.EXPECTED_MUTANTS[5], 1, 480),
    ]
    assert [pair["mutant_index"] for pair in result["pairs"]] == [0, 1, 4, 5]
    assert [pair["pair_score"] for pair in result["pairs"]] == [0.50, 0.75, 1.0, 1.0]
    assert result["classification"] == "SIGMA070_GEN1_SECOND_OPENING_CANDIDATE_SELECTED"
    assert result["selected_candidate"]["mutant_index"] == 4
    assert result["resumed_games_attempted"] == 3
    assert result["resumed_games_completed_valid"] == 3


def test_resume_persists_first_overrun_and_stops_before_next_missing_game(tmp_path, monkeypatch):
    timed_out = _game(1, completed=False, valid=False, elapsed=481.25, inconclusive_reason="wall_clock_cap")
    _, output, calls = _stub_run(tmp_path, monkeypatch, [timed_out])
    result = resume.run(output_dir=output)

    assert calls == [(screen.first_screen.EXPECTED_MUTANTS[4], 1, 480)]
    game_path = output / "mutant-4-owner-1.json"
    game = json.loads(game_path.read_text(encoding="utf-8"))
    assert game["completed"] is False and game["valid"] is False
    assert game["resource_envelope_compliant"] is False
    assert game["resource_bound_violations"] == [{
        "metric": "elapsed_seconds", "observed": 481.25, "approved_limit": 480,
    }]
    assert not (output / "mutant-5-owner-0.json").exists()
    assert result["classification"] == "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE"
    assert result["selected_candidate"] is None
    assert "mutant_4_owner_1_wall_clock_cap" in result["incomplete_reason"]
    persisted = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert persisted["pairs"][2]["games"][1]["resource_bound_violations"] == game["resource_bound_violations"]


def test_mutated_prior_result_digest_fails_before_any_game(tmp_path, monkeypatch):
    prior, output, calls = _stub_run(tmp_path, monkeypatch, [_game(1)])
    path = prior / "result.json"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(AssertionError, match="pinned evidence digest mismatch"):
        resume.run(output_dir=output)
    assert calls == []
    assert not output.exists()


def test_inconclusive_cli_result_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(resume.sys, "argv", ["resume", "--output-dir", str(tmp_path / "out")])
    monkeypatch.setattr(resume, "run", lambda output_dir: {
        "classification": "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE",
        "selected_candidate": None,
        "resumed_games_attempted": 1,
        "pairs": [],
    })

    assert resume.main() != 0
