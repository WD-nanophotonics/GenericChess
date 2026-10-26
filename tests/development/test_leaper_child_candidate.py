"""Falsify a real guarded constructor, not product default activation."""
from dataclasses import replace
import importlib
from pathlib import Path

import pytest

from generic_chess.core.position import Hands
from generic_chess.core.search_runtime import SearchPathRuntime, RuntimeCountsSnapshot
from generic_chess.core.identity import RuntimeHash
from scripts.leaper_child_candidate import ChildRuntime, candidate_arm, selected_child
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import load
from scripts.research_record import record_value


INPUTS = Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz')


@pytest.fixture
def root():
    row = next(x for x in load(INPUTS)['rows'] if x['prefix_length'] == 2)
    return make_session(row)


def runtime(cls, c, s, **kwargs):
    return cls.from_state(s.state, c, history_witnesses=s._search_witnesses, **kwargs)


def snapshot(r):
    return (r.position, r.ply_count, r.terminal_status, tuple(r.history),
            r.runtime_hash, r.search_key(), r.repetition_counts,
            {h: tuple((v.identity, v.count) for v in b) for h, b in r._occurrences.items()},
            r.depth, r._history_context, r._no_progress_context)


def test_real_selected_push_and_undo_match_core(root):
    c, s = root
    a, b = runtime(SearchPathRuntime, c, s), runtime(ChildRuntime, c, s)
    assert a.legal_actions() == b.legal_actions() == s.legal_actions()
    before = snapshot(b)
    for action in a.legal_actions():
        a.push(action); b.push(action)
        assert snapshot(a) == snapshot(b)
        a.pop(); b.pop()
        assert snapshot(b) == before
    assert b.child_successes > 0 and b.child_fallbacks == 0


def test_explicit_square_shape_is_normalized_not_parent_replaced(root):
    c, s = root
    r = runtime(ChildRuntime, c, s)
    action = r.legal_actions()[0]
    semantic, binding = r._bindings[action]
    parent = replace(r.position, board_width=c.board_size, board_height=c.board_size)
    expected = r.child_engine._transition(parent, semantic, binding)
    actual = selected_child(r, r.child_engine, parent, semantic, binding)
    assert actual == expected and actual.board_width is None and actual.board_height is None
    assert r.child_successes == 1


@pytest.mark.parametrize('kind', ['hands', 'aux', 'binding', 'foreign_fingerprint'])
def test_unsupported_parent_or_binding_falls_back_once(root, monkeypatch, kind):
    c, s = root
    r = runtime(ChildRuntime, c, s)
    action = r.legal_actions()[0]; semantic, binding = r._bindings[action]
    parent = r.position
    if kind == 'hands':
        parent = replace(parent, hands=(Hands((('unused', 1),)), Hands()))
    elif kind == 'aux':
        parent = replace(parent, aux_state=(((999, -1), 1),))
    elif kind == 'binding':
        binding = replace(binding, actor_base='foreign')
    else:
        parent = replace(parent, ruleset_fingerprint='foreign')
    calls = []
    engine = r.child_engine
    original = engine._transition
    # Patch only this test's observed original function; no benchmark uses it.
    def observed(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(type(engine), '_transition', lambda self, *a, **kw: observed(*a, **kw))
    expected = original(parent, semantic, binding)
    actual = selected_child(r, engine, parent, semantic, binding)
    assert actual == expected and len(calls) == 1
    assert r.child_fallbacks == 1 and r.child_attempts == 0


class InjectedAbort(BaseException):
    pass


def test_each_transition_effect_checkpoint_preserves_abort(root):
    c, s = root
    r = runtime(ChildRuntime, c, s); action = r.legal_actions()[0]
    semantic, binding = r._bindings[action]
    counts = []
    r.child_engine._transition(r.position, semantic, binding, checkpoint=lambda: counts.append(1))
    actual = []
    selected_child(r, r.child_engine, r.position, semantic, binding,
                   checkpoint=lambda: actual.append(1))
    assert len(actual) == len(counts) == len(binding.pattern.effects)
    for fail_at in range(1, len(counts) + 1):
        called = []
        def abort():
            called.append(1)
            if len(called) == fail_at:
                raise InjectedAbort()
        before = r.child_successes
        with pytest.raises(InjectedAbort):
            selected_child(r, r.child_engine, r.position, semantic, binding, checkpoint=abort)
        assert len(called) == fail_at and r.child_successes == before


@pytest.mark.parametrize('cls', [SearchPathRuntime, ChildRuntime])
@pytest.mark.parametrize('nested', [False, True])
@pytest.mark.parametrize('collision', [False, True])
def test_snapshot_failure_before_history_restores_occurrences_without_extra_pop(root, monkeypatch, cls, nested, collision):
    c, s = root; r = runtime(cls, c, s, hash_override=RuntimeHash(7, 7) if collision else None)
    if nested:
        r.push(r.legal_actions()[0])
    action = r.legal_actions()[0]; before = snapshot(r)
    def fail(*args, **kwargs):
        raise InjectedAbort('snapshot between occurrence add and history append')
    with monkeypatch.context() as m:
        m.setattr(RuntimeCountsSnapshot, 'updated', fail)
        with pytest.raises(InjectedAbort):
            with r.pushed(action):
                pytest.fail('failed push entered context body')
    assert snapshot(r) == before
    if nested:
        r.pop()
    r.assert_balanced()


def test_candidate_factory_is_real_and_restored_after_error(root):
    c, s = root; search = importlib.import_module('generic_chess.ai.alphabeta.search')
    assert search.SearchPathRuntime is SearchPathRuntime
    with pytest.raises(InjectedAbort):
        with candidate_arm(True):
            assert type(search.SearchPathRuntime.from_state(s.state, c,
                        history_witnesses=s._search_witnesses)) is ChildRuntime
            raise InjectedAbort()
    assert search.SearchPathRuntime is SearchPathRuntime
    with candidate_arm(False):
        assert type(search.SearchPathRuntime.from_state(s.state, c,
                    history_witnesses=s._search_witnesses)) is SearchPathRuntime


@pytest.mark.parametrize('capture', [False, True])
@pytest.mark.parametrize('cls', [SearchPathRuntime, ChildRuntime])
def test_every_actual_push_checkpoint_can_abort_without_losing_parent(root, capture, cls):
    c, s = root
    if capture:
        games = load('docs/research/data/leaper_pvs_quality_pilot_20261026/pilot/games.json')
        game = next(g for g in games if g['case_id'] == next(
            x['id'] for x in load(INPUTS)['rows'] if x['prefix_length'] == 2))
        for q in game['queries']:
            action = next(a for a in s.legal_actions() if record_value(a) == q['decision']['action'])
            target = action.to_square.rank * c.board_size + action.to_square.file
            if s.state.position.board[target] is not None:
                break
            s.submit(action)
        else:
            pytest.fail('saved capture control absent')
    else:
        action = s.legal_actions()[0]
    r = runtime(cls, c, s)
    r.legal_actions()
    before = snapshot(r)
    calls = []
    r.push(action, checkpoint=lambda: calls.append(1)); r.pop()
    assert snapshot(r) == before and len(calls) > 0
    for at in range(1, len(calls) + 1):
        observed = []
        def abort():
            observed.append(1)
            if len(observed) == at:
                raise InjectedAbort()
        with pytest.raises(InjectedAbort):
            r.push(action, checkpoint=abort)
        assert len(observed) == at and snapshot(r) == before
    r.assert_balanced()


@pytest.mark.parametrize('kind', ['ray', 'enabled_drop'])
def test_unsupported_rule_uses_original_transaction(kind):
    from scripts import leaper_design as L
    from generic_chess.core.movement import RayAtom
    from generic_chess.session.session import GameSession
    rule = L.definition(1, 2)
    if kind == 'ray':
        rule = replace(rule, piece_types=rule.piece_types[:2] +
                       (replace(rule.piece_types[2], movement_atoms=(RayAtom((1, 0)),)),))
    else:
        rule = replace(rule, drop_allowed={**rule.drop_allowed, 'A': ((True,) * 16,) * 2})
    c = L.compile_rule(rule); s = GameSession(c)
    a, b = runtime(SearchPathRuntime, c, s), runtime(ChildRuntime, c, s)
    assert b.child_patterns is None
    action = a.legal_actions()[0]
    a.push(action); b.push(action)
    assert snapshot(a) == snapshot(b)
    assert b.child_successes == 0 and b.child_fallbacks == 1
    a.pop(); b.pop()


def test_cost_comparison_keeps_full_action_and_work_fields():
    from scripts.leaper_child_cost import comparable_decision
    base = {'action': {'pattern_id': 'first', 'geometry_id': 'g'}, 'nodes': 19,
            'runtime_pushes': 33, 'elapsed_seconds': 0.5,
            'time_to_first_completed_iteration': 0.2}
    other = {**base, 'elapsed_seconds': 0.6, 'time_to_first_completed_iteration': 0.3}
    assert comparable_decision(base) == comparable_decision(other)
    other['nodes'] = 20
    assert comparable_decision(base) != comparable_decision(other)
    other = {**base, 'action': {'pattern_id': 'second', 'geometry_id': 'g'}}
    assert comparable_decision(base) != comparable_decision(other)


def test_new_cost_caller_reserves_inflight_and_delivery(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from scripts import leaper_child_cost as C
    plan = {'batch_seconds': 480, 'inflight_reserve_seconds': 5,
            'delivery_reserve_seconds': 720,
            'whole_deadline': (datetime.now(timezone.utc) + timedelta(seconds=740)).isoformat()}
    monkeypatch.setattr(C, 'read_json', lambda path: {})
    monkeypatch.setattr(C.time, 'perf_counter', lambda: 475)
    assert C.admission(plan, 0) == 'batch_dispatch_reserve'
    monkeypatch.setattr(C.time, 'perf_counter', lambda: 470)
    assert C.admission(plan, 0) is None
    plan['whole_deadline'] = (datetime.now(timezone.utc) + timedelta(seconds=724)).isoformat()
    assert C.admission(plan, 0) == 'whole_delivery_reserve'
    monkeypatch.setattr(C, 'read_json', lambda path: {'user_paused': True})
    assert C.admission(plan, 0) == 'scoped_stop'
