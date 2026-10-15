from dataclasses import replace
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_win_proof import prove_win,CertificateVerificationError
from scripts.generic_public_win_proof import prove_win_public
from scripts.generic_session_win_proof import (prove_session_win,verify_session_certificate,SessionStrategyCursor,SessionChoice,SessionProofNode,execute)


def session(*declarations,k=1,b=3,r=8,turn=0):
    rs=krk_ruleset(4);board=[None]*16
    for sq,p in [(k,Piece(0,'K','K')),(b,Piece(1,'K','K')),(r,Piece(0,'R','R'))]:board[sq]=p
    rs=replace(rs,initial_position=tuple(tuple(board[y:y+4]) for y in range(0,16,4)),initial_side_to_move=turn,declarations=tuple(declarations))
    return GameSession(compile_ruleset(rs))


def claim(owner,outcome,id='claim',**kw):return RuleDeclaration(id,owner,require_not_in_check=False,failure_outcome=outcome,**kw)


def test_real_win_claim_is_typed_choice_and_physically_ends_session_only():
    s=session(claim(0,'WIN'));state=s.state;record=s.to_record()
    assert prove_win(s.compiled,state).reason=='unsupported_declarations'
    assert prove_win_public(s.compiled,state).reason=='unsupported_declarations'
    result=prove_session_win(s,max_depth=1,seconds=3.)
    assert result.status=='PROVEN_WIN' and result.certificate.tree.rank==1
    assert verify_session_certificate(s,result.certificate,seconds=3.)['verified']
    cur=SessionStrategyCursor(s,result.certificate,seconds=3.);choice=cur.choose(s)
    assert choice==SessionChoice('DECLARATION',declaration_id='claim')
    out=cur.commit(s,choice)
    assert out.status is SessionStatus.DECLARATION and out.winner==0 and out.declaration_outcome=='WIN'
    assert s.state==state and s.to_record()!=record and s.to_record().declaration is not None
    assert cur.node.rank==0 and GameSession.replay(s.compiled,s.to_record()).result==out


def test_defender_restart_refutes_board_only_win_and_cannot_be_omitted():
    plain=session(k=0,b=2,r=10,turn=1)
    expected=prove_session_win(plain,target=0,max_depth=5,max_nodes=65536,seconds=3.)
    assert expected.status=='PROVEN_WIN'
    guarded=session(claim(1,'RESTART'),k=0,b=2,r=10,turn=1)
    got=prove_session_win(guarded,target=0,max_depth=5,max_nodes=65536,seconds=3.)
    assert got.status=='UNKNOWN' and got.certificate is None
    # A copied board-only tree with altered root binding still omits a real defense.
    forged=replace(expected.certificate,ruleset_fingerprint=guarded.compiled.ruleset_fingerprint,root_record=guarded.to_record(),root_state=guarded.state)
    assert not verify_session_certificate(guarded,forged,max_nodes=65536,seconds=3.)['verified']
    before=guarded.state;out=execute(guarded,SessionChoice('DECLARATION',declaration_id='claim'))
    assert out.winner is None and out.declaration_outcome=='RESTART' and guarded.state==before


def test_loss_claim_is_real_defender_choice_and_prover_covers_it():
    s=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    result=prove_session_win(s,target=0,max_depth=5,max_nodes=65536,seconds=3.)
    assert result.status=='PROVEN_WIN'
    assert any(c.kind=='DECLARATION' for c,n in result.certificate.tree.edges)
    assert verify_session_certificate(s,result.certificate,seconds=3.,max_nodes=65536)['verified']
    # Removing even a losing legal defense violates the explicit certificate contract.
    tree=replace(result.certificate.tree,edges=tuple((c,n) for c,n in result.certificate.tree.edges if c.kind!='DECLARATION'))
    assert not verify_session_certificate(s,replace(result.certificate,tree=tree),seconds=3.)['verified']


def test_restart_or_loss_root_is_not_a_win_certificate():
    for outcome in ('RESTART','LOSS'):
        s=session(claim(0,outcome),k=0,b=15,r=10)
        # Real immediate declaration itself never receives a WIN reward.
        before=s.state;out=execute(s,SessionChoice('DECLARATION',declaration_id='claim'))
        assert out.winner!=(0) and s.state==before
        assert prove_session_win(s).status=='ALREADY_TERMINAL'


def test_changed_record_forged_rank_and_mixed_choice_rejected():
    s=session(claim(0,'WIN'));cert=prove_session_win(s,max_depth=1,seconds=3.).certificate
    bad=replace(cert,tree=replace(cert.tree,rank=0));assert not verify_session_certificate(s,bad)['verified']
    with pytest.raises(CertificateVerificationError):SessionStrategyCursor(s,bad)
    with pytest.raises(ValueError):execute(s,SessionChoice('DECLARATION',action=s.legal_actions()[0],declaration_id='claim'))
    cur=SessionStrategyCursor(s,cert,seconds=3.);s.submit(s.legal_actions()[0])
    with pytest.raises(ValueError):cur.choose(s)


def test_cancellation_after_public_claim_replay_cannot_issue_certificate(monkeypatch):
    import scripts.generic_session_win_proof as m
    s=session(claim(0,'WIN'));before=s.to_record();original=m.execute;flag=[False]
    def cancel_after(*args):
        out=original(*args);flag[0]=True;return out
    monkeypatch.setattr(m,'execute',cancel_after)
    got=prove_session_win(s,cancel=lambda:flag[0],max_depth=1,seconds=3.)
    assert got.status=='UNKNOWN' and got.reason=='cancelled' and got.certificate is None and s.to_record()==before
