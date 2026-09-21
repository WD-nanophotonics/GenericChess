from types import SimpleNamespace

from scripts import f146_shogi_material_score_race_threshold3_evolution as race


def test_threshold3_and_source_level_score_independence():
    assert race.SCORE_THRESHOLD == 3
    source = race.inspect.getsource(race.score_event)
    assert "champion" not in source
    assert "child" not in source
    assert "values" not in source


def test_nondecisive_terminal_is_always_invalid():
    repetition = SimpleNamespace(status=race.SessionStatus.REPETITION, winner=None)
    assert race._core_winner(repetition) is False
    assert race.resolve_terminal(repetition, [1, 2]) == (None, "invalid_nondecisive_terminal", False)
    assert race.resolve_terminal(repetition, [5, 5]) == (None, "invalid_nondecisive_terminal", False)
    checkmate = SimpleNamespace(status=race.SessionStatus.CHECKMATE, winner=0)
    assert race._core_winner(checkmate) is True
    assert race.resolve_terminal(checkmate, [0, 0]) == (0, "checkmate", True)


def test_threshold_winner_and_safety_terminal_contract():
    assert race.resolve_threshold([3, 0], 0) == (0, "score_threshold", True)
    max_ply = SimpleNamespace(status=race.SessionStatus.MAX_PLY, winner=None)
    assert race.resolve_terminal(max_ply, [2, 1]) == (None, "invalid_nondecisive_terminal", False)


def test_threshold3_pilot_acceptance_contract():
    assert race.SAFETY_MAX_PLIES == 512
    assert race.PILOT_SEED == 1_460_001
    assert race.SCREENING_SEEDS == {1: 1_461_001, 2: 1_461_002}
    assert race.PROMOTION_SEEDS == {1: 1_462_001, 2: 1_462_002}
