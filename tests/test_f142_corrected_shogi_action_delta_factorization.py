from scripts.f142_corrected_shogi_action_delta_factorization import BASELINE, RAW_WIDTH, SHARD_SCHEMA


def test_f142_binds_the_published_f141_checkpoint():
    assert BASELINE == "576a14430b512a15f90e1368f59263ab3334e989"


def test_f142_uses_the_exact_transition_delta_contract():
    assert RAW_WIDTH == 1086
    assert SHARD_SCHEMA == "F141_CORRECTED_T1_LABEL_SHARD_V1"
