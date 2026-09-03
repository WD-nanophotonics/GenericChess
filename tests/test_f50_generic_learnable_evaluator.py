"""F50 generic dynamic evaluator contracts."""

from dataclasses import replace

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.features import DYNAMIC_FEATURE_NAMES
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    dynamic_features,
    guarded_actions,
    make_checked,
    pack_position,
    semantic_iterative_search,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


pytestmark = pytest.mark.skipif(not native_available(), reason="native extension unavailable")


def _initial():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(compiled)
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id], ids[piece.current_type_id],
            piece.owner, int(piece.promoted),
        ]
        for row in compiled.support.initial_position
        for piece in row
    ]
    position = pack_position(native, {
        "side": 0, "ply": 0, "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)], "aux_state": (),
    })
    return compiled, native, position


def _initial_for(compiled, native):
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id], ids[piece.current_type_id],
            piece.owner, int(piece.promoted),
        ]
        for row in compiled.support.initial_position
        for piece in row
    ]
    return pack_position(native, {
        "side": 0, "ply": 0, "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)], "aux_state": (),
    })


def test_dynamic_feature_vector_is_fixed_and_native_leaf_scoring_agrees():
    _compiled, native, position = _initial()
    assert DYNAMIC_FEATURE_NAMES == ("mobility", "promotion_potential", "anchor_safety")
    action = guarded_actions(native, position)[0]
    child = make_checked(native, position, action)
    features = dynamic_features(native, child)
    weights = (2, 3, 5)
    zero = (0,) * len(native.type_ids)
    result = semantic_iterative_search(
        native,
        position,
        1,
        max_nodes=100000,
        board_values=zero,
        hand_values=zero,
        dynamic_values=weights,
    )
    assert result["completed_depth"] == 1
    selected_child = make_checked(native, position, result["best_action"])
    selected_features = dynamic_features(native, selected_child)
    assert result["score"] == sum(w * f for w, f in zip(weights, selected_features))
    assert all(isinstance(value, int) for value in features)


def test_v1_checkpoint_roundtrip_remains_material_only_and_v2_seeds_from_config():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    legacy = compile_ruleset_for_execution(build_western_chess_ruleset())
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    v1 = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    assert "dynamic_weights" not in v1.to_dict()
    assert LearnableMaterialCheckpoint.from_dict(v1.to_dict()).checkpoint_id == v1.checkpoint_id
    config = EvaluationConfig()
    v2 = LearnableMaterialCheckpoint.from_profile(
        compiled,
        profile,
        dynamic_weights={
            "mobility": config.dynamic_mobility_weight,
            "promotion_potential": config.promotion_potential_weight,
            "anchor_safety": config.anchor_escape_weight,
        },
    )
    assert tuple(v2.dynamic_weights) == DYNAMIC_FEATURE_NAMES
    assert v2.evaluator_version == "learnable-generic-v2"
    assert LearnableMaterialCheckpoint.from_dict(v2.to_dict()).checkpoint_id == v2.checkpoint_id


def test_dynamic_checkpoint_rebind_clears_persistent_tt():
    compiled, native, _position = _initial()
    legacy = compile_ruleset_for_execution(build_western_chess_ruleset())
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, dynamic_weights={"mobility": 2, "promotion_potential": 3, "anchor_safety": 5}
    )
    child = replace(parent, dynamic_weights={"mobility": 4, "promotion_potential": 3, "anchor_safety": 5})
    engine = SemanticSearchEngine(compiled, native, checkpoint=parent, tt_megabytes=1)
    engine.search(GameSession(compiled), SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0))
    assert engine.tt_info()["occupied_entries"] > 0
    engine.bind_checkpoint(child)
    assert engine.tt_info()["occupied_entries"] == 0


@pytest.mark.parametrize("corpus_name", ["weird_0", "weird_1"])
def test_native_leaf_dynamic_definition_is_generic_across_generated_semantic_rulesets(corpus_name):
    import sys
    sys.path.insert(0, "tests")
    from phase19c1_native_semantic_fixtures import semantic_corpus

    compiled = dict(semantic_corpus())[corpus_name]
    native = compile_native_semantic_rules(compiled)
    position = _initial_for(compiled, native)
    result = SemanticSearchEngine(
        compiled,
        native,
        board_values=(0,) * len(native.type_ids),
        hand_values=(0,) * len(native.type_ids),
        dynamic_values=(2, 3, 5),
        tt_megabytes=0,
    ).search(GameSession(compiled), SearchLimits(max_depth=1, max_nodes=1000, quiescence_max_depth=0))
    assert result.action is not None
    assert len(result.dynamic_features) == 3
    assert result.score == sum(weight * value for weight, value in zip((2, 3, 5), result.dynamic_features))


def test_native_leaf_dynamic_definition_is_generic_on_standard_shogi():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native = compile_native_semantic_rules(compiled)
    result = SemanticSearchEngine(
        compiled,
        native,
        board_values=(0,) * len(native.type_ids),
        hand_values=(0,) * len(native.type_ids),
        dynamic_values=(2, 3, 5),
        tt_megabytes=0,
    ).search(GameSession(compiled), SearchLimits(max_depth=1, max_nodes=1000, quiescence_max_depth=0))
    assert result.action is not None
    assert result.dynamic_features == tuple(result.dynamic_features)
    assert result.score == sum(weight * value for weight, value in zip((2, 3, 5), result.dynamic_features))
