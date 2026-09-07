"""Static contracts for the F63 causal triage harness."""

from scripts import f63_champion_loop_causal_triage as f63


def test_f63_freezes_teacher_gate_and_candidate_population():
    assert f63.WORK_ORDER == "GENERICCHESS-F63-CHAMPION-LOOP-CAUSAL-TRIAGE"
    assert f63.SHALLOW_NODES == 2_000
    assert f63.DEEP_NODES == 20_000
    assert f63.GEN2_SEEDS == (59011, 59012, 59013)
    assert f63.F62_STAGE_SHA == (
        "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
    )
    assert f63.F62_RECORDS_SHA == (
        "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
    )


def test_f63_teacher_gate_is_stricter_than_a_tied_triage():
    tied = {
        "mean_pair_score": 0.5,
        "child_better_pairs": 2,
        "child_worse_pairs": 2,
    }
    clear = {
        "mean_pair_score": 0.75,
        "child_better_pairs": 3,
        "child_worse_pairs": 1,
    }
    assert not f63._teacher_is_clearly_supported(tied)
    assert f63._teacher_is_clearly_supported(clear)
