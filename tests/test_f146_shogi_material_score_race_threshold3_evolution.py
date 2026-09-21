from types import SimpleNamespace

from scripts import f146_shogi_material_score_race_threshold3_evolution as race


def test_threshold3_and_source_level_score_independence():
    assert race.SCORE_THRESHOLD == 3
    source = race.inspect.getsource(race.score_event)
    assert "champion" not in source
    assert "child" not in source
    assert "values" not in source


def test_nondecisive_terminal_is_always_invalid():
    assert race._core_winner(SimpleNamespace(status=race.SessionStatus.REPETITION, winner=None)) is False
    assert race._core_winner(SimpleNamespace(status=race.SessionStatus.CHECKMATE, winner=0)) is True


def test_threshold3_pilot_acceptance_contract():
    assert race.SAFETY_MAX_PLIES == 512
    assert race.PILOT_SEED == 1_460_001
    assert race.SCREENING_SEEDS == {1: 1_461_001, 2: 1_461_002}
    assert race.PROMOTION_SEEDS == {1: 1_462_001, 2: 1_462_002}
