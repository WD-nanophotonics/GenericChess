"""Finite availability primitive semantics: actual states, cutoff independence."""
from dataclasses import replace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import semantic as ns
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.search_backend_comparison import CASES,CoreBoard
from scripts.native_core_availability import NativeCoreAvailability
pytestmark=pytest.mark.skipif(not native_available(),reason='native extension unavailable')
@pytest.mark.parametrize('case_id',['chess-ep','chess-promotion','shogi-promotion','shogi-drop'])
def test_availability_is_readonly_and_agrees_with_existing_effect_children(case_id):
    case=next(x for x in CASES if x['id']==case_id)
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'))
    core=CoreBoard(case,c);candidate=NativeCoreAvailability(c);engine=semantic_engine_for(c)
    from scripts.full_q_refresh_comparison import runtime_state
    root=runtime_state(core.runtime);candidate.install()
    try:
        assert candidate(core.runtime)==engine.has_legal_action(core.runtime.position)
        for action in core.runtime.legal_actions()[:16]:
            core.runtime.push(action)
            try: assert candidate(core.runtime)==engine.has_legal_action(core.runtime.position)
            finally: core.runtime.pop()
        core.runtime.assert_balanced();assert runtime_state(core.runtime)==root
    finally:candidate.restore()
    assert candidate.fallbacks==0 and candidate.calls==candidate.imports==candidate.queries

@pytest.mark.parametrize('policy',['draw','loss'])
@pytest.mark.parametrize('repeated',[False,True])
def test_no_action_query_does_not_change_stalemate_or_history_priority(policy,repeated):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location("availability_policy_fixture",Path(__file__).parents[1]/"product"/"test_native_terminal_policy_support.py")
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    _stalemate=fixture._stalemate
    c,native,session,packed=_stalemate(policy,repeated)
    saved=ns.snapshot(native,packed)
    assert ns.has_legal_action(native,packed) is False
    assert ns.snapshot(native,packed)==saved
    from generic_chess.core.search_runtime import SearchPathRuntime
    from collections import Counter
    state=replace(session.state,repetition_counts=tuple(sorted(Counter(r.position_key for r in session.state.history).items())))
    rt=SearchPathRuntime(state,c,history_witnesses=session._search_witnesses)
    candidate=NativeCoreAvailability(c)
    assert candidate(rt) is False
    from generic_chess.core import terminal
    candidate.install()
    try:
        from generic_chess.core import search_runtime
        assert search_runtime.terminal_from_search_runtime(rt)==terminal.terminal_from_search_runtime(rt)
    finally:candidate.restore()

def test_query_ignores_ply_cutoff_and_checks_rules_identity():
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));case=next(x for x in CASES if x['id']=='chess-ep');core=CoreBoard(case,c);native=compile_native_semantic_rules(c)
    packed=ns.pack_current_position(native,core.runtime.position,ply_count=c.support.max_ply)
    before=ns.snapshot(native,packed)
    assert ns.has_legal_action(native,packed) is True
    assert ns.snapshot(native,packed)==before
    other=compile_native_semantic_rules(compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi')))
    with pytest.raises(ValueError,match='fingerprint'):ns.has_legal_action(other,packed)

@pytest.mark.parametrize('case_id',['chess-ep','chess-promotion','shogi-promotion','shogi-drop'])
def test_boolean_probe_audit_stops_at_legal_prefix_without_unused_history(case_id):
    from generic_chess.native import _module
    case=next(x for x in CASES if x['id']==case_id)
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'))
    core=CoreBoard(case,c);candidate=NativeCoreAvailability(c);native=candidate.provider.native_rules
    packed=ns.pack_position(native,candidate.provider._state_only_payload(core.runtime.position,0))
    saved=ns.snapshot(native,packed)
    audit=_module().semantic_has_legal_action_audit(native.capsule,packed)
    assert audit['available']==semantic_engine_for(c).has_legal_action(core.runtime.position)
    assert audit['candidate_count']>=1 and audit['s3_trial_count']>=audit['candidate_count']
    # Nested S4 reply guards may still construct their existing scoped witnesses.
    if audit['nested_reply_count']==0:
        assert audit['child_canonical_key_computations']==audit['history_appends']==0
    assert ns.snapshot(native,packed)==saved

@pytest.mark.parametrize('words',[2,4,6])
@pytest.mark.parametrize('length',[1,17,1025])
def test_live_prefix_pack_retains_exact_supplied_history_and_legacy_events(words,length):
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    core=CoreBoard(next(x for x in CASES if x['id']=='chess-ep'),c)
    provider=NativeCoreAvailability(c).provider;native=provider.native_rules
    payload=provider._state_only_payload(core.runtime.position,0)
    history=[]
    for i in range(length):
        row=[i+1,i+2,i+3,i+4,255 if i==0 else i%2,i%2]
        history.append(row[:words])
    payload['history']=history
    packed=ns.pack_position(native,payload);snap=ns.snapshot(native,packed)
    assert snap['history']==tuple(tuple(row[:4] if words==6 else row) for row in history)
    assert snap['history_exact']==(words!=2)
    assert snap['history_events']==tuple((row[4],bool(row[5])) if words==6 else (0,False) for row in history)
    assert snap['history_events_exact']==(words==6)
    assert snap['history_occurrences']==1
    assert ns.has_legal_action(native,packed)==semantic_engine_for(c).has_legal_action(core.runtime.position)
    assert ns.snapshot(native,packed)==snap

@pytest.mark.parametrize('mode',['decline','native','malformed','exception'])
def test_instance_availability_contract_and_push_rollback(mode):
    from generic_chess.core import search_runtime
    from scripts.full_q_refresh_comparison import runtime_state
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    core=CoreBoard(next(x for x in CASES if x['id']=='chess-ep'),c)
    native=NativeCoreAvailability(c);calls=[]
    def provider(position,checkpoint=None):
        calls.append(position)
        if mode=='decline':return None
        if mode=='malformed':return 1
        if mode=='exception':raise RuntimeError('provider interrupted')
        return native.for_position(position,checkpoint=checkpoint)
    rt=core.runtime;rt.availability_provider=provider
    saved=runtime_state(rt);action=rt.legal_actions()[0]
    if mode in ('malformed','exception'):
        with pytest.raises(TypeError if mode=='malformed' else RuntimeError):rt.push(action)
    else:
        rt.push(action)
        try: assert rt.terminal_status==__import__('generic_chess.core.terminal',fromlist=['terminal_from_search_runtime']).terminal_from_search_runtime(core_child(rt,c))
        finally:rt.pop()
    assert calls and runtime_state(rt)==saved
    rt.assert_balanced()

def core_child(rt,c):
    # Compare unchanged Core authority on the exact live child without a second
    # imported history representation or a Native terminal verdict.
    class View:
        def __getattr__(self,name):return getattr(rt,name)
    view=View();view.availability_provider=None
    return view

def test_two_runtime_availability_callbacks_are_isolated_and_checkpointed():
    from generic_chess.core import search_runtime,terminal
    from scripts.full_q_refresh_comparison import runtime_state
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    a=CoreBoard(next(x for x in CASES if x['id']=='chess-ep'),c).runtime
    b=CoreBoard(next(x for x in CASES if x['id']=='chess-promotion'),c).runtime
    engine=semantic_engine_for(c);counts=[0,0];polls=[];original=search_runtime.terminal_from_search_runtime
    def query(index):
        def call(position,checkpoint=None):
            counts[index]+=1
            if checkpoint:checkpoint()
            return engine.has_legal_action(position,checkpoint=checkpoint)
        return call
    a.availability_provider=query(0);b.availability_provider=query(1)
    before=[runtime_state(a),runtime_state(b)]
    for rt in (a,b,a):
        terminal.terminal_from_search_runtime(rt,checkpoint=lambda:polls.append(1))
    assert counts==[2,1] and polls
    assert [runtime_state(a),runtime_state(b)]==before
    assert search_runtime.terminal_from_search_runtime is original
