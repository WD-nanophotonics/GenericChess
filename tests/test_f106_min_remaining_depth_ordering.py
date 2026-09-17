"""F106 remaining-depth learned-ordering contracts."""

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.arena import ArenaConfig
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules
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
        games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1,
        training_config_hash="f106-min-depth", training_seed=106,
    )
    return compiled, native, parent, ordering


def _search(engine, compiled):
    return engine.search(
        GameSession(compiled),
        SearchLimits(max_depth=4, max_nodes=3000, quiescence_max_depth=0),
        root_window_pruning=False,
    )


def test_min_depth_two_skips_only_remaining_depth_one_and_keeps_exact_result():
    compiled, native, parent, ordering = _fixture()
    historical = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        ordering_min_depth=1, tt_megabytes=0,
    )
    candidate = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        ordering_min_depth=2, tt_megabytes=0,
    )
    historical_result = _search(historical, compiled)
    candidate_result = _search(candidate, compiled)
    assert historical_result.ordering_min_depth == 1
    assert candidate_result.ordering_min_depth == 2
    assert (candidate_result.action, candidate_result.score) == (
        historical_result.action, historical_result.score,
    )
    assert candidate_result.ordering_skipped_by_remaining_depth[1] > 0
    assert sum(candidate_result.ordering_skipped_by_remaining_depth[2:]) == 0
    assert sum(candidate_result.ordering_evaluations_by_ply) > 0


def test_min_depth_two_cache_parity_and_arena_identity_validation():
    compiled, native, parent, ordering = _fixture()
    enabled = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        ordering_min_depth=2, ordering_cache_enabled=True, tt_megabytes=0,
    )
    disabled = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        ordering_min_depth=2, ordering_cache_enabled=False, tt_megabytes=0,
    )
    a = _search(enabled, compiled)
    b = _search(disabled, compiled)
    assert (a.action, a.score, a.principal_variation) == (
        b.action, b.score, b.principal_variation,
    )
    assert ArenaConfig(ordering_min_depth=2).ordering_min_depth == 2
    with pytest.raises(ValueError):
        ArenaConfig(ordering_min_depth=0)
    with pytest.raises(ValueError):
        ArenaConfig(ordering_min_depth=True)
