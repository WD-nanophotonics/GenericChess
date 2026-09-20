import numpy as np

from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CorrectedShogiFrozenBasisV2
from scripts.f138_corrected_shogi_targeted_gauge_coverage_a1 import (
    BASELINE,
    GENERATOR_SEED,
    TRAJECTORY_LENGTHS,
    _prepare_augmented,
    _target_signature,
    _target_value,
)


def test_f138_baseline_and_generator_contract():
    assert BASELINE == "50e02a9be7042b4c89a5313740f78a2165831124"
    assert GENERATOR_SEED == 1380201
    assert TRAJECTORY_LENGTHS == (8, 24, 64, 128, 192, 256)


def test_f138_target_inspection_reads_only_position_occupancy():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    state = initial_state(compiled)
    assert _target_value(state, "occupancy_diff:P:0:6") == -1.0
    assert _target_value(state, "occupancy_diff:P:0:0") == 0.0
    signature = _target_signature(state, ["occupancy_diff:P:0:6", "occupancy_diff:R:1:0"])
    assert signature == {"occupancy_diff:P:0:6": -1.0, "occupancy_diff:R:1:0": 0.0}


def test_f138_augmented_prepare_uses_train_only_normalization():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = CorrectedShogiFrozenBasisV2("standard_shogi", compiled)
    vector = basis.vector(initial_state(compiled)).tolist()
    rows = {split: [{"features": vector, "oracle": 0.0, "identity": split, "split": split}] for split in ("train", "dev", "holdout")}
    rows["train"].append({"features": (np.asarray(vector) + 1.0).tolist(), "oracle": 1.0, "identity": "train-2", "split": "train"})
    pack = _prepare_augmented(rows, basis)
    assert pack["design"]["train"].shape[0] == 2
    assert pack["design"]["dev"].shape[0] == 1
    assert pack["feature_mean"].shape[0] == len(basis.names)
