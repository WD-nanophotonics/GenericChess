"""F105 selective shallow learned-ordering contracts."""

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
        training_config_hash="f105-shallow-ordering", training_seed=105,
    )
    return compiled, native, parent, ordering


def _search(engine, compiled, *, max_depth=4):
    return engine.search(
        GameSession(compiled),
        SearchLimits(max_depth=max_depth, max_nodes=3000, quiescence_max_depth=0),
        root_window_pruning=False,
    )


def test_bound_one_preserves_exact_result_and_exposes_only_shallow_ordering():
    compiled, native, parent, ordering = _fixture()
    bounded = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        ordering_max_ply=1, tt_megabytes=0,
    )
    unbounded = SemanticSearchEngine(
        compiled, native, checkpoint=parent, ordering_checkpoint=ordering,
        ordering_max_ply=-1, tt_megabytes=0,
    )
    bounded_result = _search(bounded, compiled)
    unbounded_result = _search(unbounded, compiled)
    assert bounded_result.ordering_max_ply == 1
    assert unbounded_result.ordering_max_ply == -1
    assert (bounded_result.action, bounded_result.score, bounded_result.principal_variation) == (
        unbounded_result.action, unbounded_result.score, unbounded_result.principal_variation,
    )
    assert bounded_result.ordering_evaluations_by_ply[0] > 0
    assert bounded_result.ordering_evaluations_by_ply[1] > 0
    assert all(value == 0 for value in bounded_result.ordering_evaluations_by_ply[2:])
    assert all(value == 0 for value in bounded_result.ordering_nodes_by_ply[2:])
    assert all(value == 0 for value in bounded_result.ordering_actions_by_ply[2:])
    assert all(value == 0 for value in bounded_result.ordering_elapsed_nanoseconds_by_ply[2:])


def test_ordering_bound_is_part_of_arena_configuration_and_validated():
    assert ArenaConfig(ordering_max_ply=1).ordering_max_ply == 1
    with pytest.raises(ValueError):
        ArenaConfig(ordering_max_ply=-2)
    with pytest.raises(ValueError):
        ArenaConfig(ordering_max_ply=True)
