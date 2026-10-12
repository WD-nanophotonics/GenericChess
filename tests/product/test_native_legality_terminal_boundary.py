"""Native empty frontiers do not establish Core's terminal cause."""

from dataclasses import replace

import pytest

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.pieces import Piece
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action
from generic_chess.native import native_available
from generic_chess.session.session import GameSession


@pytest.mark.skipif(not native_available(), reason="native unavailable")
@pytest.mark.parametrize("target,checked", (((0, 7), True), ((0, 2), False)))
def test_max_ply_keeps_core_terminal_cause_with_empty_native_frontier(target, checked):
    rows = [[None] * 8 for _ in range(8)]
    rows[1][0] = Piece(0, "Q", "Q")
    rows[0][6] = Piece(0, "K", "K")
    rows[7][7] = Piece(1, "K", "K")
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("western_chess"), max_ply=1,
        initial_position=tuple(map(tuple, rows)),
    ))
    session = GameSession(compiled)
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    assert provider is not None
    runtime = SearchPathRuntime.from_state(
        session.state, compiled, history_witnesses=session._search_witnesses,
        legal_binding_provider=provider,
    )
    action = next(a for a in runtime.legal_actions()
                  if (a.from_square.file, a.from_square.rank) == (0, 1)
                  and (a.to_square.file, a.to_square.rank) == target)
    expected = apply_action(session.state, action, compiled)
    with runtime.pushed(action):
        assert runtime._frames[-1].child_in_check is checked
        assert semantic_engine_for(compiled).has_legal_action(runtime.position)
        assert provider(runtime.position, runtime.ply_count, None) == ()
        assert runtime.terminal_status == expected.terminal_status
        assert runtime.terminal_status.status is TerminalStatus.MAX_PLY
        assert runtime.legal_actions() == ()
    runtime.assert_balanced()
    assert runtime.position is session.state.position


@pytest.mark.skipif(not native_available(), reason="native unavailable")
def test_checked_repetition_keeps_raw_native_actions_out_of_terminal_cache():
    from conftest import T, king_type, make_ruleset, sq
    from generic_chess import compile_legacy_ruleset_for_semantic_execution
    from generic_chess.core.movement import RayAtom

    types = [king_type(), T("R", *(RayAtom(d) for d in
                                    ((1, 0), (-1, 0), (0, 1), (0, -1))))]
    compiled = compile_legacy_ruleset_for_semantic_execution(make_ruleset(
        4, types, lines=["...k", "....", "R...", "K..."], repetition_limit=2,
    ))
    session = GameSession(compiled)
    path = ((sq(0, 1), sq(3, 1)), (sq(3, 3), sq(2, 3)),
            (sq(3, 1), sq(2, 1)), (sq(2, 3), sq(3, 3)))
    for source, target in path:
        session.submit(next(a for a in session.legal_actions()
                            if a.from_square == source and a.to_square == target))
    root = session.state
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    assert provider is not None
    runtime = SearchPathRuntime.from_state(
        root, compiled, history_witnesses=session._search_witnesses,
        legal_binding_provider=provider,
    )
    action = next(a for a in runtime.legal_actions()
                  if a.from_square == sq(2, 1) and a.to_square == sq(3, 1))
    expected = apply_action(root, action, compiled)
    with runtime.pushed(action):
        assert runtime._frames[-1].child_in_check is True
        assert runtime.terminal_status == expected.terminal_status
        assert runtime.terminal_status.status is TerminalStatus.REPETITION
        assert len(provider(runtime.position, runtime.ply_count, None)) == 2
        assert runtime._legal_cache is None
        assert runtime.legal_actions() == ()
    runtime.assert_balanced()
    assert runtime.position is root.position


@pytest.mark.skipif(not native_available(), reason="native unavailable")
@pytest.mark.parametrize("strict", (False, True))
def test_ongoing_checking_continuation_at_max_ply_uses_core_fallback(strict):
    from generic_chess import RuleAutomaticAdjudication

    rows = [[None] * 8 for _ in range(8)]
    rows[1][0] = Piece(0, "Q", "Q")
    rows[0][6] = Piece(0, "K", "K")
    rows[7][7] = Piece(1, "K", "K")
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("western_chess"), max_ply=1,
        initial_position=tuple(map(tuple, rows)),
        automatic_adjudications=(RuleAutomaticAdjudication("checking-continuation", 1),),
    ))
    session = GameSession(compiled)
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=strict)
    assert provider is not None
    runtime = SearchPathRuntime.from_state(
        session.state, compiled, history_witnesses=session._search_witnesses,
        legal_binding_provider=provider,
    )
    action = next(a for a in runtime.legal_actions()
                  if a.from_square.file == 0 and a.from_square.rank == 1
                  and a.to_square.file == 0 and a.to_square.rank == 7)
    session.submit(action)
    with runtime.pushed(action):
        assert runtime.terminal_status.status is TerminalStatus.ONGOING
        assert runtime.terminal_status == session.state.terminal_status
        assert provider(runtime.position, runtime.ply_count, None) == ()
        assert not provider.supports_position(runtime.position, runtime.ply_count)
        assert set(runtime.legal_actions()) == set(session.legal_actions())
        assert len(runtime.legal_actions()) == 2
        assert runtime.legal_provider_fallbacks == 1
        assert runtime.legal_provider_operational_failures == 0
        assert runtime._legal_provider_active
        next_action = runtime.legal_actions()[0]
        expected = apply_action(session.state, next_action, compiled)
        with runtime.pushed(next_action):
            assert runtime.position == expected.position
            assert runtime.terminal_status == expected.terminal_status
    runtime.assert_balanced()
    assert runtime.ply_count == 0
    assert provider.supports_position(runtime.position, runtime.ply_count)


@pytest.mark.skipif(not native_available(), reason="native unavailable")
@pytest.mark.parametrize("max_ply", (1, 2))
def test_prelimit_s4_reply_probe_preserves_legal_checking_pawn_drop(max_ply):
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import GameState, Hands, HistoryRecord
    from generic_chess.core.transition import initial_state, legal_actions

    rows = [[None] * 9 for _ in range(9)]
    rows[0][4] = Piece(0, "K", "K")
    rows[8][4] = Piece(1, "K", "K")
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("standard_shogi"), max_ply=max_ply,
        initial_position=tuple(map(tuple, rows)),
    ))
    # Agent-constructed imported hand position, not a claimed played history.
    initial = initial_state(compiled)
    position = replace(initial.position, hands=(Hands((("P", 1),)), Hands()))
    key = repetition_identity_key(position, compiled)
    state = GameState(position, 0, ((key, 1),), initial.terminal_status,
                      (HistoryRecord(key, -1, "", False),))
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    assert provider is not None
    expected = legal_actions(state, compiled)
    target = next(a for a in expected if getattr(a, "from_square", None) is None
                  and a.to_square.file == 4 and a.to_square.rank == 7)
    runtime = SearchPathRuntime.from_state(
        state, compiled, history_witnesses=(position,), legal_binding_provider=provider,
    )
    assert set(runtime.legal_actions()) == set(expected)
    assert target in runtime.legal_actions()
    assert provider.supports_position(position, 0) is (max_ply == 2)
    assert runtime.legal_provider_fallbacks == (max_ply == 1)
    assert runtime.legal_provider_operational_failures == 0
    public_child = apply_action(state, target, compiled)
    with runtime.pushed(target):
        assert runtime.position == public_child.position
        assert runtime.terminal_status == public_child.terminal_status
    runtime.assert_balanced()
