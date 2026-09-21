from types import SimpleNamespace

from scripts import f151_shogi_material_paired_score_microprobe as probe


def test_contract_is_bounded_and_frozen():
    assert probe.MICROPROBE_SEED == 1_510_101
    assert probe.MICROPROBE_OPENING_COUNT == 32
    assert probe.INITIAL_OPENING_COUNT == 16
    assert probe.MAX_STAGE_B_PAIRS == 2
    assert probe.SEARCH_LIMITS.max_nodes == 1000
    assert probe.SEARCH_LIMITS.max_depth == 12
    assert probe.SEARCH_LIMITS.quiescence_max_depth == 4
    assert probe.SEARCH_LIMITS.quiescence_hard_max_depth == 8


def test_historical_vectors_are_distinct_and_gen0_is_exact():
    expected = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    assert tuple(probe.gen0_vector(probe.GEN0_SEED)) == expected
    vectors = probe.diagnostic_vectors()
    assert tuple(vectors["Gen0"]) == expected
    assert tuple(vectors["M140"]) != expected
    assert probe.M140_SEED == 1_440_401
    assert probe.M140_SIGMA == 1.40


def test_action_key_is_stable():
    action = {"kind": "move", "from_square": "7g", "to_square": "7f"}
    assert probe._action_key(action) == probe._action_key(dict(reversed(tuple(action.items()))))
    assert probe._action_key(None) is None


def test_classification_no_leverage():
    rows = [{"action_disagreement": False}]
    assert probe._classification(rows, []) == "MATERIAL_VECTOR_NO_ABP_DECISION_LEVERAGE_MICROPROBE"


def test_classification_unscorable():
    rows = [{"action_disagreement": True}]
    pairs = [{"valid": False, "pair_score_differs_from_half": False}]
    assert probe._classification(rows, pairs) == "MATERIAL_VECTOR_CHANGES_DECISIONS_BUT_SCORE_RACE_UNSCORABLE_MICROPROBE"


def test_classification_discrimination():
    rows = [{"action_disagreement": True}]
    pairs = [{"valid": True, "pair_score": 1.0, "pair_score_differs_from_half": True}]
    assert probe._classification(rows, pairs) == "MATERIAL_VECTOR_PRODUCES_PAIRED_SCORE_DISCRIMINATION_MICROPROBE"


def test_classification_cancellation():
    rows = [{"action_disagreement": True}]
    pairs = [{"valid": True, "pair_score": 0.5, "pair_score_differs_from_half": False}]
    assert probe._classification(rows, pairs) == "MATERIAL_VECTOR_CHANGES_DECISIONS_BUT_PAIRED_SCORE_CANCELS_MICROPROBE"


def test_trajectory_annotation_records_hash_and_cancellation():
    pair = {
        "games": [
            {"actions": [{"actor": 0, "action": {"kind": "a"}}]},
            {"actions": [{"actor": 0, "action": {"kind": "a"}}]},
        ],
        "pair_score": 0.5,
    }
    annotated = probe._annotate_pair(pair)
    assert all(len(game["action_sequence_sha256"]) == 64 for game in annotated["games"])
    assert annotated["role_swapped_action_trajectories_identical"] is True
    assert annotated["pair_score_differs_from_half"] is False


def test_score_race_contract_matches_f149():
    assert probe.race.SCORE_THRESHOLD == 10
    assert probe.race.CAPTURE_POINTS == 1
    assert probe.race.CHECK_POINTS == 1
    assert probe.race.OPENING_MIN_PLIES == 16
    assert probe.race.OPENING_MAX_PLIES == 32
