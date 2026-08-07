"""Learning Phase 1.5: experiment provenance (pre-config / calibration /
final config / checkpoint hashes)."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.learning import experiment
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256

from native_test_helpers import generated_compiled, requires_native


def _params(seed=7):
    return {
        "training_seed": seed,
        "generations": 2,
        "selfplay_games": 2,
        "selfplay_nodes": 200,
        "arena_pairs": 2,
        "arena_nodes": 200,
        "arena_opening_seed": 314159,
        "arena_opening_count": 2,
        "arena_min_plies": 2,
        "arena_max_plies": 4,
        "alpha": None,
        "alpha_target_l2_fraction": 0.10,
        "alpha_max_multiplier": 200.0,
        "lambda": 0.7,
        "gamma": 1.0,
        "max_depth": 6,
        "epsilon": 0.1,
        "tt_mb": 4,
    }


@requires_native
def test_provenance_three_stage():
    compiled = generated_compiled(size=4)
    openings = generate_arena_openings(
        compiled, count=2, seed=314159, min_plies=2, max_plies=4
    )
    out = (
        Path.cwd()
        / "artifacts"
        / "learning_phase1_5"
        / f"_test_provenance_{int(time.time() * 1000)}"
    )
    experiment._run_experiment(
        "test", None, compiled, _params(), out, openings=openings
    )

    # Stage 1: pre-calibration config must NOT contain the derived alpha.
    pre = json.loads((out / "pre_calibration_config.json").read_text())
    assert "calibrated_alpha" not in pre
    assert pre["alpha_target_l2_fraction"] == 0.10

    # Stage 2: calibration artifact traces the trajectories.
    cal = json.loads((out / "calibration.json").read_text())
    assert cal["calibrated_alpha"] > 0
    assert cal["number_of_trajectories"] == 2
    assert cal["trajectory_ids"]

    # Stage 3: final config has the real hash.
    final = json.loads((out / "final_config.json").read_text())
    config = json.loads((out / "config.json").read_text())
    assert final == config
    recorded = final["training_config_hash"]
    recomputed = stable_sha256(
        {k: v for k, v in final.items() if k != "training_config_hash"}
    )
    assert recorded == recomputed
    assert final["calibrated_alpha"] == cal["calibrated_alpha"]
    assert final["calibration_artifact_hash"] == cal["calibration_artifact_hash"]

    # Every child checkpoint carries the same final hash.
    for gen in (1, 2):
        data = json.loads(
            (out / f"generation_{gen:03d}.json").read_text()
        )
        child = LearnableMaterialCheckpoint.from_dict(data["child"])
        assert child.training_config_hash == recorded
        assert child.schema_version == 2


@requires_native
def test_changing_calibrated_alpha_changes_hash():
    compiled = generated_compiled(size=4)
    openings = generate_arena_openings(
        compiled, count=2, seed=314159, min_plies=2, max_plies=4
    )
    base = (
        Path.cwd()
        / "artifacts"
        / "learning_phase1_5"
        / f"_test_provenance_{int(time.time() * 1000)}"
    )
    out_a = base / "a"
    out_b = base / "b"
    experiment._run_experiment(
        "test", None, compiled, _params(), out_a, openings=openings
    )
    # Force a different alpha path by changing the target fraction.
    params_b = _params()
    params_b["alpha_target_l2_fraction"] = 0.20
    experiment._run_experiment(
        "test", None, compiled, params_b, out_b, openings=openings
    )
    fa = json.loads((out_a / "final_config.json").read_text())
    fb = json.loads((out_b / "final_config.json").read_text())
    assert fa["training_config_hash"] != fb["training_config_hash"]
