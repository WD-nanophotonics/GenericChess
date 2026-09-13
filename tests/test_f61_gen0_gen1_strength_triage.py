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


def test_generated_fixture_executes_same_smoke_fit_and_arena_path():
    compiled, native, parent, ruleset_id = triage._generated_context()
    records = triage._d0_records(compiled, 620101, count=3, smoke=True)
    child, training = triage._fit_one(compiled, native, parent, records, smoke=True)
    arena = triage._arena(compiled, native, parent, child, seed=620701, smoke=True)
    assert ruleset_id == "gen_classic_like_4_101"
    assert compiled._legacy_compiled.ruleset_fingerprint == compiled.ruleset_fingerprint
    assert child.parent_checkpoint_id == parent.checkpoint_id
    assert training["training_roots"] >= 1
    assert arena["pair_count"] == 2
    assert len(arena["pair_scores"]) == 2
