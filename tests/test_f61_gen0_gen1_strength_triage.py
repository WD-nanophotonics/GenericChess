from scripts import f61_gen0_gen1_strength_triage as triage


def test_strength_triage_freezes_small_ruleset_order_and_real_strength_gate():
    assert triage.RULESET_ORDER == (
        "B_CANONICAL_STANDARD_SHOGI",
        "A_CANONICAL_WESTERN_CHESS",
        "GEN_CLASSIC_LIKE_4_101",
    )
    assert triage.ROOT_COUNT == 24
    assert triage.ARENA_PAIRS == 4
    assert triage._directional_failure({
        "mean_pair_score": 0.49,
        "child_better_pairs": 1,
        "child_worse_pairs": 3,
    })
    assert not triage._directional_failure({
        "mean_pair_score": 0.49,
        "child_better_pairs": 3,
        "child_worse_pairs": 1,
    })
