from types import SimpleNamespace

import pytest

from scripts import f146_shogi_material_score_race_threshold3_evolution as race


def test_threshold3_and_source_level_score_independence():
    assert race.SCORE_THRESHOLD == 3
    source = race.inspect.getsource(race.score_event)
    assert "champion" not in source
    assert "child" not in source
    assert "values" not in source


def test_nondecisive_terminal_uses_score_tiebreak_or_valid_score_draw():
    repetition = SimpleNamespace(status=race.SessionStatus.REPETITION, winner=None)
    assert race._core_winner(repetition) is False
    assert race.resolve_terminal(repetition, [1, 2]) == (1, "score_tiebreak", True)
    assert race.resolve_terminal(repetition, [0, 0]) == (None, "score_draw", True)
    checkmate = SimpleNamespace(status=race.SessionStatus.CHECKMATE, winner=0)
    assert race._core_winner(checkmate) is True
    assert race.resolve_terminal(checkmate, [0, 0]) == (0, "checkmate", True)


@pytest.mark.parametrize("status", [
    race.SessionStatus.CHECKMATE,
    race.SessionStatus.PERPETUAL_CHECK,
    race.SessionStatus.DECLARATION,
    race.SessionStatus.RESIGNATION,
])
def test_formal_core_winners_keep_precedence_on_equal_race_scores(status):
    terminal = SimpleNamespace(status=status, winner=1)
    assert race.resolve_terminal(terminal, [3, 3]) == (1, status.value, True)


def test_threshold_winner_and_safety_terminal_contract():
    assert race.resolve_threshold([3, 0], 0) == (0, "score_threshold", True)
    max_ply = SimpleNamespace(status=race.SessionStatus.MAX_PLY, winner=None)
    assert race.resolve_terminal(max_ply, [2, 1]) == (0, "score_tiebreak", True)
    assert race.resolve_terminal(max_ply, [3, 3]) == (None, "score_draw", True)


def test_draw_win_loss_and_role_swapped_pair_scoring():
    draw0 = {"valid": True, "decisive_reason": "score_draw", "winner": None, "child_owner": 0}
    draw1 = {"valid": True, "decisive_reason": "score_draw", "winner": None, "child_owner": 1}
    win0 = {"valid": True, "decisive_reason": "score_tiebreak", "winner": 0, "child_owner": 0}
    loss1 = {"valid": True, "decisive_reason": "score_tiebreak", "winner": 0, "child_owner": 1}
    win1 = {"valid": True, "decisive_reason": "score_tiebreak", "winner": 1, "child_owner": 1}
    assert race.pair_score([draw0, draw1]) == 0.5
    assert race.pair_score([win0, loss1]) == 0.5
    assert race.pair_score([draw0, win1]) == 0.75
    original = race.pair_score([win0, loss1])
    swapped_roles = [
        dict(win0, child_owner=1, winner=1),
        dict(loss1, child_owner=0, winner=1),
    ]
    assert original == race.pair_score(swapped_roles) == 0.5
    assert race.pair_score([dict(draw0, valid=False), draw1]) is None
    assert race.pair_score([draw0, dict(draw0)]) is None


def test_recorded_equal_score_repetition_retroactively_becomes_a_neutral_draw():
    from pathlib import Path
    import json

    result_path = Path(__file__).resolve().parents[1] / ".generic_chess_flow/f153-mutant4-fresh-single-pair-output/game-owner-0.json"
    if not result_path.is_file():
        pytest.skip("ignored Heavy evidence is only available in the active workspace")
    recorded = json.loads(result_path.read_text(encoding="utf-8"))
    assert recorded["terminal_cause"] == "repetition"
    assert recorded["scores"] == [0, 0]
    assert recorded["completed"] is True
    old = {"valid": recorded["valid"], "decisive_reason": recorded["decisive_reason"],
           "winner": recorded["winner"], "child_owner": recorded["child_owner"]}
    assert old["valid"] is False
    winner, reason, valid = race.resolve_terminal(
        SimpleNamespace(status=race.SessionStatus.REPETITION, winner=None), recorded["scores"]
    )
    replayed = {"valid": valid, "decisive_reason": reason, "winner": winner,
                "child_owner": recorded["child_owner"]}
    assert (winner, reason, valid) == (None, "score_draw", True)
    assert race.child_game_score(replayed) == 0.5
    assert race.pair_score([replayed]) is None
    assert race.pair_score([replayed, dict(replayed)]) is None


def test_f149_pair_task_keeps_two_score_draws_valid_for_opening_selection(monkeypatch):
    from types import SimpleNamespace

    from scripts import f149_shogi_material_score_race_deep_openings as deep_race

    opening = SimpleNamespace(index=0, final_position_key="fresh-root", target_plies=21)
    monkeypatch.setattr(deep_race, "_compile", lambda: object())
    monkeypatch.setattr(deep_race.v2, "_opening_from_payload", lambda _payload: opening)
    monkeypatch.setattr(
        deep_race,
        "play_score_race",
        lambda _compiled, _opening, _champion, _child, owner, _ordering, _limits: {
            "child_owner": owner, "winner": None, "decisive_reason": "score_draw", "valid": True,
        },
    )
    row = deep_race._pair_task({
        "opening": {}, "champion": [], "child": [], "ordering_values": {}, "max_nodes": 1,
    })
    assert row["valid"] is True
    assert row["pair_score"] == 0.5


def test_threshold3_pilot_acceptance_contract():
    assert race.SAFETY_MAX_PLIES == 512
    assert race.PILOT_SEED == 1_460_001
    assert race.SCREENING_SEEDS == {1: 1_461_001, 2: 1_461_002}
    assert race.PROMOTION_SEEDS == {1: 1_462_001, 2: 1_462_002}
