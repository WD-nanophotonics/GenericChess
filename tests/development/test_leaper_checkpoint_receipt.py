"""Pinned real Native checkpoint boundaries; no timing or extra service probes."""
import pytest
from scripts.leaper_checkpoint_receipt import CheckpointReceiptProvider
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as Provider
from generic_chess.ai.alphabeta.search import SearchAborted


def prepared():
    from generic_chess.native import native_available
    if not native_available():pytest.skip('Native unavailable')
    from scripts import leaper_design as L
    from generic_chess.session.session import GameSession
    c=L.compile_rule(L.definition(1,2));s=GameSession(c);p=Provider.try_create(c,strict=True)
    assert p is not None
    return c,s,p


@pytest.mark.parametrize('ordinal',[1,2,3,4])
def test_current_attempt_exit_matches_real_original_poll_order_and_stale_success(ordinal):
    c,s,p=prepared();before=s.to_record();p._metrics_local.last={'previous_success':123};proxy=CheckpointReceiptProvider(p);seen=[];expected=SearchAborted('boundary')
    def poll():
        seen.append(len(seen)+1)
        if len(seen)==ordinal:raise expected
    with pytest.raises(SearchAborted) as error:proxy(s.state.position,0,checkpoint=poll)
    assert error.value is expected and seen==list(range(1,ordinal+1)) and s.to_record()==before
    r=proxy.last_attempt_receipt;assert r['status']=='raised' and r['failed_checkpoint']==ordinal
    assert r['kernel_returned_known']==(ordinal>=3)
    assert r['exit_boundary']=={1:'entry_checkpoint',2:'packed_before_kernel_checkpoint',3:'kernel_returned_before_decode_checkpoint',4:'decode_chunk_or_final_checkpoint'}[ordinal]
    assert p.last_call_metrics==proxy.last_call_metrics=={'previous_success':123}
    assert proxy.receipt_summary['valid'] and proxy.receipt_summary['entries']==proxy.receipt_summary['exits']==1


def test_normal_return_same_public_actions_and_no_added_none_checkpoint_calls():
    from scripts.research_record import record_value
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p)
    expected=p(s.state.position,0,checkpoint=None);got=proxy(s.state.position,0,checkpoint=None)
    assert [record_value(x[0]) for x in got]==[record_value(x[0]) for x in expected]
    r=proxy.last_attempt_receipt;assert r['status']=='returned' and r['kernel_returned_known'] is True
    assert r['checkpoint_count'] is None and not r['checkpoint_observed']
    value=proxy.last_attempt_receipt;value['status']='tampered';assert proxy.last_attempt_receipt['status']=='returned'


def test_native_api_exception_between_pack_and_postkernel_poll_is_unknown(monkeypatch):
    import generic_chess.native.semantic as native
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p);expected=ValueError('injectedNativeerror');polls=[]
    def failure(*args):raise expected
    monkeypatch.setattr(native,'transient_legal_actions',failure)
    with pytest.raises(ValueError) as error:proxy(s.state.position,0,checkpoint=lambda:polls.append(1))
    assert error.value is expected and len(polls)==2
    r=proxy.last_attempt_receipt;assert r['failed_checkpoint'] is None and r['last_passed_checkpoint']==2
    assert r['kernel_returned_known'] is None and r['exit_boundary']=='between_checkpoints'


def test_source_drift_is_rejected_before_recording_or_global_mutation(monkeypatch):
    c,s,p=prepared();monkeypatch.setattr(Provider,'__call__',lambda *args,**kwargs:())
    with pytest.raises(ValueError,match='sourcechanged'):CheckpointReceiptProvider(p)


def test_nested_call_is_forwarded_but_observation_invalid():
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p);entered=False
    def poll():
        nonlocal entered
        if not entered:entered=True;proxy(s.state.position,0,checkpoint=None)
    result=proxy(s.state.position,0,checkpoint=poll)
    assert result and proxy.receipt_summary['entries']==proxy.receipt_summary['exits']==2
    assert not proxy.receipt_summary['valid'] and proxy.receipt_summary['nested_calls']==1


def test_player_cancel_consumes_receipt_without_changing_original_result_or_undo(monkeypatch):
    import generic_chess.native.semantic as native
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.cancellation import CancellationToken
    from generic_chess.ai.limits import SearchLimits
    c,s,_=prepared();before=s.to_record();real=native.transient_legal_actions;active={'token':None};results=[]
    def cancel_after(*args):
        value=real(*args)
        if active['token'] is not None:active['token'].cancel()
        return value
    monkeypatch.setattr(native,'transient_legal_actions',cancel_after)
    for on in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
        proxy=CheckpointReceiptProvider(p.native_legality_provider)
        if on:p._native_legality_provider=proxy
        token=CancellationToken();active['token']=token
        d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=50000,max_time_seconds=3,quiescence_max_depth=4),cancel_token=token);active['token']=None
        assert before==s.to_record() and d.runtime_depth_balanced and d.termination_reason=='cancelled'
        results.append((d.choice_kind,d.action,d.principal_variation,d.nodes,d.qnodes,d.result_source,d.runtime_pushes,d.runtime_pops))
        if on:
            r=proxy.last_failed_attempt_receipt
            assert r['failed_checkpoint']==3 and r['kernel_returned_known'] is True
            latest=proxy.last_attempt_receipt
            assert r['id']==1 and latest['id']==2 and latest['status']=='returned'
            assert latest['failed_checkpoint'] is None and latest['checkpoint_count']==4
            assert proxy.receipt_summary['valid'] and d.native_legality_calls==1
    assert results[0]==results[1]


def test_failed_receipt_is_historical_copy_and_success_does_not_erase_it():
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p);expected=SearchAborted('first')
    def cancel():raise expected
    with pytest.raises(SearchAborted):proxy(s.state.position,0,checkpoint=cancel)
    old=proxy.last_failed_attempt_receipt
    assert old['id']==1 and old['failed_checkpoint']==1
    old['failed_checkpoint']=99
    proxy(s.state.position,0,checkpoint=None)
    assert proxy.last_attempt_receipt['id']==2 and proxy.last_attempt_receipt['status']=='returned'
    assert proxy.last_failed_attempt_receipt['id']==1 and proxy.last_failed_attempt_receipt['failed_checkpoint']==1


def test_no_checkpoint_exception_does_not_claim_observed_kernel_phase(monkeypatch):
    import generic_chess.native.semantic as native
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p);expected=RuntimeError('no-poll-native')
    def failure(*args):raise expected
    monkeypatch.setattr(native,'transient_legal_actions',failure)
    with pytest.raises(RuntimeError) as error:proxy(s.state.position,0,checkpoint=None)
    assert error.value is expected
    r=proxy.last_failed_attempt_receipt
    assert r['exit_boundary']=='no_checkpoint_observation' and r['kernel_returned_known'] is None
    assert r['checkpoint_count'] is None and proxy.receipt_summary['valid']


def test_decoding_failure_after_kernel_is_not_misclassified_as_kernel_failure(monkeypatch):
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p);expected=ValueError('decode')
    def failure(*args):raise expected
    monkeypatch.setattr(p,'_decode_action',failure)
    with pytest.raises(ValueError) as error:proxy(s.state.position,0,checkpoint=lambda:None)
    assert error.value is expected
    r=proxy.last_failed_attempt_receipt
    assert r['last_passed_checkpoint']==3 and r['failed_checkpoint'] is None
    assert r['exit_boundary']=='between_checkpoints' and r['kernel_returned_known'] is True


def test_foreign_thread_forwarding_is_explicitly_invalid():
    import threading
    c,s,p=prepared();proxy=CheckpointReceiptProvider(p);errors=[]
    def run():
        try:proxy(s.state.position,0,checkpoint=lambda:None)
        except BaseException as exc:errors.append(exc)
    t=threading.Thread(target=run);t.start();t.join(timeout=5)
    assert not t.is_alive() and not errors
    assert proxy.receipt_summary['foreign_thread_calls']==1 and not proxy.receipt_summary['valid']
    assert not proxy.last_attempt_receipt['scope_valid']


@pytest.mark.parametrize('count,ordinal,decoded_before',[(64,4,64),(65,4,64),(65,5,65)])
def test_chunk_and_final_poll_share_explicitly_ambiguous_exit(monkeypatch,count,ordinal,decoded_before):
    # Deliberately repeated packed actions exercise the pinned provider loop,
    # not Core admission (Core correctly rejects duplicate public actions).
    import generic_chess.native.semantic as native
    c,s,p=prepared();real=native.transient_legal_actions
    packed=real(p.native_rules,p._pack_position(s.state.position,0))[0]
    monkeypatch.setattr(native,'transient_legal_actions',lambda *args:(packed,)*count)
    original_decode=p._decode_action;decoded=[]
    def decode(*args):decoded.append(1);return original_decode(*args)
    monkeypatch.setattr(p,'_decode_action',decode)
    proxy=CheckpointReceiptProvider(p);polls=[];expected=SearchAborted('chunk-or-final')
    def checkpoint():
        polls.append(1)
        if len(polls)==ordinal:raise expected
    with pytest.raises(SearchAborted) as error:proxy(s.state.position,0,checkpoint=checkpoint)
    assert error.value is expected and len(decoded)==decoded_before
    r=proxy.last_failed_attempt_receipt
    assert r['failed_checkpoint']==ordinal and r['exit_boundary']=='decode_chunk_or_final_checkpoint'
    assert r['kernel_returned_known'] is True and proxy.receipt_summary['valid']


def test_recording_error_never_masks_original_exception_or_produces_valid_receipt():
    class BrokenReceipt(CheckpointReceiptProvider):
        def __setattr__(self,name,value):
            if name=='_last' and isinstance(value,dict):raise ValueError('injected-recorder-storage')
            super().__setattr__(name,value)
    c,s,p=prepared();proxy=BrokenReceipt(p);expected=SearchAborted('real-cancel')
    def checkpoint():raise expected
    with pytest.raises(SearchAborted) as error:proxy(s.state.position,0,checkpoint=checkpoint)
    assert error.value is expected and proxy.last_attempt_receipt is None
    assert proxy.receipt_summary['record_errors']==1 and not proxy.receipt_summary['valid']


def test_cancellation_after_provider_return_is_outside_receipt_not_false_native_abort():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.cancellation import CancellationToken
    from generic_chess.ai.limits import SearchLimits
    c,s,_=prepared();before=s.to_record();token=CancellationToken()
    class CancelAfterReturn(CheckpointReceiptProvider):
        def __call__(self,*args,**kwargs):
            result=super().__call__(*args,**kwargs)
            token.cancel()
            return result
    p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
    proxy=CancelAfterReturn(p.native_legality_provider);p._native_legality_provider=proxy
    d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=50000,max_time_seconds=3,quiescence_max_depth=4),cancel_token=token)
    assert d.termination_reason=='cancelled' and d.root_scan_used_fallback
    assert before==s.to_record() and d.runtime_depth_balanced
    # Core's post-return checked() aborts the first attempt outside this proxy;
    # root fallback invokes a second successful provider call with a no-op poll.
    assert proxy.receipt_summary['entries']==proxy.receipt_summary['exits']==2
    assert proxy.receipt_summary['valid'] and proxy.last_failed_attempt_receipt is None
    assert proxy.last_attempt_receipt['status']=='returned' and proxy.last_attempt_receipt['id']==2
    assert proxy.last_attempt_receipt['checkpoint_count']==4 and d.native_legality_calls==1


def test_deeper_kernel_cancel_preserves_active_runtime_undo_and_original_work(monkeypatch):
    import generic_chess.native.semantic as native
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.cancellation import CancellationToken
    from generic_chess.ai.limits import SearchLimits
    c,s,_=prepared();before=s.to_record();real=native.transient_legal_actions;active={'token':None,'calls':0};results=[]
    def cancel_third(*args):
        value=real(*args);active['calls']+=1
        if active['calls']==3:active['token'].cancel()
        return value
    monkeypatch.setattr(native,'transient_legal_actions',cancel_third)
    for on in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
        proxy=CheckpointReceiptProvider(p.native_legality_provider)
        if on:p._native_legality_provider=proxy
        active.update(token=CancellationToken(),calls=0)
        d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=50000,max_time_seconds=3,quiescence_max_depth=4),cancel_token=active['token'])
        assert before==s.to_record() and d.runtime_depth_balanced and d.termination_reason=='cancelled'
        assert d.runtime_pushes==d.runtime_pops and d.runtime_pushes>0
        results.append((d.action,d.score,d.completed_depth,d.principal_variation,d.nodes,d.qnodes,d.runtime_pushes,d.runtime_pops,d.result_source,active['calls']))
        if on:
            r=proxy.last_failed_attempt_receipt
            assert r['id']==3 and r['failed_checkpoint']==3 and r['kernel_returned_known'] is True
            assert proxy.receipt_summary['valid']
    assert results[0]==results[1]
