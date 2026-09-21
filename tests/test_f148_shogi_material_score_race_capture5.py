from types import SimpleNamespace

from scripts import f148_shogi_material_score_race_capture5 as race


def test_capture5_scoring_contract():
    assert race.SCORE_THRESHOLD == 10
    assert race.CAPTURE_POINTS == 5
    assert race.CHECK_POINTS == 1
    assert race.race_points(1, 0) == 5
    assert race.race_points(0, 1) == 1
    assert race.race_points(1, 1) == 6
    assert race.resolve_threshold([5, 0], 0) == (None, "", False)
    assert race.resolve_threshold([10, 0], 0) == (0, "score_threshold", True)


def test_anchor_and_king_captures_get_no_capture_points():
    compiled = SimpleNamespace(types_by_id={"K": SimpleNamespace(is_anchor=True), "P": SimpleNamespace(is_anchor=False)})
    king = SimpleNamespace(owner=1, current_type_id="K")
    pawn = SimpleNamespace(owner=1, current_type_id="P")
    assert race._capture_value(king, 0, compiled) == 0
    assert race._capture_value(pawn, 0, compiled) == 5
    assert race._capture_value(None, 0, compiled) == 0


def test_formal_and_terminal_precedence():
    checkmate = SimpleNamespace(status=race.SessionStatus.CHECKMATE, winner=0)
    repetition = SimpleNamespace(status=race.SessionStatus.REPETITION, winner=None)
    assert race.resolve_terminal(checkmate, [0, 0]) == (0, "checkmate", True)
    assert race.resolve_terminal(repetition, [5, 0]) == (0, "score_tiebreak", True)
    assert race.resolve_terminal(repetition, [5, 5]) == (None, "invalid_equal_score_terminal", False)


def test_source_has_no_material_vector_input_and_gen0_parity():
    source = race.inspect.getsource(race.score_event)
    assert "champion" not in source
    assert "child" not in source
    assert "values" not in source
    assert tuple(race.gen0_vector(race.GEN0_SEED)) == (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)


def test_f148_seed_and_schema_contract():
    assert race.PILOT_SEED == 1_480_001
    assert race.DISCRIMINATION_SEED == 1_480_101
    assert race.SCREENING_SEEDS == {1: 1_481_001, 2: 1_481_002}
    assert race.PROMOTION_SEEDS == {1: 1_482_001, 2: 1_482_002}
    assert race.PILOT_POOL_OPENINGS >= 64
    assert race.DISCRIMINATION_POOL_OPENINGS >= 96
    assert race.COMMON_POOL_OPENINGS >= 128
    assert race.PROMOTION_POOL_OPENINGS >= 256
