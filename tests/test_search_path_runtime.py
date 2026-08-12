"""F2 Core search-path runtime contract tests."""

from __future__ import annotations

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.identity import RuntimeHash
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks


def test_runtime_push_pop_matches_immutable_successors():
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    expected = dict(legal_successors(root, compiled))
    runtime = SearchPathRuntime.from_state(root, compiled)
    assert set(runtime.legal_actions()) == set(expected)
    for action in runtime.legal_actions():
        with runtime.pushed(action):
            child = expected[action]
            assert runtime.position == child.position
            assert runtime.ply_count == child.ply_count
            assert runtime.terminal_status == child.terminal_status
    runtime.assert_balanced()
    assert runtime.position == root.position
    assert runtime.repetition_counts == dict(root.repetition_counts)


def test_runtime_forced_hash_collision_uses_exact_guard():
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    runtime = SearchPathRuntime.from_state(root, compiled, hash_override=RuntimeHash(0, 0))
    with runtime.pushed(runtime.legal_actions()[0]):
        assert runtime.runtime_hash == RuntimeHash(0, 0)
        assert runtime.collision_checks == 1
        assert runtime.collision_fallbacks == 1
    runtime.assert_balanced()


def test_runtime_rejects_malformed_imported_history():
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    from dataclasses import replace
    from generic_chess.core.position import HistoryRecord

    malformed = replace(
        root,
        history=(HistoryRecord("wrong", -1, "", False),),
    )
    with pytest.raises(ValueError, match="malformed imported history"):
        SearchPathRuntime.from_state(malformed, compiled)


def test_runtime_search_closes_depth_and_tuple_copy_counters():
    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    stats = SearchStatistics()
    run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=3, quiescence_max_depth=1),
        None,
        stats,
        use_tt=True,
        use_ordering=True,
        tuning=SearchTuning(use_root_tactical=False),
    )
    assert stats.runtime_root_imports == 1
    assert stats.runtime_pushes == stats.runtime_pops
    assert stats.runtime_depth_balanced
    assert stats.runtime_hash_updates == stats.runtime_pushes
    assert stats.runtime_repetition_tuple_copies == 0
    assert stats.runtime_history_tuple_copies == 0
