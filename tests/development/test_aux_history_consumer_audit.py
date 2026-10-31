"""Offline evidence corruption checks; exhausted producers are never invoked."""
from copy import deepcopy
import pytest
from scripts.aux_history_consumer_audit import audit,read_bound

@pytest.fixture
def packet(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("offline audit must not call Player/prover")
    monkeypatch.setattr('generic_chess.ai.alphabeta.player.AlphaBetaPlayer.choose_action',forbidden)
    monkeypatch.setattr('scripts.generic_session_win_proof.prove_session_win',forbidden)
    return read_bound()

def test_actual_saved_pvs_regret_and_failed_dispatch_cost(packet):
    result=audit(packet)
    assert result['actual_Player_calls_all_dispatches']==5
    assert not result['budget_compliant']
    assert result['total_paid_nodes']=='UNKNOWN_FIRST_RETURN_LOST'
    assert result['claim_level']=='DESCRIPTIVE_PROTOCOL_FAILURE'
    assert [(r['history'],r['depth'],r['actor1_regret'])for r in result['rows']]==[
        ('DRAW',1,1),('WIN',1,0),('DRAW',3,0),('WIN',3,0)]
    assert result['rows'][2]['terminal_status']=='repetition'
    assert result['actual_offline_GameSession_submit_calls']==52

@pytest.mark.parametrize('case',[
    'omit_lost_call','lower_plan_to_actual','wrong_root_seat','strict_loss_as_zero',
    'drop_branch','failed_proof_as_draw','selected_semantic_alias','wrong_prefix',
    'pv_first_action','terminal_value','leaf_features','hidden_attempt_nodes'])
def test_corrupt_evidence_is_rejected_without_search(packet,case):
    q=packet['q0-observed.json'];b=packet['branch-observed.json']
    if case=='omit_lost_call':packet['q0-accounting-correction.json']['actual_Player_calls']=4
    elif case=='lower_plan_to_actual':packet['q0-protocol.json']['budget']['Player_calls']=5
    elif case=='wrong_root_seat':q['rows'][0]['actual_root_actor']=0
    elif case=='strict_loss_as_zero':q['rows'][0]['actor_regret_bounds']=[0,0]
    elif case=='drop_branch':b['rows'].pop()
    elif case=='failed_proof_as_draw':
        row=next(r for r in b['rows']if not r['verified_check']['verified'])
        row['classification']='DRAW';row['child_value_for0_bounds']=[0,0]
    elif case=='selected_semantic_alias':q['rows'][0]['selected_action']['pattern_id']='different_same_coordinates'
    elif case=='wrong_prefix':q['rows'][0]['literal_leaf_record']['actions'][0]['to']=[1,1]
    elif case=='pv_first_action':q['rows'][0]['receipt']['action']['action']['geometry_id']='different'
    elif case=='terminal_value':q['rows'][2]['receipt']['value']=1.
    elif case=='leaf_features':q['rows'][0]['receipt']['pv_phi']=[0,0]
    elif case=='hidden_attempt_nodes':q['rows'][0]['receipt']['attempts'][0]['nodes']=4
    with pytest.raises(ValueError):audit(packet)

def test_closed_producer_refuses_before_any_computation():
    from scripts.aux_history_q0_consumer import run
    with pytest.raises(RuntimeError,match='CLOSED_CAP_EXCEEDED'):run('unused')
