from dataclasses import replace

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.features import (
    DYNAMIC_FEATURE_NAMES,
    SPATIAL_CELL_COUNT,
    localized_control_features,
    material_features,
    spatial_occupancy_features,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.learning.trajectory import TrainingPoint, TrainingTrajectory
from generic_chess.native import native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.semantic import (
    dynamic_features as native_dynamic_features,
    evaluate as native_evaluate,
    spatial_features as native_spatial_features,
)
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


pytestmark = pytest.mark.skipif(not native_available(), reason="native extension unavailable")


def _compiled(ruleset):
    compiled = compile_semantic_ruleset(ruleset)
    return compiled, compile_native_semantic_rules(compiled)


def _v2_parent(compiled, ruleset):
    legacy = compile_ruleset_for_execution(ruleset)
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    return LearnableMaterialCheckpoint.from_profile(
        compiled, profile,
        dynamic_weights={"mobility": 2.0, "promotion_potential": 3.0, "anchor_safety": 5.0},
        training_seed=5600000,
    )


def _v3_checkpoint(parent, type_ids):
    spatial = {}
    for owner in (0, 1):
        for type_id in type_ids:
            row = [0.0] * SPATIAL_CELL_COUNT
            if type_id == type_ids[0]:
                row[0] = 1.0 + owner
                row[-1] = -(1.0 + owner)
            spatial[f"{owner}:{type_id}"] = tuple(row)
    control = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0)
    return parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        spatial_occupancy_weights=spatial,
        localized_control_weights=control,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="f56-test",
        training_seed=5600001,
    )


def test_f56_spatial_features_match_native_on_western_and_shogi():
    for ruleset in (build_western_chess_ruleset(), build_standard_shogi_ruleset()):
        compiled, native = _compiled(ruleset)
        session = GameSession(compiled)
        packed = pack_semantic_search_position(compiled, native, session)
        native_values = native_spatial_features(native, packed)
        type_ids = tuple(native.type_ids)
        python_occupancy = spatial_occupancy_features(session.state.position, type_ids)
        python_vector = tuple(
            value
            for owner in (0, 1)
            for type_id in type_ids
            for value in python_occupancy[f"{owner}:{type_id}"]
        ) + localized_control_features(session.state.position, compiled)
        assert tuple(native_values["occupancy"]) == python_vector[: len(native_values["occupancy"])]
        assert tuple(native_values["localized_control"]) == python_vector[len(native_values["occupancy"]):]
        assert sum(native_values["localized_control"]) == 0


def test_f56_owner_axis_keeps_asymmetric_spatial_witness_and_zero_mean():
    ruleset = build_western_chess_ruleset()
    compiled, native = _compiled(ruleset)
    parent = _v2_parent(compiled, ruleset)
    checkpoint = _v3_checkpoint(parent, tuple(native.type_ids))
    checkpoint.validate_ruleset(compiled)
    assert checkpoint.evaluator_version == "learnable-generic-v3"
    assert checkpoint.spatial_occupancy_weights["0:" + native.type_ids[0]][0] != checkpoint.spatial_occupancy_weights["1:" + native.type_ids[0]][0]
    assert all(abs(sum(row)) < 1e-12 for row in checkpoint.spatial_occupancy_weights.values())
    assert abs(sum(checkpoint.localized_control_weights)) < 1e-12
    assert checkpoint.checkpoint_id != parent.checkpoint_id


def test_f56_native_leaf_score_matches_python_fixed_point_owner0_convention():
    ruleset = build_western_chess_ruleset()
    compiled, native = _compiled(ruleset)
    parent = _v2_parent(compiled, ruleset)
    checkpoint = _v3_checkpoint(parent, tuple(native.type_ids))
    session = GameSession(compiled)
    packed = pack_semantic_search_position(compiled, native, session)
    type_ids = tuple(native.type_ids)
    position = session.state.position
    material_type_ids = tuple(sorted(parent.board_weights))
    material = material_features(position, material_type_ids, perspective=0)
    dynamic = native_dynamic_features(native, packed)
    occupancy = spatial_occupancy_features(position, type_ids)
    control = localized_control_features(position, compiled)
    material_board_q = checkpoint.semantic_quantized_board(material_type_ids)
    material_hand_q = checkpoint.semantic_quantized_hand(material_type_ids)
    score_owner0 = sum(
        board_q * count + hand_q * hand
        for board_q, hand_q, count, hand in zip(
            material_board_q, material_hand_q,
            material.board_counts, material.hand_counts,
        )
    )
    dynamic_q = checkpoint.semantic_quantized_dynamic()
    score_owner0 += sum(q * value for q, value in zip(dynamic_q, dynamic))
    spatial_q = checkpoint.semantic_quantized_spatial(type_ids)
    cursor = 0
    for owner in (0, 1):
        for type_id in type_ids:
            score_owner0 += sum(
                spatial_q[cursor + cell] * occupancy[f"{owner}:{type_id}"][cell]
                for cell in range(SPATIAL_CELL_COUNT)
            )
            cursor += SPATIAL_CELL_COUNT
    control_q = checkpoint.semantic_quantized_localized_control()
    score_owner0 += sum(q * value for q, value in zip(control_q, control))
    expected = score_owner0 if position.side_to_move == 0 else -score_owner0
    actual = native_evaluate(
        native, packed,
        board_values=checkpoint.semantic_quantized_board(type_ids),
        hand_values=checkpoint.semantic_quantized_hand(type_ids),
        dynamic_values=dynamic_q,
        spatial_occupancy_values=spatial_q,
        localized_control_values=control_q,
        evaluator_scale=checkpoint.semantic_native_scale,
    )
    assert actual == expected


def test_f56_v3_rebind_clears_tt_without_ruleset_recompile():
    ruleset = build_standard_shogi_ruleset()
    compiled, native = _compiled(ruleset)
    parent = _v2_parent(compiled, ruleset)
    first = _v3_checkpoint(parent, tuple(native.type_ids))
    second = replace(first, localized_control_weights=(-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0))
    engine = SemanticSearchEngine(compiled, native, checkpoint=first, tt_megabytes=1)
    engine.search(GameSession(compiled), __import__("generic_chess.ai.limits", fromlist=["SearchLimits"]).SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0))
    assert engine.tt_info()["occupied_entries"] > 0
    engine.bind_checkpoint(second)
    assert engine.checkpoint_id == second.checkpoint_id
    assert engine.tt_info()["occupied_entries"] == 0


def test_f56_generated_semantic_rules_execute_v3_binding_and_learning_update():
    import sys
    sys.path.insert(0, "tests")
    from phase19c1_native_semantic_fixtures import semantic_corpus

    compiled = dict(semantic_corpus())["weird_0"]
    native = compile_native_semantic_rules(compiled)
    legacy = compiled._legacy_compiled
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled, profile,
        dynamic_weights={"mobility": 2.0, "promotion_potential": 3.0, "anchor_safety": 5.0},
        training_seed=5600000,
    )
    checkpoint = _v3_checkpoint(parent, tuple(native.type_ids))
    session = GameSession(compiled)
    packed = pack_semantic_search_position(compiled, native, session)
    assert len(native_spatial_features(native, packed)["occupancy"]) == 2 * len(native.type_ids) * 9
    result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=0).search(
        session, __import__("generic_chess.ai.limits", fromlist=["SearchLimits"]).SearchLimits(
            max_depth=1, max_nodes=100, quiescence_max_depth=0
        )
    )
    assert result.action is not None
    type_ids = tuple(sorted(parent.board_weights))
    material = material_features(session.state.position, type_ids, perspective=0)
    point = TrainingPoint(
        ply=0,
        root_position_key="generated-root",
        action=None,
        exploration=False,
        pv=(),
        leaf_position_key="generated-leaf",
        leaf_feature_board=material.board_counts,
        leaf_feature_hand=material.hand_counts,
        leaf_value=0.0,
        completed_depth=1,
        leaf_feature_dynamic=native_dynamic_features(native, packed),
    )
    trajectory = TrainingTrajectory(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        generation=0,
        game_seed=5600002,
        initial_position_key="generated-root",
        actions=(),
        search_nodes=1,
        search_max_depth=1,
        points=(point,),
        terminal="draw",
        winner=None,
        type_ids=type_ids,
    )
    update = tdleaf_update([trajectory], checkpoint, TDLeafConfig(alpha=0.1))
    assert update.positions_seen == 1
    assert update.spatial_occupancy_weights == checkpoint.spatial_occupancy_weights
    assert update.localized_control_weights == checkpoint.localized_control_weights
