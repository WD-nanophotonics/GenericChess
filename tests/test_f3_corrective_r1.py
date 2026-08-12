"""F3 Corrective R1 closure corpus and runtime-cost tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movegen import legal_actions
from generic_chess.core.search_runtime import (
    RuntimeCountsSnapshot,
    RuntimeHistoryContext,
    RuntimeHash,
    RuntimePositionIdentity,
    SearchPathRuntime,
)
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks


def _semantic_shogi():
    from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset

    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    return SearchSemanticCompiled(
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )


def _evaluator(compiled):
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    config = EvaluationConfig()
    return Evaluator(legacy, build_ruleset_profile(legacy, config), config)


def _session_with_seed(compiled, plies: int, seed: int) -> GameSession:
    session = GameSession(compiled)
    for ply in range(plies):
        actions = sorted(session.legal_actions(), key=str)
        if not actions or session.result.status.value != "ongoing":
            break
        session.submit(actions[(seed + 3 * ply) % len(actions)])
    return session


def _session_from_texts(compiled, texts: tuple[str, ...]) -> GameSession:
    session = GameSession(compiled)
    for text in texts:
        action = next(action for action in session.legal_actions() if str(action) == text)
        session.submit(action)
    return session


def _run(session, compiled, use_tt: bool, depth: int):
    stats = SearchStatistics()
    result = run_root_search(
        session.state,
        compiled,
        _evaluator(compiled),
        TranspositionTable(),
        SearchLimits(max_depth=depth, max_nodes=800, quiescence_max_depth=0),
        None,
        stats,
        use_tt=use_tt,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
        _history_witnesses=session._search_witnesses,
    )
    return result, stats


def _assert_pv_legal(session, compiled, pv):
    state = session.state
    for action in pv:
        assert action in legal_actions(state, compiled)
        state = apply_action(state, action, compiled)


def _assert_search_parity(session, compiled, depth: int):
    off, off_stats = _run(session, compiled, False, depth)
    on, on_stats = _run(session, compiled, True, depth)
    assert off == on
    root_actions = {str(action) for action in legal_actions(session.state, compiled)}
    assert off[0] is None or str(off[0]) in root_actions
    assert on[0] is None or str(on[0]) in root_actions
    assert off_stats.completed_depth == on_stats.completed_depth
    assert off_stats.runtime_depth_balanced and on_stats.runtime_depth_balanced
    assert off_stats.runtime_pushes == off_stats.runtime_pops
    assert on_stats.runtime_pushes == on_stats.runtime_pops
    _assert_pv_legal(session, compiled, off[2])
    _assert_pv_legal(session, compiled, on[2])


def test_f3_persistent_player_tt_survives_successive_session_moves():
    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    session = GameSession(compiled)
    player_on = AlphaBetaPlayer(
        compiled,
        use_tt=True,
        use_ordering=False,
        use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    player_off = AlphaBetaPlayer(
        compiled,
        use_tt=False,
        use_ordering=False,
        use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    limits = SearchLimits(max_depth=2, max_nodes=800, quiescence_max_depth=0)

    old_key = SearchPathRuntime.from_state(
        session.state, compiled, history_witnesses=session._search_witnesses
    ).search_key()
    first_on = player_on.choose_action(session, limits)
    first_off = player_off.choose_action(session, limits)
    assert (first_on.action, first_on.score) == (first_off.action, first_off.score)
    assert first_on.action in session.legal_actions()
    assert len(player_on._tt) > 0
    assert player_on._tt.generation == 1

    session.submit(first_on.action)
    new_key = SearchPathRuntime.from_state(
        session.state, compiled, history_witnesses=session._search_witnesses
    ).search_key()
    assert old_key != new_key
    assert old_key.history_context != new_key.history_context
    prior_entries = tuple(player_on._tt._data)

    second_on = player_on.choose_action(session, limits)
    second_off = player_off.choose_action(session, limits)
    assert (second_on.action, second_on.score) == (second_off.action, second_off.score)
    assert second_on.action in session.legal_actions()
    assert player_on._tt.generation == 2
    assert second_on.tt_probes > 0
    assert second_on.tt_hits > 0
    same_state_entries = [
        entry_key
        for entry_key in prior_entries
        if entry_key.position_key == new_key.position_key
        and entry_key.runtime_hash == new_key.runtime_hash
        and entry_key.ply_count == new_key.ply_count
    ]
    assert same_state_entries
    assert all(entry_key.history_context == new_key.history_context for entry_key in same_state_entries)


def test_f3_multi_prefix_generic_draw_policy_differential():
    compiled = build_4x4_rooks()
    for seed, plies in ((0, 0), (1, 1), (2, 2), (3, 3)):
        session = _session_with_seed(compiled, plies, seed)
        _assert_search_parity(session, compiled, depth=2)


def test_f3_multi_prefix_continuous_check_differential():
    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    paths = (
        (),
        ("a1-a2", "b3-b2", "a2-a1", "b2-b3"),
        (
            "a1-a2", "b3-b2", "a2-a1", "b2-b3",
            "c2-c3", "b3-b2", "c3-c2",
        ),
        (
            "c2-c3", "b3-b2", "c3-c2", "b2-b3",
            "a1-a2", "b3-b2", "a2-a1",
        ),
    )
    for texts in paths:
        session = _session_from_texts(compiled, texts)
        for depth in (1, 2, 3):
            _assert_search_parity(session, compiled, depth)


def test_f3_bounded_semantic_standard_shogi_differential():
    compiled = _semantic_shogi()
    for seed, plies in ((0, 0), (1, 1), (2, 2), (3, 3)):
        session = _session_with_seed(compiled, plies, seed)
        _assert_search_parity(session, compiled, depth=1)


def test_f3_opaque_custom_root_skips_tt_instead_of_conflating_history():
    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    session = _session_with_seed(compiled, 3, 1)
    opaque = replace(session.state, history=())
    stats = SearchStatistics()
    run_root_search(
        opaque,
        compiled,
        _evaluator(compiled),
        TranspositionTable(),
        SearchLimits(max_depth=2, max_nodes=800, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    assert stats.tt_skipped_ineligible_nodes > 0
    assert stats.tt_probes == 0
    assert stats.tt_stores == 0


def test_f3_ordinary_repetition_tt_parity():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    for ply in (0, 3, 7):
        session = _session_at_ply(compiled, ply)
        _assert_search_parity(session, compiled, depth=2)


def test_f3_independent_equal_contexts_produce_equal_keys():
    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    session = _session_from_texts(
        compiled, ("a1-a2", "b3-b2", "a2-a1", "b2-b3")
    )
    left = SearchPathRuntime.from_state(
        session.state, compiled, history_witnesses=session._search_witnesses
    )
    right = SearchPathRuntime.from_state(
        session.state, compiled, history_witnesses=session._search_witnesses
    )
    assert left._history_context is not right._history_context
    assert left._history_context == right._history_context
    assert left.search_key() == right.search_key()


def test_f3_exception_and_sibling_rollback_restore_history_context(monkeypatch):
    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    runtime = SearchPathRuntime.from_state(GameSession(compiled).state, compiled)
    root_context = runtime._history_context
    actions = sorted(runtime.legal_actions(), key=str)

    with runtime.pushed(actions[0]):
        assert runtime._history_context is not root_context
    assert runtime._history_context is root_context

    monkeypatch.setattr(
        "generic_chess.core.search_runtime.terminal_from_search_runtime",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("r1 rollback")),
    )
    with pytest.raises(RuntimeError, match="r1 rollback"):
        runtime.push(actions[0])
    assert runtime._history_context is root_context
    runtime.assert_balanced()


def test_f3_runtime_hash_collision_keeps_snapshot_exact_guard():
    compiled = build_4x4_rooks()
    runtime = SearchPathRuntime.from_state(GameSession(compiled).state, compiled)
    root_identity = RuntimePositionIdentity(runtime.position)
    action = sorted(runtime.legal_actions(), key=str)[0]
    with runtime.pushed(action):
        child_identity = RuntimePositionIdentity(runtime.position)
    forced = RuntimeHash(0, 0)
    left = RuntimeCountsSnapshot.from_counts(
        {root_identity: 1}, fast_hashes={root_identity: forced}
    )
    right = RuntimeCountsSnapshot.from_counts(
        {child_identity: 1}, fast_hashes={child_identity: forced}
    )
    assert left.digest == right.digest
    assert left != right


def test_f3_pvs_aspiration_research_restores_parent_history_context(monkeypatch):
    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    session = _session_from_texts(
        compiled, ("a1-a2", "b3-b2", "a2-a1", "b2-b3")
    )
    restored = []
    original_pop = SearchPathRuntime.pop

    def pop(runtime):
        parent_context = runtime._frames[-1].history_context
        result = original_pop(runtime)
        restored.append(runtime._history_context is parent_context)
        return result

    monkeypatch.setattr(SearchPathRuntime, "pop", pop)
    stats = SearchStatistics()
    run_root_search(
        session.state,
        compiled,
        _evaluator(compiled),
        TranspositionTable(),
        SearchLimits(max_depth=3, max_nodes=1200, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=False,
        tuning=SearchTuning(
            use_pvs=True,
            use_aspiration=True,
            aspiration_start_depth=2,
            use_root_tactical=False,
        ),
        _history_witnesses=session._search_witnesses,
    )
    assert restored
    assert all(restored)
    assert stats.runtime_depth_balanced


def test_f3_qsearch_does_not_probe_tt():
    from generic_chess.ai.alphabeta import search as search_module

    compiled = build_4x4_rooks()
    runtime = SearchPathRuntime.from_state(GameSession(compiled).state, compiled)
    stats = SearchStatistics()
    limits = SearchLimits(max_depth=1, quiescence_max_depth=1)
    budget = search_module._Budget(limits, None)
    ctx = search_module._Context(
        compiled,
        _evaluator(compiled),
        TranspositionTable(),
        stats,
        budget,
        SearchTuning(use_root_tactical=False),
        True,
        False,
        1,
        2,
        None,
        runtime=runtime,
    )
    search_module.quiescence(runtime.state, -search_module.INF, search_module.INF, 0, 0, ctx)
    assert stats.qnodes > 0
    assert stats.tt_probes == 0
    runtime.assert_balanced()


def test_f3_runtime_cost_counters_separate_snapshot_context_and_key_work():
    compiled = build_4x4_rooks()
    stats = SearchStatistics()
    run_root_search(
        GameSession(compiled).state,
        compiled,
        _evaluator(compiled),
        TranspositionTable(),
        SearchLimits(max_depth=2, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    assert stats.runtime_snapshot_updates == stats.runtime_pushes
    assert stats.runtime_snapshot_entry_digest_calls >= stats.runtime_snapshot_updates
    assert stats.runtime_history_context_updates == stats.runtime_pushes
    assert stats.runtime_search_key_calls > 0
    assert stats.runtime_child_external_key_computations == 0
