"""Frozen-checkpoint self-play with TDLeaf trajectory collection."""

from __future__ import annotations

import random
from copy import copy
from dataclasses import dataclass

from ..ai.limits import SearchLimits
from ..ai.evaluation.config import EvaluationConfig
from ..core.identity import position_identity_key
from ..core.transition import apply_action
from ..core.terminal import TerminalStatus
from ..native.compiler import compile_native_evaluation
from ..native.engine import NativeSearchEngine
from ..native.semantic_engine import SemanticSearchEngine
from ..session.session import GameSession
from .features import dynamic_features, linear_value, material_features, non_anchor_type_ids
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
    max_plies: int | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.epsilon <= 1.0):
            raise ValueError("epsilon must be in [0, 1]")
        if self.nodes_per_move <= 0 or self.max_depth <= 0:
            raise ValueError("node/depth budgets must be positive")
        if self.max_plies is not None and self.max_plies <= 0:
            raise ValueError("max_plies must be positive when supplied")


def collect_self_play(
    compiled,
    native_rules,
    checkpoint: LearnableMaterialCheckpoint,
    config: SelfPlayConfig,
) -> list[TrainingTrajectory]:
    """Play ``config.games`` games of Gen-N vs Gen-N with one frozen
    evaluator, recording a TDLeaf trajectory per game."""
    if checkpoint.compact_nonlinear:
        raise NotImplementedError("TDLeaf collection does not support compact nonlinear checkpoints")
    checkpoint.validate_ruleset(compiled)
    from ..rules.ir import CompiledSemanticRuleset

    semantic_path = isinstance(compiled, CompiledSemanticRuleset)
    if not semantic_path and (checkpoint.spatial_occupancy_weights or checkpoint.localized_control_weights):
        raise NotImplementedError("spatial TDLeaf collection requires semantic Native evaluation")
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
        while (
            session.result.status.value == "ongoing"
            and (config.max_plies is None or ply < config.max_plies)
        ):
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
                if semantic_path and any(isinstance(step, str) for step in
                                         getattr(result, "decision_line", ())):
                    raise NotImplementedError(
                        "TDLeaf declaration-ended PV requires a complete declaration leaf record"
                    )
                leaf_state = session.state
                for action in pv:
                    leaf_state = apply_action(leaf_state, action, compiled)
                if (semantic_path and compiled.ir.declarations
                        and not leaf_state.terminal_status.is_terminal):
                    from ..core.declarations import available_declarations
                    if any(claim.outcome in ("RESTART", "NO_CONTEST") for claim in
                           available_declarations(leaf_state, compiled)):
                        # Native neutral floors can omit the claim from the line.
                        # Refuse this unsupported target rather than fabricate W/L/D
                        # or train on a physical leaf that omits the declaration.
                        raise NotImplementedError(
                            "TDLeaf PV leaf with a non-scoring declaration is unsupported"
                        )
                leaf_key = position_identity_key(leaf_state.position, compiled)
                features = material_features(
                    leaf_state.position, type_ids, perspective=0
                )
                dynamic = (
                    result.dynamic_features
                    if semantic_path
                    else dynamic_features(leaf_state.position, compiled).as_tuple()
                )
                spatial, control = _spatial_snapshot(
                    compiled, native_rules, session, pv, checkpoint, leaf_state
                )
                u = _normalized_value(
                    features,
                    checkpoint.board_weights,
                    checkpoint.hand_weights,
                    checkpoint.value_scale,
                    dynamic,
                    checkpoint.dynamic_weights,
                    dict(spatial), checkpoint.spatial_occupancy_weights,
                    control, checkpoint.localized_control_weights,
                )
                leaf_terminal_z = None
                if leaf_state.terminal_status.is_terminal:
                    if leaf_state.terminal_status.status is TerminalStatus.NO_CONTEST:
                        raise ValueError("non-scoring PV leaf cannot be a TDLeaf W/L/D target")
                    winner = leaf_state.terminal_status.winner
                    leaf_terminal_z = 0.0 if winner is None else 1.0 if winner == 0 else -1.0
                    u = leaf_terminal_z
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
                        leaf_feature_dynamic=tuple(dynamic),
                        leaf_terminal_z=leaf_terminal_z,
                        leaf_feature_spatial=spatial,
                        leaf_feature_control=control,
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
                    leaf_feature_dynamic=old.leaf_feature_dynamic,
                    leaf_terminal_z=old.leaf_terminal_z,
                    leaf_feature_spatial=old.leaf_feature_spatial,
                    leaf_feature_control=old.leaf_feature_control,
                )
            session.submit(action)
            ply += 1
        result = session.result
        truncated = result.status.value == "ongoing"
        bootstrap_value = None
        if truncated:
            termination_reason = (
                "max_plies"
                if config.max_plies is not None and ply >= config.max_plies
                else "ongoing_after_loop"
            )
            # A code-level ply cap is a nonterminal cutoff, never a draw. Use
            # the frozen parent evaluator for TDLeaf's explicit bootstrap.
            current_features = material_features(
                session.state.position, type_ids, perspective=0
            )
            if semantic_path:
                from ..native.semantic import dynamic_features as native_dynamic_features
                from ..native.adapter import pack_semantic_search_position

                current_position = pack_semantic_search_position(
                    compiled, native_rules, session
                )
                current_dynamic = native_dynamic_features(
                    native_rules, current_position
                )
            else:
                current_dynamic = dynamic_features(
                    session.state.position, compiled
                ).as_tuple()
            spatial, control = _spatial_snapshot(
                compiled, native_rules, session, (), checkpoint, session.state
            )
            bootstrap_value = _normalized_value(
                current_features,
                checkpoint.board_weights,
                checkpoint.hand_weights,
                checkpoint.value_scale,
                current_dynamic,
                checkpoint.dynamic_weights,
                dict(spatial), checkpoint.spatial_occupancy_weights,
                control, checkpoint.localized_control_weights,
            )
        else:
            termination_reason = result.status.value
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
                termination_reason=termination_reason,
                truncated=truncated,
                bootstrap_value=bootstrap_value,
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


def _spatial_snapshot(compiled, native_rules, session, pv, checkpoint, leaf_state):
    """Frozen v3 offsets, with exact Native control semantics and full history.

    The private session copy retains immutable state, records and every history
    witness; submitting its PV cannot mutate the live parent. Occupancy is a
    position-only feature. Scoring terminal constants need neither offset.
    """
    if leaf_state.terminal_status.is_terminal:
        return (), ()
    spatial = ()
    if checkpoint.spatial_occupancy_weights:
        from .features import spatial_occupancy_features
        spatial = tuple(sorted(spatial_occupancy_features(
            leaf_state.position, tuple(native_rules.type_ids)
        ).items()))
    control = ()
    if checkpoint.localized_control_weights:
        from ..native.adapter import pack_semantic_search_position
        from ..native.semantic import spatial_features
        leaf_session = session
        if pv:
            leaf_session = copy(session)
            for action in pv:
                leaf_session.submit(action)
        packed = pack_semantic_search_position(compiled, native_rules, leaf_session)
        control = spatial_features(native_rules, packed)["localized_control"]
    return spatial, control
