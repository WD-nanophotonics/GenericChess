"""Frozen-checkpoint self-play with TDLeaf trajectory collection."""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..ai.limits import SearchLimits
from ..ai.evaluation.config import EvaluationConfig
from ..core.identity import position_identity_key
from ..core.transition import apply_action
from ..native.compiler import compile_native_evaluation
from ..native.engine import NativeSearchEngine
from ..native.semantic_engine import SemanticSearchEngine
from ..session.session import GameSession
from .features import linear_value, material_features, non_anchor_type_ids
from .material import LearnableMaterialCheckpoint
from .tdleaf import _normalized_value
from .trajectory import TrainingPoint, TrainingTrajectory


@dataclass(frozen=True, slots=True)
class SelfPlayConfig:
    games: int = 8
    nodes_per_move: int = 3000
    max_depth: int = 12
    seed: int = 0
    epsilon: float = 0.10
    tt_megabytes: int = 8

    def __post_init__(self) -> None:
        if not (0.0 <= self.epsilon <= 1.0):
            raise ValueError("epsilon must be in [0, 1]")
        if self.nodes_per_move <= 0 or self.max_depth <= 0:
            raise ValueError("node/depth budgets must be positive")


def collect_self_play(
    compiled,
    native_rules,
    checkpoint: LearnableMaterialCheckpoint,
    config: SelfPlayConfig,
) -> list[TrainingTrajectory]:
    """Play ``config.games`` games of Gen-N vs Gen-N with one frozen
    evaluator, recording a TDLeaf trajectory per game."""
    checkpoint.validate_ruleset(compiled)
    from ..rules.ir import CompiledSemanticRuleset

    semantic_path = isinstance(compiled, CompiledSemanticRuleset)
    eval_tables = None if semantic_path else compile_native_evaluation(
        native_rules,
        _dummy_profile(compiled, checkpoint),
        EvaluationConfig(),
        material_override=checkpoint,
    )
    type_ids = non_anchor_type_ids(compiled)
    trajectories: list[TrainingTrajectory] = []
    for game_index in range(config.games):
        game_seed = config.seed * 1000 + game_index
        rng = random.Random(game_seed)
        session = GameSession(compiled)
        engine = (
            SemanticSearchEngine(
                compiled, native_rules, checkpoint=checkpoint,
                tt_megabytes=config.tt_megabytes,
            )
            if semantic_path else NativeSearchEngine(
                compiled, native_rules, eval_tables, config.tt_megabytes
            )
        )
        points: list[TrainingPoint] = []
        ply = 0
        while session.result.status.value == "ongoing":
            result = engine.search(
                session,
                SearchLimits(
                    max_depth=config.max_depth,
                    max_nodes=config.nodes_per_move,
                    quiescence_max_depth=0,
                ),
            )
            pv = result.principal_variation
            if result.completed_depth >= 1 and pv:
                leaf_state = session.state
                for action in pv:
                    leaf_state = apply_action(leaf_state, action, compiled)
                leaf_key = position_identity_key(leaf_state.position, compiled)
                features = material_features(
                    leaf_state.position, type_ids, perspective=0
                )
                u = _normalized_value(
                    features,
                    checkpoint.board_weights,
                    checkpoint.hand_weights,
                    checkpoint.value_scale,
                )
                points.append(
                    TrainingPoint(
                        ply=ply,
                        root_position_key=position_identity_key(
                            session.state.position, compiled
                        ),
                        action=None,  # filled below
                        exploration=False,  # filled below
                        pv=pv,
                        leaf_position_key=leaf_key,
                        leaf_feature_board=features.board_counts,
                        leaf_feature_hand=features.hand_counts,
                        leaf_value=u,
                        completed_depth=result.completed_depth,
                    )
                )
            if getattr(result, "declaration_id", None) is not None:
                session.declare(result.declaration_id)
                break
            legal = session.legal_actions()
            if not legal:
                break
            exploration = rng.random() < config.epsilon
            if exploration:
                action = rng.choice(list(legal))
            else:
                action = result.action if result.action is not None else legal[0]
            if points and points[-1].ply == ply:
                old = points[-1]
                points[-1] = TrainingPoint(
                    ply=old.ply,
                    root_position_key=old.root_position_key,
                    action=action,
                    exploration=exploration,
                    pv=old.pv,
                    leaf_position_key=old.leaf_position_key,
                    leaf_feature_board=old.leaf_feature_board,
                    leaf_feature_hand=old.leaf_feature_hand,
                    leaf_value=old.leaf_value,
                    completed_depth=old.completed_depth,
                )
            session.submit(action)
            ply += 1
        result = session.result
        from ..core.transition import initial_state
        initial_key = position_identity_key(
            initial_state(compiled).position, compiled
        )
        trajectories.append(
            TrainingTrajectory(
                ruleset_fingerprint=compiled.ruleset_fingerprint,
                generation=checkpoint.generation,
                game_seed=game_seed,
                initial_position_key=initial_key,
                actions=tuple(rec.action for rec in session.history),
                search_nodes=config.nodes_per_move,
                search_max_depth=config.max_depth,
                points=tuple(points),
                terminal=result.status.value,
                winner=result.winner,
                type_ids=type_ids,
            )
        )
    return trajectories


def _dummy_profile(compiled, checkpoint):
    """Minimal profile shim satisfying compile_native_evaluation's validation
    when a material override is supplied."""
    from types import SimpleNamespace

    return SimpleNamespace(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        promotion_gain_by_type={
            pt.type_id: 0 for pt in compiled.piece_types
        },
        evaluator_version=checkpoint.evaluator_version,
    )
