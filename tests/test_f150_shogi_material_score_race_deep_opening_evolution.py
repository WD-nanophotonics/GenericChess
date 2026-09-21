from types import SimpleNamespace

from scripts import f150_shogi_material_score_race_deep_opening_evolution as race


def test_f149_calibration_and_valid_outcome_contract():
    assert race.SCREENING_TARGET_PAIRS == 4
    assert race.DISCRIMINATION_TARGET_PAIRS == 12
    assert race.PROMOTION_TARGET_PAIRS == 24
    assert race._base_result(SimpleNamespace(ruleset_fingerprint="x"), {}, race.gen0_vector(), 4)["f149_calibration"]["scored_outcome_fraction"] == 16 / 22
    assert "score_tiebreak" in race._base_result(SimpleNamespace(ruleset_fingerprint="x"), {}, race.gen0_vector(), 4)["score_race"]["valid_outcomes"]


def test_self_pair_semantics_remain_exactly_half_for_valid_pairs():
    assert race.race.resolve_terminal(SimpleNamespace(status=race.race.SessionStatus.REPETITION, winner=None), [1, 1]) == (None, "invalid_equal_score_terminal", False)
    assert race.race.resolve_threshold([10, 0], 0) == (0, "score_threshold", True)


def test_gen0_and_m140_parity():
    expected = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    assert tuple(race.gen0_vector(race.GEN0_SEED)) == expected
    vectors = race.diagnostic_vectors()
    assert tuple(vectors["Gen0"]) == expected
    assert tuple(vectors["M140"]) != expected


def test_f150_seeds_and_deep_openings_are_frozen():
    assert race.DISCRIMINATION_SEED == 1_500_101
    assert race.SCREENING_SEEDS == {1: 1_501_001, 2: 1_501_002}
    assert race.PROMOTION_SEEDS == {1: 1_502_001, 2: 1_502_002}
    assert race.race.OPENING_MIN_PLIES == 16
    assert race.race.OPENING_MAX_PLIES == 32
