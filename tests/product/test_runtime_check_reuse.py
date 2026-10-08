"""Computed current-child check is reusable; history responsibility is not."""
from dataclasses import replace

import pytest

from generic_chess.core.actions import PassAction
from generic_chess.core.attacks import is_in_check
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from ai_fixtures import build_4x4_rooks
from conftest import make_state
from rule_semantics_ir_fixtures import cannon_ruleset, weird_rulesets
from test_generic_pass_action import _compiled


def truth(runtime, owner):
    engine = semantic_engine_for(runtime.compiled)
    return (engine.in_check(runtime.position, owner) if engine is not None
            else is_in_check(runtime.position, owner, runtime.compiled))


@pytest.mark.parametrize('factory', [build_4x4_rooks,
    lambda: compile_ruleset_for_execution(cannon_ruleset()),
    *[lambda index=i: compile_ruleset_for_execution(weird_rulesets()[index])
      for i in range(3)]])
def test_check_matches_independent_queries_through_nested_push_pop(factory):
    compiled = factory()
    runtime = SearchPathRuntime(GameSession(compiled).state, compiled)
    root = runtime.position
    for first in runtime.legal_actions()[:12]:
        with runtime.pushed(first):
            parent = runtime.position
            for owner in (0, 1):
                assert runtime.in_check(owner) == truth(runtime, owner)
            for second in runtime.legal_actions()[:5]:
                with runtime.pushed(second):
                    for owner in (0, 1):
                        assert runtime.in_check(owner) == truth(runtime, owner)
                assert runtime.position is parent
                assert runtime.in_check(parent.side_to_move) == truth(runtime, parent.side_to_move)
        assert runtime.position is root
        assert runtime.in_check(root.side_to_move) == truth(runtime, root.side_to_move)
    runtime.assert_balanced()


def test_child_reuses_query_but_root_and_other_owner_do_not(monkeypatch):
    compiled = build_4x4_rooks()
    runtime = SearchPathRuntime(GameSession(compiled).state, compiled)
    original = is_in_check
    calls = []

    def counted(position, owner, compiled):
        calls.append((position, owner))
        return original(position, owner, compiled)

    monkeypatch.setattr('generic_chess.core.search_runtime.is_in_check', counted)
    runtime.in_check(runtime.position.side_to_move)
    assert len(calls) == 1
    with runtime.pushed(runtime.legal_actions()[0]):
        before = len(calls)
        side = runtime.position.side_to_move
        expected = truth(runtime, side)
        assert runtime.in_check(side) == expected
        assert runtime.in_check(side) == expected
        assert len(calls) == before
        runtime.in_check(1 - side)
        assert len(calls) == before + 1
    before = len(calls)
    runtime.in_check(runtime.position.side_to_move)
    assert len(calls) == before + 1


@pytest.mark.parametrize('semantic', [False, True])
def test_pass_history_false_does_not_override_actual_check(semantic):
    _, compiled = _compiled(semantic, True)
    size = compiled.board_size
    lines = ['.' * size for _ in range(size)]
    lines[0] = '.' * (size - 1) + 'k'
    lines[-1] = 'K' + '.' * (size - 2) + 'R'
    state = make_state(compiled, lines)
    runtime = SearchPathRuntime(state, compiled)
    assert PassAction() in runtime.legal_actions()
    with runtime.pushed(PassAction()):
        assert runtime.history[-1].gave_check is False
        assert truth(runtime, 1) is True
        assert runtime.in_check(1) is True
    runtime.assert_balanced()


def test_cached_query_keeps_cancellation_and_exception_undo():
    compiled = build_4x4_rooks()
    runtime = SearchPathRuntime(GameSession(compiled).state, compiled)
    root = runtime.position

    def cancel():
        raise RuntimeError('cancel check')

    with pytest.raises(RuntimeError, match='cancel check'):
        with runtime.pushed(runtime.legal_actions()[0]):
            runtime.in_check(runtime.position.side_to_move, checkpoint=cancel)
    assert runtime.position is root
    runtime.assert_balanced()


def test_imported_history_does_not_supply_root_check():
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    session.submit(session.legal_actions()[0])
    runtime = SearchPathRuntime(session.state, compiled)
    assert not runtime._frames
    # A recorded checking responsibility is distinct from a reusable DFS child.
    assert runtime.history
    runtime._history[-1] = replace(runtime.history[-1], gave_check=not truth(runtime, runtime.position.side_to_move))
    assert runtime.in_check(runtime.position.side_to_move) == truth(runtime, runtime.position.side_to_move)
