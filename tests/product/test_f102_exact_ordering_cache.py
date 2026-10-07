"""F102 exact learned-ordering cache and cost-reduction contracts."""

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import evaluate
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


pytestmark = pytest.mark.skipif(
    not native_available(), reason="native extension unavailable"
)


def _fixture():
    ruleset = build_western_chess_ruleset()
    compiled = compile_semantic_ruleset(ruleset)
    native = compile_native_semantic_rules(compiled)
    legacy = compile_ruleset_for_execution(ruleset)
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    ordering = parent.child_checkpoint(
        board_weights={key: -value for key, value in parent.board_weights.items()},
        hand_weights={key: -value for key, value in parent.hand_weights.items()},
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="f102-ordering-cache",
        training_seed=102,
    )
    return compiled, native, parent, ordering


def _limits(**kwargs):
    return SearchLimits(quiescence_max_depth=0, **kwargs)


def test_cache_enabled_and_disabled_are_search_exact_and_warm_hits_are_reported():
    compiled, native, parent, ordering = _fixture()
    enabled = SemanticSearchEngine(
        compiled,
        native,
        checkpoint=parent,
        ordering_checkpoint=ordering,
        tt_megabytes=0,
        ordering_cache_enabled=True,
    )
    disabled = SemanticSearchEngine(
        compiled,
        native,
        checkpoint=parent,
        ordering_checkpoint=ordering,
        tt_megabytes=0,
        ordering_cache_enabled=False,
    )
    enabled_result = enabled.search(
        GameSession(compiled), _limits(max_depth=4, max_nodes=3000),
        root_window_pruning=False,
    )
    disabled_result = disabled.search(
        GameSession(compiled), _limits(max_depth=4, max_nodes=3000),
        root_window_pruning=False,
    )
    assert (enabled_result.action, enabled_result.score, enabled_result.principal_variation) == (
        disabled_result.action,
        disabled_result.score,
        disabled_result.principal_variation,
    )
    assert enabled_result.ordering_cache_capacity > 0
    assert enabled_result.ordering_cache_entry_bytes > 0
    assert enabled_result.ordering_cache_misses > 0
    assert enabled_result.ordering_cache_hits > 0
    assert enabled_result.ordering_cache_hit_rate == pytest.approx(
        enabled_result.ordering_cache_hits /
        (enabled_result.ordering_cache_hits + enabled_result.ordering_cache_misses)
    )
    assert disabled_result.ordering_cache_capacity == 0
    assert disabled_result.ordering_cache_hits == 0
    assert disabled_result.ordering_cache_misses == 0


def test_frozen_reachable_position_parity_and_leaf_bindings():
    compiled, native, parent, ordering = _fixture()
    enabled = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        tt_megabytes=0, ordering_cache_enabled=True,
    )
    disabled = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        tt_megabytes=0, ordering_cache_enabled=False,
    )
    reference_session = GameSession(compiled)
    optimized_session = GameSession(compiled)
    limits = _limits(max_depth=2, max_nodes=128)
    for index in range(100):
        reference = disabled.search(
            reference_session, limits, root_window_pruning=False,
        )
        optimized = enabled.search(
            optimized_session, limits, root_window_pruning=False,
        )
        assert (optimized.action, optimized.score, optimized.principal_variation,
                optimized.completed_depth, optimized.nodes) == (
            reference.action,
            reference.score,
            reference.principal_variation,
            reference.completed_depth,
            reference.nodes,
        ), index
        packed = pack_semantic_search_position(
            compiled, native, optimized_session,
        )
        assert evaluate(
            native,
            packed,
            board_values=parent.semantic_quantized_board(native.type_ids),
            hand_values=parent.semantic_quantized_hand(native.type_ids),
            dynamic_values=parent.semantic_quantized_dynamic(),
            spatial_occupancy_values=parent.semantic_quantized_spatial(native.type_ids),
            localized_control_values=parent.semantic_quantized_localized_control(),
            compact_values=parent.compact_nonlinear or None,
            evaluator_scale=parent.semantic_native_scale,
        ) == evaluate(
            native,
            packed,
            board_values=parent.semantic_quantized_board(native.type_ids),
            hand_values=parent.semantic_quantized_hand(native.type_ids),
            dynamic_values=parent.semantic_quantized_dynamic(),
            spatial_occupancy_values=parent.semantic_quantized_spatial(native.type_ids),
            localized_control_values=parent.semantic_quantized_localized_control(),
            compact_values=parent.compact_nonlinear or None,
            evaluator_scale=parent.semantic_native_scale,
        )
        legal = reference_session.legal_actions()
        if not legal:
            break
        action = legal[(index * 17 + 3) % len(legal)]
        reference_session.submit(action)
        optimized_session.submit(action)
