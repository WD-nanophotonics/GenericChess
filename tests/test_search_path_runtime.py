"""F2 Core search-path runtime contract tests."""

from __future__ import annotations

from dataclasses import replace

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
from generic_chess.core.search_runtime import (
    RuntimeCountsSnapshot,
    RuntimeHistoryContext,
    SearchPathRuntime,
    _full_runtime_hash,
)
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.movement import LeapAtom, RayAtom

from ai_fixtures import build_4x4_rooks
from conftest import king_type, make_compiled, make_state, sq, T


def _continuous_history_pair():
    """Two legal routes with equal position/count state and different check evidence."""
    from dataclasses import replace

    from ai_fixtures import build_4x4_rooks

    compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
    paths = (
        (
            "a1-a2", "b3-b2", "a2-a1", "b2-b3",
            "c2-c3", "b3-b2", "c3-c2",
        ),
        (
            "c2-c3", "b3-b2", "c3-c2", "b2-b3",
            "a1-a2", "b3-b2", "a2-a1",
        ),
    )
    states = []
    state = __import__("generic_chess.core.transition", fromlist=["initial_state"]).initial_state(compiled)
    from generic_chess.core.transition import apply_action, legal_successors

    for path in paths:
        current = state
        for text in path:
            action = next(
                action
                for action, _child in legal_successors(current, compiled)
                if str(action) == text
            )
            current = apply_action(current, action, compiled)
        states.append(current)
    return compiled, tuple(states), paths


def test_legacy_child_pushes_use_zero_external_keys_and_incremental_oracle():
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    runtime = SearchPathRuntime.from_state(root, compiled)
    root_hash = runtime.runtime_hash
    for action in runtime.legal_actions():
        with runtime.pushed(action):
            assert runtime.child_external_key_computations == 0
            assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
            if runtime.legal_actions():
                with runtime.pushed(runtime.legal_actions()[0]):
                    assert runtime.child_external_key_computations == 0
                    assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
    runtime.assert_balanced()
    assert runtime.runtime_hash == root_hash
    assert runtime.legacy_incremental_updates >= 1


def test_semantic_child_push_uses_component_diff_without_external_key():
    from rule_semantics_ir_fixtures import nifu_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.core.transition import initial_state

    compiled = compile_semantic_ruleset(nifu_ruleset())
    runtime = SearchPathRuntime.from_state(initial_state(compiled), compiled)
    action = runtime.legal_actions()[0]
    with runtime.pushed(action):
        assert runtime.child_external_key_computations == 0
        assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
        assert runtime.semantic_full_diff_fallbacks == 1
    runtime.assert_balanced()


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


def test_f2_runtime_key_insufficiency_is_reproduced_by_legal_histories():
    from generic_chess.core.identity import history_adjudication_context

    compiled, (left, right), _paths = _continuous_history_pair()
    left_runtime = SearchPathRuntime.from_state(left, compiled)
    right_runtime = SearchPathRuntime.from_state(right, compiled)

    assert left.position == right.position
    assert left.ply_count == right.ply_count
    assert left.repetition_counts == right.repetition_counts
    assert history_adjudication_context(left, compiled) != history_adjudication_context(right, compiled)

    # This is the accepted F2 key projection: it has no history context.
    left_f2 = (
        compiled.ruleset_fingerprint,
        left_runtime.runtime_hash,
        left_runtime.current_identity,
        left_runtime._snapshot,
        left_runtime.ply_count,
    )
    right_f2 = (
        compiled.ruleset_fingerprint,
        right_runtime.runtime_hash,
        right_runtime.current_identity,
        right_runtime._snapshot,
        right_runtime.ply_count,
    )
    assert left_f2 == right_f2
    assert left_runtime.search_key() != right_runtime.search_key()


def test_history_context_exact_guard_survives_forced_digest_collision(monkeypatch):
    compiled, (left, right), _paths = _continuous_history_pair()
    left_runtime = SearchPathRuntime.from_state(left, compiled)
    right_runtime = SearchPathRuntime.from_state(right, compiled)
    original = RuntimeHistoryContext._record_digest
    monkeypatch.setattr(
        RuntimeHistoryContext,
        "_record_digest",
        staticmethod(lambda *_args: bytes(16)),
    )
    left_context = RuntimeHistoryContext.from_records(left_runtime.history)
    right_context = RuntimeHistoryContext.from_records(right_runtime.history)
    assert left_context.digest == right_context.digest
    assert left_context != right_context
    monkeypatch.setattr(RuntimeHistoryContext, "_record_digest", original)


def test_continuous_check_tt_is_eligible_only_for_exact_history():
    from dataclasses import replace

    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.core.transition import initial_state

    compiled, (complete, _other), _paths = _continuous_history_pair()
    incomplete = replace(complete, history=())
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)

    exact_stats = SearchStatistics()
    run_root_search(
        complete,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=3, quiescence_max_depth=0),
        None,
        exact_stats,
        use_tt=True,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    opaque_stats = SearchStatistics()
    run_root_search(
        incomplete,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=2, quiescence_max_depth=0),
        None,
        opaque_stats,
        use_tt=True,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    assert exact_stats.tt_eligible_nodes > 0
    assert exact_stats.tt_hits > 0
    assert opaque_stats.tt_skipped_ineligible_nodes > 0
    assert opaque_stats.tt_probes == 0


def test_continuous_check_tt_matches_no_tt_on_legal_history_pair():
    compiled, (left, right), _paths = _continuous_history_pair()
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    for state in (left, right):
        results = []
        for use_tt in (False, True):
            stats = SearchStatistics()
            result = run_root_search(
                state,
                compiled,
                evaluator,
                TranspositionTable(),
                SearchLimits(max_depth=3, quiescence_max_depth=0),
                None,
                stats,
                use_tt=use_tt,
                use_ordering=False,
                tuning=SearchTuning(use_root_tactical=False),
            )
            results.append((result, stats))
        (no_tt, _no_stats), (with_tt, tt_stats) = results
        assert with_tt[0] == no_tt[0]
        assert with_tt[1] == no_tt[1]
        assert tt_stats.tt_hits > 0


def test_certified_semantic_shogi_history_aware_tt_reuses_safely():
    from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset

    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    compiled = SearchSemanticCompiled(
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )
    session = GameSession(compiled)
    config = EvaluationConfig()
    evaluator = Evaluator(
        compiled._legacy_compiled,
        build_ruleset_profile(compiled._legacy_compiled, config),
        config,
    )
    results = []
    stats_list = []
    for use_tt in (False, True):
        stats = SearchStatistics()
        result = run_root_search(
            session.state,
            compiled,
            evaluator,
            TranspositionTable(),
            SearchLimits(max_depth=2, quiescence_max_depth=0),
            None,
            stats,
            use_tt=use_tt,
            use_ordering=False,
            tuning=SearchTuning(use_root_tactical=False),
            _history_witnesses=session._search_witnesses,
        )
        results.append(result)
        stats_list.append(stats)
    assert results[1] == results[0]
    assert stats_list[1].tt_eligible_nodes > 0
    assert stats_list[1].tt_hits > 0
    assert stats_list[1].tt_stores > 0


def test_history_aware_tt_does_not_cross_reuse_distinct_legal_histories():
    compiled, (left, right), _paths = _continuous_history_pair()
    left_runtime = SearchPathRuntime.from_state(left, compiled)
    right_runtime = SearchPathRuntime.from_state(right, compiled)
    table = TranspositionTable()
    left_key = left_runtime.search_key()
    right_key = right_runtime.search_key()
    assert left_key != right_key

    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    for state in (left, right):
        run_root_search(
            state,
            compiled,
            evaluator,
            table,
            SearchLimits(max_depth=2, quiescence_max_depth=0),
            None,
            SearchStatistics(),
            use_tt=True,
            use_ordering=False,
            tuning=SearchTuning(use_root_tactical=False),
        )
    assert table.probe(left_key) is not None
    assert table.probe(right_key) is not None


def test_history_aware_tt_pvs_aspiration_parity():
    compiled, (state, _other), _paths = _continuous_history_pair()
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    tuning = SearchTuning(
        use_pvs=True,
        use_aspiration=True,
        aspiration_start_depth=2,
        use_root_tactical=False,
    )
    results = []
    for use_tt in (False, True):
        stats = SearchStatistics()
        results.append(
            run_root_search(
                state,
                compiled,
                evaluator,
                TranspositionTable(),
                SearchLimits(max_depth=4, quiescence_max_depth=0),
                None,
                stats,
                use_tt=use_tt,
                use_ordering=False,
                tuning=tuning,
            )
        )
    assert results[1] == results[0]


def test_pre_root_non_root_repetition_merges_with_runtime_identity():
    """A legal pre-root occurrence must count when the runtime reaches it."""
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 3)
    root = session.state
    target_key = root.history[1].position_key
    assert target_key in dict(root.repetition_counts)

    runtime = SearchPathRuntime.from_state(root, compiled)
    first = session.legal_actions()[0]
    expected_first = legal_successors(root, compiled)[0][1]
    runtime.push(first)
    second = runtime.legal_actions()[0]
    expected_second = legal_successors(expected_first, compiled)[0][1]
    runtime.push(second)

    assert position_identity_key(expected_second.position, compiled) == target_key
    assert dict(expected_second.repetition_counts)[target_key] == 2
    assert runtime.occurrence_count() == 2
    assert len(runtime.history_occurrences(runtime.current_identity)) == 2

    runtime.pop()
    runtime.pop()
    assert runtime.occurrence_count() == 1
    assert runtime.history_occurrences(runtime.current_identity) == [3]
    runtime.assert_balanced()


def test_pre_root_bridge_preserves_exactness_under_forced_runtime_hash_collision():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    root = _session_at_ply(compiled, 3).state
    forced = RuntimeHash(0, 0)
    runtime = SearchPathRuntime.from_state(root, compiled, hash_override=forced)

    runtime.push(runtime.legal_actions()[0])
    runtime.push(runtime.legal_actions()[0])

    assert runtime.occurrence_count() == 2
    assert len(runtime.history_occurrences(runtime.current_identity)) == 2
    assert len(runtime.repetition_counts) == 4
    runtime.pop()
    runtime.pop()
    runtime.assert_balanced()


def test_incomplete_imported_history_uses_conditional_external_key_fallback():
    from dataclasses import replace
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    root = _session_at_ply(compiled, 3).state
    incomplete = replace(root, history=())
    runtime = SearchPathRuntime.from_state(incomplete, compiled)

    runtime.push(runtime.legal_actions()[0])
    runtime.push(runtime.legal_actions()[0])

    assert runtime.occurrence_count() == 2
    assert runtime.opaque_history_child_external_key_computations == 2
    assert not runtime._history_complete
    runtime.pop()
    runtime.pop()
    assert runtime.occurrence_count() == 1
    assert len(runtime._opaque_imported_keys) == 3
    runtime.assert_balanced()


def test_session_supplies_exact_private_history_witnesses():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 3)
    runtime = SearchPathRuntime.from_state(
        session.state,
        compiled,
        history_witnesses=session._search_witnesses,
    )

    assert runtime.history_witness_hits == len(session.state.history)
    assert runtime.history_witness_misses == 0
    assert not runtime._opaque_imported_keys
    runtime.assert_balanced()


def test_unreplayable_custom_history_falls_back_only_when_child_can_match():
    from dataclasses import replace
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    root = _session_at_ply(compiled, 3).state
    records = list(root.history)
    records[1] = replace(records[1], action_signature="{not-replayable}")
    opaque = replace(root, history=tuple(records))
    runtime = SearchPathRuntime.from_state(opaque, compiled)
    assert runtime.history_witness_misses > 0
    assert runtime._history_complete

    runtime.push(runtime.legal_actions()[0])
    runtime.push(runtime.legal_actions()[0])
    assert runtime.occurrence_count() == 2
    runtime.pop()
    runtime.pop()
    assert runtime.occurrence_count() == 1
    runtime.assert_balanced()


def test_complete_history_continuous_check_pre_root_parity():
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_certification import (
        PERPETUAL_CHECK_MOVES,
        PERPETUAL_CHECK_SFEN,
        _seed_history,
    )
    from generic_chess.learning.shogi_rules import sfen_to_gc_state, usi_to_gc_action
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset

    compiled = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    state = _seed_history(
        compiled,
        sfen_to_gc_state(compiled, PERPETUAL_CHECK_SFEN),
    )
    for usi in PERPETUAL_CHECK_MOVES[:4]:
        state = apply_action(state, usi_to_gc_action(compiled, state, usi), compiled)

    runtime = SearchPathRuntime.from_state(state, compiled)
    pushed = 0
    for usi in PERPETUAL_CHECK_MOVES[4:]:
        legacy_action = usi_to_gc_action(compiled, state, usi)
        action = next(
            candidate
            for candidate in runtime.legal_actions()
            if getattr(candidate, "from_square", None) == legacy_action.from_square
            and getattr(candidate, "to_square", None) == legacy_action.to_square
            and getattr(candidate, "promotion_target_id", None)
            == getattr(legacy_action, "promotion_target_id", None)
        )
        runtime.push(action)
        pushed += 1
        state = apply_action(state, legacy_action, compiled)
        assert runtime.position == state.position
        assert runtime.terminal_status == state.terminal_status
        if state.terminal_status.is_terminal:
            break

    assert state.terminal_status.status.name == "PERPETUAL_CHECK"
    assert runtime.terminal_status == state.terminal_status
    assert runtime.opaque_history_child_external_key_computations == 3
    for _ in range(pushed):
        runtime.pop()
    runtime.assert_balanced()


def test_opaque_bridge_exception_rollback_restores_incremental_state(monkeypatch):
    from dataclasses import replace
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    root = _session_at_ply(compiled, 3).state
    runtime = SearchPathRuntime.from_state(replace(root, history=()), compiled)
    runtime.push(runtime.legal_actions()[0])
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.runtime_hash,
        runtime.repetition_counts,
        frozenset(runtime._opaque_imported_keys),
        dict(runtime._history_aliases),
        runtime._snapshot,
    )
    monkeypatch.setattr(
        "generic_chess.core.search_runtime.terminal_from_search_runtime",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected bridge terminal")),
    )
    with pytest.raises(RuntimeError, match="injected bridge terminal"):
        runtime.push(runtime.legal_actions()[0])
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.runtime_hash,
        runtime.repetition_counts,
        frozenset(runtime._opaque_imported_keys),
        dict(runtime._history_aliases),
        runtime._snapshot,
    )
    assert after == before
    runtime.pop()
    runtime.assert_balanced()


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
    malformed = replace(
        root,
        history=(HistoryRecord("wrong", -1, "", False),),
    )
    with pytest.raises(ValueError, match="malformed imported history"):
        SearchPathRuntime.from_state(malformed, compiled)


def test_runtime_rejects_ghost_and_nonpositive_imported_counts():
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    key = position_identity_key(root.position, compiled)
    history = (HistoryRecord(key, -1, "", False),)
    with pytest.raises(ValueError, match="malformed imported"):
        SearchPathRuntime.from_state(replace(root, history=history, repetition_counts=((key, 1), ("ghost", 1))), compiled)
    with pytest.raises(ValueError, match="malformed imported"):
        SearchPathRuntime.from_state(replace(root, history=history, repetition_counts=((key, 0),)), compiled)


def test_forced_hash_collision_keeps_distinct_runtime_occurrences_separate():
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    forced = RuntimeHash(0, 0)
    runtime = SearchPathRuntime.from_state(root, compiled, hash_override=forced)
    root_identity = runtime.current_identity
    first = runtime.legal_actions()[0]
    with runtime.pushed(first):
        child_identity = runtime.current_identity
        assert child_identity != root_identity
        assert runtime.occurrence_count(root_identity, forced) == 1
        assert runtime.occurrence_count(child_identity, forced) == 1
        assert runtime.terminal_status.status.name != "REPETITION"
    runtime.assert_balanced()


def test_snapshot_is_path_order_independent_and_exact_under_digest_collision(monkeypatch):
    left = RuntimeCountsSnapshot.from_counts({"a": 1})
    left = left.updated("b", 2, 0)
    right = RuntimeCountsSnapshot.from_counts({"b": 2})
    right = right.updated("a", 1, 0)
    assert left == right
    assert hash(left) == hash(right)
    original = RuntimeCountsSnapshot._entry_digest
    monkeypatch.setattr(RuntimeCountsSnapshot, "_entry_digest", staticmethod(lambda _key, _count: bytes(16)))
    collision_a = RuntimeCountsSnapshot.from_counts({"a": 1})
    collision_b = RuntimeCountsSnapshot.from_counts({"b": 1})
    assert collision_a != collision_b
    monkeypatch.setattr(RuntimeCountsSnapshot, "_entry_digest", original)


def test_exception_after_child_occurrence_restores_complete_parent_runtime(monkeypatch):
    compiled = build_4x4_rooks()
    root = GameSession(compiled).state
    runtime = SearchPathRuntime.from_state(root, compiled)
    before = (runtime.position, runtime.ply_count, runtime.runtime_hash, tuple(runtime.history), runtime.repetition_counts)
    monkeypatch.setattr("generic_chess.core.search_runtime.terminal_from_search_runtime", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected terminal")))
    with pytest.raises(RuntimeError, match="injected terminal"):
        runtime.push(runtime.legal_actions()[0])
    after = (runtime.position, runtime.ply_count, runtime.runtime_hash, tuple(runtime.history), runtime.repetition_counts)
    assert after == before
    runtime.assert_balanced()


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
    assert stats.runtime_child_external_key_computations == 0
    assert stats.runtime_legacy_incremental_updates == stats.runtime_pushes
    assert stats.runtime_repetition_tuple_copies == 0
    assert stats.runtime_history_tuple_copies == 0


def test_semantic_depth_search_reports_zero_child_external_keys():
    from rule_semantics_ir_fixtures import nifu_ruleset
    from generic_chess.core.transition import initial_state
    from generic_chess.rules.compiler import compile_semantic_ruleset

    compiled = compile_semantic_ruleset(nifu_ruleset())
    state = initial_state(compiled)
    config = EvaluationConfig()
    evaluator = Evaluator(compiled._legacy_compiled, build_ruleset_profile(compiled._legacy_compiled, config), config)
    stats = SearchStatistics()
    run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=2, quiescence_max_depth=0),
        None,
        stats,
        use_tt=False,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    assert stats.runtime_child_external_key_computations == 0
    assert stats.runtime_semantic_full_diff_fallbacks > 0
    assert stats.runtime_pushes == stats.runtime_pops
    assert stats.runtime_depth_balanced


def test_runtime_hash_oracle_covers_capture_promotion_and_drop():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1)))
    rook = T("R", RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1)))
    compiled = make_compiled(8, [king_type(), pawn, gold, rook], auto_drop=True, auto_promotion=True)

    cases = [
        (
            make_state(
                compiled,
                [
                    ".......k",
                    "........",
                    "........",
                    "........",
                    "........",
                    "r.......",
                    "........",
                    "R......K",
                ],
            ),
            BoardMove(sq(0, 0), sq(0, 2)),
        ),
        (
            make_state(
                compiled,
                [
                    ".......k",
                    "....P...",
                    "........",
                    "........",
                    "........",
                    "........",
                    "........",
                    "K.......",
                ],
            ),
            BoardMove(sq(4, 6), sq(4, 7), "G"),
        ),
        (
            make_state(
                compiled,
                [
                    ".......k",
                    "........",
                    "........",
                    "........",
                    "........",
                    "........",
                    "........",
                    "K.......",
                ],
                hands=([("P", 1)], []),
            ),
            DropMove("P", sq(4, 4)),
        ),
    ]
    for state, action in cases:
        runtime = SearchPathRuntime.from_state(state, compiled)
        assert action in runtime.legal_actions()
        with runtime.pushed(action):
            assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
        runtime.assert_balanced()
