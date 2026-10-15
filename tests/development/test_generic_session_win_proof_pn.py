"""Real public SessionChoice PN certificates and complete defenses."""
from dataclasses import replace
from copy import copy
import pytest
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor,SessionChoice,execute
from test_generic_session_win_proof import session,claim


def test_actual_win_claim_avoids_unrelated_frontier_and_executes(monkeypatch):
    from generic_chess.session.session import GameSession
    current=session(claim(0,'WIN'));before=current.to_record()
    def forbidden(self):raise AssertionError('unused board frontier')
    monkeypatch.setattr(GameSession,'legal_actions',forbidden)
    result=prove_session_win_pn(current,max_depth=1,seconds=3.)
    assert result.status=='PROVEN_WIN' and result.nodes==2 and result.transitions==1 and result.frontiers==1
    assert current.to_record()==before and verify_session_certificate(current,result.certificate,seconds=3.)['verified']
    cursor=SessionStrategyCursor(current,result.certificate,seconds=3.)
    assert cursor.commit(current,cursor.choose(current)).winner==0


@pytest.mark.parametrize('outcome',['WIN','RESTART'])
def test_actual_defender_claim_refutes_forced_win(outcome):
    current=session(claim(1,outcome),k=0,b=2,r=10,turn=1)
    result=prove_session_win_pn(current,target=0,max_depth=8,seconds=3.)
    assert result.status=='UNKNOWN' and result.certificate is None and result.transitions==1
    assert current.result.status is SessionStatus.ONGOING


def test_complete_loss_claim_and_board_defenses_independently_replay_and_execute():
    current=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    result=prove_session_win_pn(current,target=0,max_nodes=65536,max_depth=8,seconds=3.)
    assert result.status=='PROVEN_WIN' and verify_session_certificate(current,result.certificate,max_nodes=65536,seconds=3.)['verified']
    assert len(result.certificate.tree.edges)==len(current.legal_actions())+1
    leaves=[]
    def walk(s,node):
        if not node.edges:assert s.result.winner==0;leaves.append(s.result.status);return
        for choice,child in node.edges:
            branch=copy(s);execute(branch,choice);walk(branch,child)
    walk(current,result.certificate.tree)
    assert SessionStatus.DECLARATION in leaves and SessionStatus.CHECKMATE in leaves
    omitted=replace(result.certificate.tree,edges=result.certificate.tree.edges[1:])
    assert not verify_session_certificate(current,replace(result.certificate,tree=omitted),seconds=3.)['verified']


@pytest.mark.parametrize('max_nodes,max_depth',[(0,8),(1,8),(4096,0),(4096,1)])
def test_caps_remain_unknown_not_a_draw_or_partial_certificate(max_nodes,max_depth):
    current=session(k=0,b=2,r=10,turn=1);before=current.to_record()
    result=prove_session_win_pn(current,target=0,max_nodes=max_nodes,max_depth=max_depth,seconds=3.)
    assert result.status=='UNKNOWN' and result.certificate is None and result.nodes<=max_nodes
    assert current.to_record()==before


@pytest.mark.parametrize('mode',['cancel','time'])
def test_cancel_after_actual_claim_cannot_publish_partial_frontier(monkeypatch,mode):
    from scripts import generic_session_win_proof_pn as m
    current=session(claim(0,'WIN'));record=current.to_record();flag=[False];clock=[0.];original=m.execute
    def crossing(*args):
        terminal=original(*args);flag[0]=True;clock[0]=2.;return terminal
    monkeypatch.setattr(m,'execute',crossing)
    result=prove_session_win_pn(current,seconds=1.,cancel=(lambda:flag[0]) if mode=='cancel' else None,_clock=lambda:clock[0])
    assert result.status=='UNKNOWN' and result.reason==('cancelled' if mode=='cancel' else 'time_budget')
    assert result.certificate is None and current.to_record()==record


def test_actual_terminal_session_is_reported_without_a_new_proof():
    current=session(claim(0,'WIN'));current.declare('claim')
    result=prove_session_win_pn(current,seconds=3.)
    assert result.status=='ALREADY_TERMINAL' and result.certificate is None and result.nodes==0
