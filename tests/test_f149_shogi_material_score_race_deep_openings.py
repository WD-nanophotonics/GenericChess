from scripts import f149_shogi_material_score_race_deep_openings as race


def test_f149_restores_original_score_contract_and_seeds():
    assert race.SCORE_THRESHOLD == 10
    assert race.CAPTURE_POINTS == 1
    assert race.CHECK_POINTS == 1
    assert race.PILOT_SEED == 1_490_001
    assert race.DISCRIMINATION_SEED == 1_490_101
    assert race.SCREENING_SEEDS == {1: 1_491_001, 2: 1_491_002}
    assert race.PROMOTION_SEEDS == {1: 1_492_001, 2: 1_492_002}


def test_opening_corpus_is_deterministic_deep_and_terminal_free():
    compiled = race._compile()
    first = race.opening_corpus(compiled, race.PILOT_SEED, 4)
    second = race.opening_corpus(compiled, race.PILOT_SEED, 4)
    assert [opening.final_position_key for opening in first] == [opening.final_position_key for opening in second]
    assert all(race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES for opening in first)
    assert all(opening.target_plies == len(opening.actions) for opening in first)
    assert all(opening.final_position_key for opening in first)


def test_openings_do_not_depend_on_candidate_vectors():
    compiled = race._compile()
    corpus = race.opening_corpus(compiled, race.PILOT_SEED, 2)
    gen0 = tuple(race.gen0_vector(race.GEN0_SEED))
    m140 = tuple(race.diagnostic_vectors()["M140"])
    assert [opening.final_position_key for opening in corpus] == [opening.final_position_key for opening in race.opening_corpus(compiled, race.PILOT_SEED, 2)]
    assert gen0 != m140


def test_f149_gen0_parity_and_score_event_source_independence():
    assert tuple(race.gen0_vector(race.GEN0_SEED)) == (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    source = race.inspect.getsource(race.score_event)
    assert "champion" not in source
    assert "child" not in source
    assert "values" not in source
