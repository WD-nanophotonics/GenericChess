"""Actual full-mechanism certificates and interruption guard for new ordering."""
import pytest
from time import perf_counter
from scripts.generic_session_win_proof_batch_pn import _Forward,_children
from scripts.generic_win_proof import _Budget
from results.dev_aux.task1951.check_first import prove_check_first,ordered_children
from test_generic_session_win_proof import session,claim
from test_generic_session_proof_mechanisms import (test_actual_capture_hand_then_drop_mate_is_preserved as _drop,test_real_forced_promotion_mate_retains_base_piece as _promotion,test_real_pass_draw_defense_cannot_be_omitted as _pass,test_actual_played_perpetual_history_win_is_not_mislabeled_mate as _perpetual,test_actual_no_progress_draw_and_depth_unknown_remain_distinct as _draw,test_semantic_action_ids_survive_transport_and_forged_ids_fail_public_execution as _semantic)
from scripts.generic_session_win_proof import verify_session_certificate

@pytest.mark.parametrize('mechanism',[_drop,_promotion,_pass,_perpetual,_draw,_semantic])
def test_real_full_rule_mechanism(mechanism):mechanism(prove_check_first)

@pytest.mark.parametrize('outcome',['WIN','LOSS','RESTART'])
def test_complete_frontier_records_equal_original(outcome):
 s=session(claim(0,outcome));current=_Forward(s.compiled,s.state,s.to_record(),s.result);costs=[];frontiers=[]
 for factory in (_children,ordered_children):
  b=_Budget(100000,5.,None,perf_counter);cost=[0,0];frontiers.append(dict(factory(current,b,cost)));costs.append(cost)
 assert frontiers[0]==frontiers[1] and costs[0]==costs[1]

@pytest.mark.parametrize('outcome',['WIN','RESTART'])
def test_defender_nonloss_claim_still_refutes(outcome):
 s=session(claim(1,outcome),k=0,b=2,r=10,turn=1);r=prove_check_first(s,target=0,max_depth=8,seconds=3.)
 assert r.status=='UNKNOWN' and r.certificate is None

def test_winning_claim_streams_before_unneeded_board(monkeypatch):
 import scripts.generic_session_win_proof_batch_pn as base
 def forbidden(*args):raise AssertionError('unused board frontier')
 monkeypatch.setattr(base,'legal_successors',forbidden)
 s=session(claim(0,'WIN'));r=prove_check_first(s,max_depth=1,seconds=3.)
 assert r.status=='PROVEN_WIN' and r.nodes==2 and verify_session_certificate(s,r.certificate,seconds=3.)['verified']

def test_cancel_during_check_ordering_cannot_emit_partial_certificate(monkeypatch):
 import results.dev_aux.task1951.check_first as module
 flag=[False];original=module.is_in_check
 def crossing(*args):
  v=original(*args);flag[0]=True;return v
 monkeypatch.setattr(module,'is_in_check',crossing)
 s=session(k=0,b=2,r=10,turn=1);record=s.to_record();r=prove_check_first(s,target=0,cancel=lambda:flag[0],seconds=3.)
 assert r.status=='UNKNOWN' and r.reason=='cancelled' and r.certificate is None and s.to_record()==record

@pytest.mark.parametrize('n,d',[(0,8),(1,8),(4096,0),(4096,1)])
def test_real_node_depth_limits_stay_unknown(n,d):
 s=session(k=0,b=2,r=10,turn=1);r=prove_check_first(s,target=0,max_nodes=n,max_depth=d,seconds=3.)
 assert r.status=='UNKNOWN' and r.certificate is None and r.nodes<=n
