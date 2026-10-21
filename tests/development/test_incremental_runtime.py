"""The learner reuses mainline Core without changing its episode targets."""
from dataclasses import replace
import pytest

from generic_chess.learning.incremental import (
    AlphaBeta, BudgetEnd, FixedScaleSessionEnv, Model, NonScoringTerminal,
    SessionChoice,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import weird_rulesets
from scripts.generic_proof_fixtures import krk_ruleset
from product.test_no_progress_search_context import pair


def compare(session, unit='P'):
    envs = [FixedScaleSessionEnv(session, unit_type=unit, use_runtime=mode)
            for mode in (False, True)]
    before = envs[0].record()
    results = [AlphaBeta(2, 0).search(e, Model([1.] * len(e.names)),
                nodes=20_000, seconds=20, seed=4321) for e in envs]
    left, right = results
    assert left.complete and right.complete
    assert (left.action, left.value, left.pv_phi, left.pv_terminal,
            left.samples, left.nodes) == (
            right.action, right.value, right.pv_phi, right.pv_terminal,
            right.samples, right.nodes)
    assert all(e.record() == before and not e.stack for e in envs)


def test_no_progress_actual_different_histories_use_same_shared_core():
    _, sessions = pair()
    assert sessions[0].compiled._legacy_compiled is None
    for session in sessions:
        assert FixedScaleSessionEnv(session).names[0] == ('board', 'P')
        compare(session)
        view = FixedScaleSessionEnv(session).search_view()
        assert view.runtime._no_progress_context is not None
        view.runtime.assert_balanced()


@pytest.mark.parametrize('source', weird_rulesets())
def test_semantic_action_frontier_matches_public_session(source):
    compiled = compile_ruleset_for_execution(source)
    session = GameSession(compiled)
    unit = next(p.type_id for p in source.piece_types if not p.is_anchor)
    compare(session, unit)


@pytest.mark.parametrize('outcome', ('WIN', 'LOSS', 'RESTART', 'NO_CONTEST'))
def test_declaration_assessment_and_restore_use_shared_rule_authority(outcome):
    source = replace(krk_ruleset(4), declarations=(
        RuleDeclaration('claim', 0, require_not_in_check=False, failure_outcome=outcome),))
    session = GameSession(compile_ruleset_for_execution(source))
    env = FixedScaleSessionEnv(session, unit_type='R')
    view = env.search_view()
    key = view.runtime.search_key()
    choice = SessionChoice('DECLARATION', declaration_id='claim')
    view.push(choice)
    env.push(choice)
    if outcome in ('RESTART', 'NO_CONTEST'):
        with pytest.raises(NonScoringTerminal): view.terminal()
        with pytest.raises(NonScoringTerminal): env.terminal()
    else:
        assert view.terminal() == env.terminal()
    view.pop(); env.pop()
    assert view.runtime.search_key() == key
    assert view.terminal() is env.terminal() is None
    assert view.runtime.depth == 0


def test_budget_after_root_admission_is_incomplete_and_preserves_public_root(monkeypatch):
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))), unit_type='R')
    before = env.record()
    factory = env.search_view
    cancelled = False
    def admitted():
        nonlocal cancelled
        view = factory()
        cancelled = True
        return view
    def guard():
        if cancelled:
            raise BudgetEnd('STOPPED_USER')
    monkeypatch.setattr(env, 'search_view', admitted)
    result = AlphaBeta(2, 0).search(env, Model([1.] * len(env.names)), cancel=guard)
    assert not result.complete and result.reason == 'STOPPED_USER'
    assert result.nodes == 0 and result.value is result.action is None
    assert env.record() == before


def test_root_import_time_is_charged_before_searching_any_node(monkeypatch):
    from generic_chess.learning import incremental
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))), unit_type='R')
    clock = [0.]
    factory = env.search_view
    def admitted():
        view = factory()
        clock[0] = 1.
        return view
    monkeypatch.setattr(env, 'search_view', admitted)
    monkeypatch.setattr(incremental.time, 'perf_counter', lambda: clock[0])
    result = AlphaBeta(2, 0).search(env, Model([1.] * len(env.names)), seconds=.5)
    assert not result.complete and result.nodes == 0
    assert result.seconds == 1. and result.reason == 'resource limit'
