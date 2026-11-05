"""Observer contracts: transparent calls/exceptions, exact intervals, real abort/undo."""
import gc
from contextlib import nullcontext
import pytest
from scripts.leaper_latency_observer import FrontierObserver,overlap_union
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as Provider
from generic_chess.ai.alphabeta.search import SearchAborted


def test_interval_union_clips_and_does_not_double_count():
    assert overlap_union(0,10,[(1,4),(3,7)])==6
    assert overlap_union(2,5,[(1,4),(3,7),(2,3)])==3
    assert overlap_union(0,1,[(1,3),(-2,0)])==0


def test_special_method_path_return_identity_checkpoints_and_callback_restoration(monkeypatch):
    marker=object();seen=[]
    def original(self,position,ply_count,checkpoint=None):
        seen.append((position,ply_count))
        if checkpoint:checkpoint()
        return marker
    monkeypatch.setattr(Provider,'__call__',original)
    p=object.__new__(Provider);position=object();poll=[];callbacks=tuple(gc.callbacks);settings=(gc.isenabled(),gc.get_threshold(),gc.get_debug())
    obs=FrontierObserver()
    with obs:assert p(position,17,checkpoint=lambda:poll.append('poll')) is marker
    assert seen==[(position,17)] and poll==['poll']
    assert Provider.__call__ is original and tuple(gc.callbacks)==callbacks
    assert settings==(gc.isenabled(),gc.get_threshold(),gc.get_debug())
    assert obs.snapshot()['valid'] and obs.entries==obs.exits==1


def test_original_exception_identity_and_recording_failure_not_masked(monkeypatch):
    expected=SearchAborted('contract')
    def original(*args,**kwargs):raise expected
    monkeypatch.setattr(Provider,'__call__',original)
    obs=FrontierObserver();monkeypatch.setattr(obs,'_note',lambda *args:(_ for _ in ()).throw(ValueError('recorder')))
    with pytest.raises(SearchAborted) as error:
        with obs:object.__new__(Provider)(None,0)
    assert error.value is expected and Provider.__call__ is original
    assert obs.observer_errors==1 and not obs.snapshot()['valid']


def test_gc_is_wall_overlap_and_deadline_crossing_not_exclusive_kernel(monkeypatch):
    clock=[0.];obs=FrontierObserver(deadline=2,clock=lambda:clock[0])
    def original(*args,**kwargs):
        clock[0]=1;obs._gc_event('start',dict(generation=1))
        clock[0]=4;obs._gc_event('stop',dict(generation=1,collected=2))
        clock[0]=5;return 'same'
    monkeypatch.setattr(Provider,'__call__',original)
    with obs:assert object.__new__(Provider)(None,0)=='same'
    result=obs.snapshot();assert result['valid']
    span=result['deadline_crossings'][0];assert span['duration']==5 and span['gc_overlap_seconds']==3
    assert span['outcome']=='returned' and result['GC'][0]['frontier_owner']==1


@pytest.mark.parametrize('kind',['overflow','open','unpaired','clock'])
def test_incomplete_or_invalid_observation_never_means_no_gc(kind):
    now=[2.];obs=FrontierObserver(clock=lambda:now[0],gc_cap=1)
    with obs:
        if kind=='clock':now[0]=1
        elif kind=='open':obs._gc_event('start',dict(generation=0))
        elif kind=='unpaired':obs._gc_event('stop',dict(generation=0))
        else:
            for _ in range(2):obs._gc_event('start',dict(generation=0));obs._gc_event('stop',dict(generation=0))
    assert not obs.snapshot()['valid']


def test_other_callbacks_and_nested_scope_not_overwritten():
    before=tuple(gc.callbacks);foreign=lambda *args:None;obs=FrontierObserver()
    try:
        with obs:
            gc.callbacks.append(foreign)
            with pytest.raises(RuntimeError,match='nested'):
                with FrontierObserver():pass
        assert foreign in gc.callbacks and obs.snapshot()['valid']
    finally:
        gc.callbacks.remove(foreign)
    assert tuple(gc.callbacks)==before


def native_fixture():
    from generic_chess.native import native_available
    if not native_available():pytest.skip('Native backend unavailable')
    from scripts import leaper_design as L
    from generic_chess.session.session import GameSession
    c=L.compile_rule(L.definition(1,2));return c,GameSession(c)


@pytest.mark.parametrize('stop_at',[1,3])
def test_real_native_entry_and_post_kernel_abort_same_polls_and_stale_metrics(monkeypatch,stop_at):
    import generic_chess.native.semantic as native
    c,s=native_fixture();before=s.to_record();real=native.transient_legal_actions;kernel=[]
    def counted(*args):kernel.append('kernel');return real(*args)
    monkeypatch.setattr(native,'transient_legal_actions',counted)
    signatures=[]
    for on in (False,True):
        provider=Provider.try_create(c,strict=True);assert provider is not None
        provider._metrics_local.last={'previous_call_marker':17};polls=[];expected=SearchAborted('actualcheckpoint');obs=FrontierObserver()
        def checkpoint():
            polls.append('poll')
            if len(polls)==stop_at:raise expected
        start=len(kernel)
        with pytest.raises(SearchAborted) as error:
            with (obs if on else nullcontext()):provider(s.state.position,0,checkpoint=checkpoint)
        signatures.append((len(polls),len(kernel)-start,provider.last_call_metrics))
        assert error.value is expected and s.to_record()==before
        if on:
            r=obs.snapshot();assert r['valid'] and r['entries']==r['exits']==r['exception_exits']==1
            assert r['longest'][0]['outcome']=='SearchAborted'
    assert signatures==[(stop_at,int(stop_at==3),{'previous_call_marker':17})]*2


def test_real_player_post_kernel_cancel_same_result_and_runtime_undo(monkeypatch):
    import generic_chess.native.semantic as native
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.cancellation import CancellationToken
    from generic_chess.ai.limits import SearchLimits
    c,s=native_fixture();before=s.to_record();real=native.transient_legal_actions;active={'token':None};decisions=[]
    def cancel_after(*args):
        value=real(*args)
        if active['token'] is not None:active['token'].cancel()
        return value
    monkeypatch.setattr(native,'transient_legal_actions',cancel_after)
    for on in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
        token=CancellationToken();active['token']=token;obs=FrontierObserver()
        with (obs if on else nullcontext()):d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=50000,max_time_seconds=3,quiescence_max_depth=4),cancel_token=token)
        active['token']=None
        assert d.termination_reason=='cancelled' and d.runtime_depth_balanced and before==s.to_record()
        decisions.append((d.choice_kind,d.action,d.principal_variation,d.nodes,d.qnodes,d.result_source,d.runtime_pushes,d.runtime_pops))
        if on:assert obs.snapshot()['valid'] and obs.snapshot()['exception_exits']==1
    assert decisions[0]==decisions[1]


def test_failed_clock_is_invalid_serializable_evidence_not_changed_return(monkeypatch):
    import json
    marker=object()
    monkeypatch.setattr(Provider,'__call__',lambda *args,**kwargs:marker)
    def bad_clock():raise ValueError('clockunavailable')
    obs=FrontierObserver(clock=bad_clock)
    with obs:assert object.__new__(Provider)(None,0) is marker
    data=obs.snapshot();assert not data['valid'] and data['observer_errors']>0
    json.dumps(data,allow_nan=False)
