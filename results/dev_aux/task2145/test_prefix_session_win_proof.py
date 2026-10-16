import sys
from pathlib import Path
sys.path.insert(0,str(Path("tests").resolve()))
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
    for sq,p in [(k,Piece(0,'K','K')),(b,Piece(1,'K','K')),(r-1 if turn else r,Piece(0,'R','R'))]:board[sq]=p
    rs=replace(rs,initial_position=tuple(tuple(board[y:y+4]) for y in range(0,16,4)),declarations=tuple(declarations))
    current=GameSession(compile_ruleset(rs))
    if turn:
        from scripts.generic_proof_rnb_bridge import uci
        move=chr(97+(r-1)%4)+str((r-1)//4+1)+chr(97+r%4)+str(r//4+1)
        current.submit(next(a for a in current.legal_actions() if uci(a)==move))
    return current


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
    expected=prove_session_win(plain,target=0,max_depth=8,max_nodes=65536,seconds=3.)
    assert expected.status=='PROVEN_WIN'
    guarded=session(claim(1,'RESTART'),k=0,b=2,r=10,turn=1)
    got=prove_session_win(guarded,target=0,max_depth=8,max_nodes=65536,seconds=3.)
    assert got.status=='UNKNOWN' and got.certificate is None
    # A copied board-only tree with altered root binding still omits a real defense.
    forged=replace(expected.certificate,ruleset_fingerprint=guarded.compiled.ruleset_fingerprint,root_record=guarded.to_record(),root_state=guarded.state)
    assert not verify_session_certificate(guarded,forged,max_nodes=65536,seconds=3.)['verified']
    before=guarded.state;out=execute(guarded,SessionChoice('DECLARATION',declaration_id='claim'))
    assert out.winner is None and out.declaration_outcome=='RESTART' and guarded.state==before


def test_loss_claim_is_real_defender_choice_and_prover_covers_it():
    s=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    result=prove_session_win(s,target=0,max_depth=8,max_nodes=65536,seconds=3.)
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


def test_bool_int_record_alias_and_forged_declaration_winner_fail_binding():
    s=session(claim(0,'WIN'));cert=prove_session_win(s,max_depth=1,seconds=3.).certificate
    alias=replace(cert,root_record=replace(cert.root_record,schema_version=True))
    assert alias.root_record==cert.root_record
    assert not verify_session_certificate(s,alias)['verified']
    choice,leaf=cert.tree.edges[0]
    forged=replace(leaf,terminal=replace(leaf.terminal,winner=False))
    assert forged.terminal==leaf.terminal
    bad=replace(cert,tree=replace(cert.tree,edges=((choice,forged),)))
    assert not verify_session_certificate(s,bad)['verified']


def test_complete_defensive_strategy_physically_executes_every_claim_and_board_reply():
    s=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    cert=prove_session_win(s,target=0,max_depth=8,max_nodes=65536,seconds=3.).certificate
    assert cert is not None;wins=[]
    def walk(record,node):
        current=GameSession.replay(s.compiled,record)
        if not node.edges:
            assert current.result.winner==0;wins.append(current.result.status.value);return
        if current.state.position.side_to_move==0:assert len(node.edges)==1
        # Execute all actual covered defender choices, target's single proved move.
        for choice,child in node.edges:
            branch=GameSession.replay(s.compiled,record)
            execute(branch,choice);assert child.rank<node.rank
            walk(branch.to_record(),child)
    walk(s.to_record(),cert.tree)
    assert 'declaration' in wins and 'checkmate' in wins
    assert s.result.status is SessionStatus.ONGOING


def test_promotion_choice_executes_real_session_and_retains_base_type():
    from conftest import T,king_type,make_ruleset
    from generic_chess.core.movement import LeapAtom,RayAtom
    rook=T('R',*(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',))
    rs=make_ruleset(4,[king_type(),rook,pawn],lines=['...k','P...','..K.','....'],auto_promotion=True)
    current=GameSession(compile_ruleset(rs));result=prove_session_win(current,max_nodes=4096,seconds=3.,max_depth=1)
    assert result.status=='PROVEN_WIN'
    cursor=SessionStrategyCursor(current,result.certificate,seconds=3.);choice=cursor.choose(current)
    assert choice.kind=='ACTION' and choice.action.promotion_target_id=='R'
    terminal=cursor.commit(current,choice);piece=current.state.position.board[12]
    assert terminal.winner==0 and piece.base_type_id=='P' and piece.current_type_id=='R' and piece.promoted


def test_real_no_progress_draw_does_not_become_empty_defender_win():
    from generic_chess.rules.schema import RuleNoProgressDraw
    rs=replace(krk_ruleset(4),max_ply=4,no_progress_draw=RuleNoProgressDraw(1,True))
    current=GameSession(compile_ruleset(rs));out=prove_session_win(current,max_nodes=4096,seconds=3.,max_depth=3)
    assert out.status=='UNKNOWN' and out.certificate is None
    # A real public move triggers the history rule; the result is not a proof cutoff.
    found=False
    for action in current.legal_actions():
        child=GameSession.replay(current.compiled,current.to_record());child.submit(action)
        if child.result.status is SessionStatus.NO_PROGRESS_DRAW:
            found=True;assert child.result.winner is None
    assert found


def test_unreplayable_import_is_explicitly_rejected_not_fresh_history_reset():
    from scripts.generic_proof_fixtures import krk_state
    current=session(claim(0,'WIN'));different=krk_state(current.compiled,0,15,10,0)
    # Test-only corruption demonstrates admission rejection, never used in execution.
    current._state=different
    result=prove_session_win(current,seconds=3.)
    assert result.status=='UNKNOWN' and result.reason=='unsupported_or_unreplayable_session'


def test_selected_initial_setup_and_terminal_declaration_record_are_bound():
    from generic_chess.rules.schema import RuleInitialSetupOption
    rs=krk_ruleset(4);board=[None]*16
    for sq,p in [(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(8,Piece(0,'R','R'))]:board[sq]=p
    alt=tuple(tuple(board[i:i+4]) for i in range(0,16,4))
    rs=replace(rs,declarations=(claim(0,'WIN'),),initial_setup_options=(RuleInitialSetupOption('alternate',alt),))
    current=GameSession(compile_ruleset(rs),'alternate')
    result=prove_session_win(current,max_depth=1,seconds=3.);assert result.status=='PROVEN_WIN'
    assert result.certificate.root_record.schema_version==3
    assert result.certificate.root_record.initial_setup_key=='alternate'
    cursor=SessionStrategyCursor(current,result.certificate,seconds=3.)
    cursor.commit(current,cursor.choose(current))
    record=current.to_record();assert record.schema_version==3 and record.declaration is not None
    assert GameSession.replay(current.compiled,record).result==current.result


def test_defender_winning_claim_cannot_be_treated_as_only_a_board_defense():
    current=session(claim(1,'WIN'),k=0,b=2,r=10,turn=1)
    before=current.to_record()
    result=prove_session_win(current,target=0,max_depth=8,max_nodes=65536,seconds=3.)
    assert result.status=='UNKNOWN' and result.certificate is None
    assert current.to_record()==before and current.result.status is SessionStatus.ONGOING
    end=execute(current,SessionChoice('DECLARATION',declaration_id='claim'))
    assert end.winner==1 and end.declaration_outcome=='WIN'


def test_immediate_claim_avoids_board_frontier_in_prover_and_independent_verifier(monkeypatch):
    current=session(claim(0,'WIN'))
    def unexpected_frontier(self):
        raise AssertionError('unrelated board frontier requested before actual WIN claim')
    monkeypatch.setattr(GameSession,'legal_actions',unexpected_frontier)
    result=prove_session_win(current,max_depth=1,seconds=3.)
    assert result.status=='PROVEN_WIN'
    assert verify_session_certificate(current,result.certificate,seconds=3.)['verified']
    cursor=SessionStrategyCursor(current,result.certificate,seconds=3.)
    assert cursor.commit(current,cursor.choose(current)).winner==0


@pytest.mark.parametrize('declaration_id',['missing','opponent'])
def test_single_target_claim_is_independently_validated_by_public_declare(declaration_id):
    current=session(claim(0,'WIN'),claim(1,'WIN','opponent'))
    cert=prove_session_win(current,max_depth=1,seconds=3.).certificate
    _,leaf=cert.tree.edges[0]
    forged=replace(cert,tree=replace(cert.tree,edges=((SessionChoice('DECLARATION',declaration_id=declaration_id),leaf),)))
    assert not verify_session_certificate(current,forged,seconds=3.)['verified']
    assert current.result.status is SessionStatus.ONGOING


def test_single_target_board_choice_still_requires_actual_public_legality():
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    current=session(claim(0,'WIN'))
    cert=prove_session_win(current,max_depth=1,seconds=3.).certificate
    _,leaf=cert.tree.edges[0]
    illegal=SessionChoice('ACTION',action=BoardMove(Square(0,0),Square(0,1)))
    forged=replace(cert,tree=replace(cert.tree,edges=((illegal,leaf),)))
    assert not verify_session_certificate(current,forged,seconds=3.)['verified']
    assert current.result.status is SessionStatus.ONGOING


@pytest.mark.parametrize('mode',['cancel','time'])
def test_deferred_board_frontier_crossing_budget_cannot_issue_certificate(monkeypatch,mode):
    current=session(k=1,b=3,r=8);record=current.to_record();flag=[False];clock=[0.]
    original=GameSession.legal_actions
    def crossing(self):
        actions=original(self);flag[0]=True;clock[0]=2.;return actions
    monkeypatch.setattr(GameSession,'legal_actions',crossing)
    result=prove_session_win(current,max_depth=1,seconds=1.,cancel=(lambda:flag[0]) if mode=='cancel' else None,_clock=lambda:clock[0])
    assert result.status=='UNKNOWN' and result.reason==('cancelled' if mode=='cancel' else 'time_budget')
    assert result.certificate is None and current.to_record()==record


def test_defender_frontier_cancellation_prevents_partial_verifier_acceptance(monkeypatch):
    current=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    cert=prove_session_win(current,target=0,max_depth=8,seconds=3.,max_nodes=65536).certificate
    flag=[False];original=GameSession.legal_actions;record=current.to_record()
    def crossing(self):
        actions=original(self);flag[0]=True;return actions
    monkeypatch.setattr(GameSession,'legal_actions',crossing)
    receipt=verify_session_certificate(current,cert,seconds=3.,cancel=lambda:flag[0])
    assert not receipt['verified'] and receipt['reason']=='cancelled'
    assert receipt['session_transitions']==0 and current.to_record()==record

from results.dev_aux.task2145.verify import verify_prefix_session_certificate as verify_session_certificate,PrefixSessionStrategyCursor as SessionStrategyCursor
