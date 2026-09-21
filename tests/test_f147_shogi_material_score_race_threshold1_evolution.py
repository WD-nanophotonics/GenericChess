from types import SimpleNamespace

from scripts import f147_shogi_material_score_race_threshold1_evolution as race
from scripts.f145_shogi_material_only_fitness_signal_diagnosis import diagnostic_vectors


def test_threshold1_contract_and_source_level_score_independence():
    assert race.SCORE_THRESHOLD == 1
    assert race.SAFETY_MAX_PLIES == 512
    source = race.inspect.getsource(race.score_event)
    assert "champion" not in source
    assert "child" not in source
    assert "values" not in source


def test_first_capture_or_check_immediately_wins():
    assert race.resolve_threshold([1, 0], 0) == (0, "score_threshold", True)
    assert race.resolve_threshold([0, 1], 1) == (1, "score_threshold", True)


def test_formal_winner_precedes_threshold_and_zero_score_repetition_is_invalid():
    checkmate = SimpleNamespace(status=race.SessionStatus.CHECKMATE, winner=0)
    declaration = SimpleNamespace(status=race.SessionStatus.DECLARATION, winner=1)
    repetition = SimpleNamespace(status=race.SessionStatus.REPETITION, winner=None)
    assert race.resolve_terminal(checkmate, [0, 0]) == (0, "checkmate", True)
    assert race.resolve_terminal(declaration, [0, 0]) == (1, "declaration", True)
    assert race.resolve_terminal(repetition, [0, 0]) == (None, "invalid_equal_score_terminal", False)


def test_unequal_nondecisive_terminal_uses_restored_tiebreak():
    max_ply = SimpleNamespace(status=race.SessionStatus.MAX_PLY, winner=None)
    assert race.resolve_terminal(max_ply, [1, 0]) == (0, "score_tiebreak", True)


def test_f146_parity_and_f145_m140_are_deterministic():
    expected = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    vectors = diagnostic_vectors()
    assert tuple(vectors["Gen0"]) == expected
    assert tuple(race.gen0_vector(race.GEN0_SEED)) == expected
    assert race._vector_record(tuple(vectors["M140"])) == race._vector_record(tuple(diagnostic_vectors()["M140"]))


def test_f147_seeds_and_schema_contract():
    assert race.PILOT_SEED == 1_470_001
    assert race.DISCRIMINATION_SEED == 1_470_101
    assert race.SCREENING_SEEDS == {1: 1_471_001, 2: 1_471_002}
    assert race.PROMOTION_SEEDS == {1: 1_472_001, 2: 1_472_002}
    assert race.COMMON_POOL_OPENINGS >= 128
    assert race.PROMOTION_POOL_OPENINGS >= 256
    assert race._base_result(SimpleNamespace(ruleset_fingerprint="x"), {}, race.gen0_vector(), 4)["schema"] == "F147_SHOGI_MATERIAL_SCORE_RACE_V3"
