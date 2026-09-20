from scripts.f141_corrected_shogi_known_oracle_t1_compression import (
    BASELINE,
    SHARD_SCHEMA,
    SHARD_SIZE,
    T1_GATE_NRMSE,
)


def test_f141_binds_the_published_f140_checkpoint():
    assert BASELINE == "b82e088196b01342352b01bbd1c9599d435532cd"


def test_f141_uses_fresh_fixed_size_corrected_shards():
    assert SHARD_SCHEMA == "F141_CORRECTED_T1_LABEL_SHARD_V1"
    assert SHARD_SIZE == 128
    assert T1_GATE_NRMSE == 0.15
