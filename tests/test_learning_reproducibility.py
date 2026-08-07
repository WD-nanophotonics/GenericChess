"""Learning Phase 1: deterministic reproduction of training runs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, requires_native


@requires_native
def test_experiment_payload_is_deterministic():
    compiled = generated_compiled(size=4)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    rules = compile_native_rules(compiled)
    checkpoint = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=11
    )
    selfplay_cfg = SelfPlayConfig(
        games=2, nodes_per_move=200, max_depth=4, seed=11
    )
    td_cfg = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=0.1)
    outputs = []
    for _ in range(2):
        trajectories = collect_self_play(compiled, rules, checkpoint, selfplay_cfg)
        update = tdleaf_update(trajectories, checkpoint, td_cfg)
        child = checkpoint.child_checkpoint(
            board_weights=update.board_weights,
            hand_weights=update.hand_weights,
            games_seen_delta=len(trajectories),
            positions_seen_delta=update.positions_seen,
            training_updates_delta=1,
            training_config_hash="cfg",
            training_seed=11,
        )
        outputs.append(
            (
                child.checkpoint_id,
                [t.trajectory_id for t in trajectories],
                child.board_weights,
            )
        )
    assert outputs[0] == outputs[1]
