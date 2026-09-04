from dataclasses import replace

import numpy as np
import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.nonlinear import (
    CompactNonlinearResidual,
    bounded_value_domain,
    fit_compact_residual,
    semantic_state_features,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import evaluate as native_evaluate
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


def test_f58_tanh_residual_learns_nonlinear_xor_and_roundtrips():
    features = np.asarray([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]] * 8)
    targets = np.asarray([-1.0, 1.0, 1.0, -1.0] * 8)
    model = fit_compact_residual(features, targets, width=16, regularization=1e-4, seed=5801, epochs=900)
    prediction = model.predict(features)
    assert np.mean((prediction - targets) ** 2) < 0.08
    assert np.allclose(CompactNonlinearResidual.from_dict(model.to_dict()).predict(features), prediction)


def test_f58_rejects_noncompact_width():
    with pytest.raises(ValueError, match="width must be 16 or 32"):
        fit_compact_residual(np.zeros((4, 2)), np.zeros(4), width=64, regularization=0.0, seed=1)


def test_f58_bounded_domain_uses_value_scale_not_native_fixed_point_scale():
    values = bounded_value_domain(np.asarray([0.0, 4.0, 8.0]), 4.0)
    assert np.allclose(values, [0.0, np.tanh(1.0), np.tanh(2.0)])
    assert not np.isclose(values[1], np.tanh(4.0 / 256.0))


def test_f58_state_encoding_has_fixed_aux_width_and_base_hand_axis():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    initial = GameSession(compiled).state.position
    base_type = next(
        piece_type for piece_type in compiled._legacy_compiled.piece_types
        if piece_type.promotion_target_ids
    )
    promoted_type = base_type.promotion_target_ids[0]
    board = list(initial.board)
    empty_square = next(index for index, piece in enumerate(board) if piece is None)
    board[empty_square] = Piece(0, base_type.type_id, promoted_type, True)
    promoted = replace(
        initial,
        board=tuple(board),
        hands=(Hands(((base_type.type_id, 1),)), Hands.empty()),
    )
    initial_features = semantic_state_features(initial, compiled, (0, 0, 0))
    promoted_features = semantic_state_features(promoted, compiled, (0, 0, 0))
    assert len(promoted_features) == len(initial_features)
    current_ids = tuple(sorted(compiled.support.type_metadata))
    base_ids = tuple(sorted(piece_type.type_id for piece_type in compiled._legacy_compiled.piece_types))
    hand_offset = 2 * len(current_ids) * len(initial.board)
    assert promoted_features[hand_offset + base_ids.index(base_type.type_id)] == 1.0


def _native_constant_compact_model(compiled, session):
    features = semantic_state_features(session.state.position, compiled, (0, 0, 0))
    current_ids = tuple(sorted(compiled.support.type_metadata))
    base_ids = tuple(sorted(piece_type.type_id for piece_type in compiled._legacy_compiled.piece_types))
    hand_type_indices = [current_ids.index(type_id) for type_id in base_ids]
    dimension = len(features)
    return {
        "input_mean": [0.0] * dimension,
        "input_scale": [1.0] * dimension,
        "hidden_weights": [[0.0] * dimension for _ in range(16)],
        "hidden_bias": [0.0] * 16,
        "output_weights": [0.0] * 16,
        "output_bias": 2.0,
        "target_scale": 1.0,
        "width": 16,
        "regularization": 0.001,
        "seed": 58011,
        "hand_type_indices": hand_type_indices,
    }


def test_f58_native_compact_profile_matches_constant_model_and_releases_temporaries():
    pytest.importorskip("generic_chess._native_core")
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(compiled)
    session = GameSession(compiled)
    packed = pack_semantic_search_position(compiled, native, session)
    model = _native_constant_compact_model(compiled, session)

    # Repeated direct parses exercise the temporary heap model's success/free path.
    for _ in range(32):
        assert native_evaluate(native, packed, compact_values=model, evaluator_scale=256) == 512

    # Engine construction validates and frees a temporary parse, while search
    # reparses the retained Python payload and exercises its cleanup path too.
    for _ in range(8):
        engine = SemanticSearchEngine(compiled, native, compact_values=model, tt_megabytes=0)
        result = engine.search(
            session,
            __import__("generic_chess.ai.limits", fromlist=["SearchLimits"]).SearchLimits(
                max_depth=1, max_nodes=32, quiescence_max_depth=0
            ),
        )
        assert result.score >= 0


def test_f58_checkpoint_roundtrip_binds_compact_model_and_rebinds_tt():
    pytest.importorskip("generic_chess._native_core")
    ruleset = build_western_chess_ruleset()
    compiled = compile_semantic_ruleset(ruleset)
    native = compile_native_semantic_rules(compiled)
    profile = build_ruleset_profile(compile_ruleset_for_execution(ruleset), EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled,
        profile,
        dynamic_weights={"mobility": 2.0, "promotion_potential": 3.0, "anchor_safety": 5.0},
        training_seed=5800000,
    )
    model = _native_constant_compact_model(compiled, GameSession(compiled))
    child = parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        compact_nonlinear=model,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="f58-test",
        training_seed=5800001,
    )
    assert child.evaluator_version == "learnable-generic-v4"
    assert LearnableMaterialCheckpoint.from_dict(child.to_dict()).checkpoint_id == child.checkpoint_id
    engine = SemanticSearchEngine(compiled, native, checkpoint=child, tt_megabytes=1)
    result = engine.search(
        GameSession(compiled),
        SearchLimits(max_depth=1, max_nodes=32, quiescence_max_depth=0),
    )
    assert result.action is not None
    assert engine.tt_info()["occupied_entries"] > 0
    changed_model = dict(model)
    changed_model["output_bias"] = 3.0
    changed = child.child_checkpoint(
        board_weights=child.board_weights,
        hand_weights=child.hand_weights,
        dynamic_weights=child.dynamic_weights,
        compact_nonlinear=changed_model,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="f58-test-rebind",
        training_seed=5800002,
    )
    engine.bind_checkpoint(changed)
    assert engine.checkpoint_id == changed.checkpoint_id
    assert engine.tt_info()["occupied_entries"] == 0
