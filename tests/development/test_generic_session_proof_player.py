"""Actual Session integration controls; no fake rule outcomes or Native engine."""
from copy import copy
from dataclasses import replace
import pytest
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_proof_player import SessionProofMaterialPlayer,commit_session_decision
from scripts.generic_session_win_proof import SessionChoice,SessionStrategyCursor,execute
from scripts.generic_win_proof import _Interrupted
from test_generic_session_win_proof import session,claim


def material(position,target):
    return sum((1 if p.owner==target else -1)*({'R':5}.get(p.current_type_id,0))
               for p in position.board if p is not None)


def player(s,**kw):return SessionProofMaterialPlayer(s.compiled,material,**kw)


def test_real_claim_choice_executes_once_and_terminal_is_session_only():
    s=session(claim(0,'WIN'));p=player(s);q=player(s);before=s.state
    d=p.choose(s,max_nodes=4096,seconds=3.)
    assert d.source=='PROOF' and d.choice.kind=='DECLARATION'
    assert s.result.status is SessionStatus.ONGOING
    out=commit_session_decision(s,d,[p,q])
    assert out.winner==0 and out.declaration_outcome=='WIN' and s.state==before
    assert p.cursor.node.rank==0 and len(s.to_record().actions)==0
    assert GameSession.replay(s.compiled,s.to_record()).result==out
    assert p.choose(s,seconds=3.).source=='TERMINAL'
    with pytest.raises(ValueError):commit_session_decision(s,d,[p,q])


def test_unknown_retains_actual_normal_legal_move_and_full_record():
    s=session();p=player(s,proof_depth=0,max_depth=1);record=s.to_record()
    d=p.choose(s,max_nodes=4096,seconds=3.)
    assert d.proof_reason=='depth_budget' and d.source=='MATERIAL_SEARCH'
    assert d.choice.action in s.legal_actions() and d.normal_receipt is not None
    assert d.normal_receipt.proof_nodes==0 and d.search_nodes==d.normal_receipt.nodes
    assert d.nodes<=4096 and s.to_record()==record
    commit_session_decision(s,d,[p]);assert len(s.to_record().actions)==1
    replay=GameSession.replay(s.compiled,s.to_record());assert replay.state==s.state


def test_two_player_observers_follow_every_actual_defense_without_double_commit():
    # Root belongs to defender; a verified target0 strategy covers all replies.
    s=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    from scripts.generic_session_win_proof_pn import prove_session_win_pn
    cert=prove_session_win_pn(s,target=0,max_depth=8,max_nodes=65536,seconds=3.).certificate
    assert cert is not None
    terminals=[]
    def walk(record,node):
        current=GameSession.replay(s.compiled,record)
        if not node.edges:
            assert current.result.winner==0;terminals.append(current.result.status);return
        for choice,child in node.edges:
            branch=GameSession.replay(s.compiled,record)
            p=player(branch);q=player(branch)
            # Both observers are independently bound to this subtree via the
            # original verified root, then advanced along the real prefix.
            p.cursor=SessionStrategyCursor(s,cert,max_nodes=65536,seconds=3.)
            q.cursor=SessionStrategyCursor(s,cert,max_nodes=65536,seconds=3.)
            prefix=GameSession.replay(s.compiled,s.to_record())
            # Follow the stored path carried by recursive traversal.
            for previous in paths[record]:
                before=copy(prefix);execute(prefix,previous)
                p.observe(before,previous,prefix);q.observe(before,previous,prefix)
            assert p.cursor.node==node and q.cursor.node==node
            before_record=branch.to_record()
            # Ordinary defender action selected publicly; no invented winner.
            d=replace(p.choose(branch,max_nodes=0,seconds=3.),choice=choice,
                      root_record=before_record,root_state=branch.state,root_result=branch.result)
            commit_session_decision(branch,d,[p,q])
            assert p.cursor.node==child and q.cursor.node==child
            assert len(branch.to_record().actions)==len(before_record.actions)+(choice.kind=='ACTION')
            if branch.result.status is SessionStatus.ONGOING and branch.state.position.side_to_move==0:
                selected=p.choose(branch,max_nodes=0,seconds=3.)
                assert selected.source=='PROOF_CONTINUATION' and selected.choice==child.edges[0][0]
            paths[branch.to_record()]=paths[record]+[choice]
            walk(branch.to_record(),child)
    paths={s.to_record():[]};walk(s.to_record(),cert.tree)
    assert SessionStatus.DECLARATION in terminals and SessionStatus.CHECKMATE in terminals
    assert s.result.status is SessionStatus.ONGOING


def test_cursor_observation_rejects_wrong_post_record_without_mutation():
    s=session(claim(0,'WIN'));p=player(s);d=p.choose(s,seconds=3.)
    node=p.cursor.node;before=copy(s);wrong=copy(s);wrong.submit(wrong.legal_actions()[0])
    with pytest.raises(ValueError):p.cursor.observe(before,d.choice,wrong)
    assert p.cursor.node==node and p.cursor.record==s.to_record()
    p.observe(before,d.choice,wrong);assert p.cursor is None


def test_cancel_before_choose_or_commit_cannot_mutate_or_dispatch():
    s=session(claim(0,'WIN'));p=player(s);record=s.to_record()
    d=p.choose(s,seconds=3.,cancel=lambda:True)
    assert d.choice is None and d.exit_cause=='cancelled'
    d=p.choose(s,seconds=3.)
    with pytest.raises(_Interrupted):commit_session_decision(s,d,[p],cancel=lambda:True)
    assert s.to_record()==record and p.cursor.node.rank==1


def test_normal_atomic_return_cancel_clears_choice_and_preserves_actual_receipt():
    s=session();flag=[False]
    def normal(state,nodes,seconds,cancel):
        # Run the actual bounded material search before requesting cancellation.
        real=player(s,proof_enabled=False,max_depth=1).normal.choose(state,max_nodes=nodes,seconds=seconds)
        flag[0]=True;return real.action,real.nodes
    p=player(s,proof_enabled=False,normal_search=normal)
    d=p.choose(s,seconds=3.,cancel=lambda:flag[0])
    assert d.choice is None and d.exit_cause=='cancelled' and d.search_nodes>0
    assert len(s.to_record().actions)==0


def test_unreplayable_and_wrong_rules_are_rejected_without_history_reset():
    s=session();p=player(s);other=session(claim(0,'WIN'))
    with pytest.raises(ValueError):p.choose(other,seconds=3.)
    from scripts.generic_proof_fixtures import krk_state
    s._state=krk_state(s.compiled,0,15,10,0)
    with pytest.raises(ValueError):p.choose(s,seconds=3.)

@pytest.mark.parametrize('boundary',['admission','verification','continuation'])
def test_cancel_after_real_atomic_session_boundaries_cannot_dispatch(monkeypatch,boundary):
    import scripts.generic_session_proof_player as m
    s=session(claim(0,'WIN'));p=player(s);flag=[False];record=s.to_record()
    if boundary=='admission':
        original=m.replay_bound
        def crossing(current):
            out=original(current);flag[0]=True;return out
        monkeypatch.setattr(m,'replay_bound',crossing)
    elif boundary=='verification':
        original=m.SessionStrategyCursor
        def crossing(*args,**kw):
            out=original(*args,**kw);flag[0]=True;return out
        monkeypatch.setattr(m,'SessionStrategyCursor',crossing)
    else:
        assert p.choose(s,seconds=3.).source=='PROOF'
        original=p.cursor.choose
        def crossing(current):
            out=original(current);flag[0]=True;return out
        monkeypatch.setattr(p.cursor,'choose',crossing)
    got=p.choose(s,seconds=3.,cancel=lambda:flag[0])
    assert got.choice is None and got.exit_cause=='cancelled' and s.to_record()==record


def test_completed_normal_deadline_result_is_legal_and_cost_not_clipped():
    s=session();clock=[0.]
    def normal(state,nodes,seconds,cancel):
        real=player(s,proof_enabled=False,max_depth=1).normal.choose(state,max_nodes=nodes,seconds=3.)
        clock[0]=2.;return real.action,nodes+7
    p=player(s,proof_enabled=False,normal_search=normal)
    d=p.choose(s,max_nodes=64,seconds=1.,_clock=lambda:clock[0])
    assert d.exit_cause=='time_budget' and d.choice.action in s.legal_actions()
    assert d.search_nodes==71 and d.normal_receipt.search_nodes==71 and d.seconds==2.
    assert s.result.status is SessionStatus.ONGOING


def test_budget_allocation_and_normal_no_hidden_proof(monkeypatch):
    import scripts.generic_session_proof_player as m
    original=m.prove_session_win_pn;calls=[]
    def proof(current,**kw):
        calls.append((kw['max_nodes'],kw['seconds']));return original(current,**kw)
    s=session();p=player(s,proof_search=proof,proof_depth=0)
    d=p.choose(s,max_nodes=64,seconds=4.)
    assert len(calls)==1 and calls[0][0]==16 and 0<calls[0][1]<=1.
    assert d.proof_nodes==1 and d.verification_nodes==0 and d.search_nodes<=63
    assert not p.normal.proof_enabled and d.normal_receipt.proof_nodes==0


def test_capture_hand_drop_mate_through_chooser_and_broadcast():
    from test_generic_session_proof_mechanisms import layout,played
    from scripts.generic_proof_fixtures import krk_ruleset
    from generic_chess.core.pieces import Piece
    from generic_chess.core.actions import DropMove
    rs=replace(krk_ruleset(4),drop_allowed={'R':((True,)*16,)*2},capture_disposition='capture_to_hand')
    rs=layout(rs,[(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,'R','R'))])
    s=played(rs,['a2a3','d1d2']);p=player(s);q=player(s);record=s.to_record()
    d=p.choose(s,max_nodes=4096,seconds=3.)
    assert d.source=='PROOF' and isinstance(d.choice.action,DropMove)
    out=commit_session_decision(s,d,[p,q]);assert out.winner==0 and out.status is SessionStatus.CHECKMATE
    assert len(s.to_record().actions)==len(record.actions)+1 and len(s.state.history)==4
    assert GameSession.replay(s.compiled,s.to_record()).state==s.state


def test_real_no_progress_terminal_is_not_unknown_or_material_win():
    from generic_chess.rules.schema import RuleNoProgressDraw
    from scripts.generic_proof_fixtures import krk_ruleset
    from generic_chess.rules.compiler import compile_ruleset
    s=GameSession(compile_ruleset(replace(krk_ruleset(4),no_progress_draw=RuleNoProgressDraw(1,True))))
    p=player(s,proof_depth=0,max_depth=1)
    d=p.choose(s,max_nodes=64,seconds=3.)
    assert d.choice is not None
    out=commit_session_decision(s,d,[p]);assert out.status is SessionStatus.NO_PROGRESS_DRAW and out.winner is None
    stopped=p.choose(s,seconds=3.);assert stopped.source=='TERMINAL' and stopped.choice is None

@pytest.mark.parametrize('kind',['declaration','action'])
def test_cancel_during_real_atomic_commit_returns_actual_result_and_advances_observers(monkeypatch,kind):
    if kind=='declaration':s=session(claim(0,'WIN'))
    else:s=session(k=1,b=3,r=8)
    p=player(s);q=player(s);d=p.choose(s,max_nodes=4096,seconds=3.)
    assert d.source=='PROOF';q.cursor=SessionStrategyCursor(s,p.cursor.certificate,seconds=3.)
    flag=[False];method='declare' if kind=='declaration' else 'submit';original=getattr(GameSession,method);actual=[0]
    def crossing(current,*args):
        out=original(current,*args)
        if current is s:actual[0]+=1;flag[0]=True
        return out
    monkeypatch.setattr(GameSession,method,crossing)
    before=s.to_record();out=commit_session_decision(s,d,[p,q],cancel=lambda:flag[0])
    assert flag[0] and actual[0]==1 and out.winner==0
    assert p.cursor.node.rank==q.cursor.node.rank==0
    assert len(s.to_record().actions)==len(before.actions)+(kind=='action')
    if kind=='declaration':assert s.to_record().declaration is not None
    with pytest.raises(ValueError):commit_session_decision(s,d,[p,q])
    assert actual[0]==1 and GameSession.replay(s.compiled,s.to_record()).result==out


def test_horizon_disables_new_proof_but_keeps_verified_strategy(monkeypatch):
    import scripts.generic_session_proof_player as m
    s=session(claim(0,'WIN'));p=player(s)
    first=p.choose(s,seconds=3.);assert first.source=='PROOF'
    def forbidden(*args,**kw):raise AssertionError('new proof after closed horizon')
    p.proof_search=forbidden
    continuation=p.choose(s,seconds=3.,allow_new_proof=False)
    assert continuation.source=='PROOF_CONTINUATION' and continuation.choice==first.choice
    assert continuation.proof_nodes==continuation.verification_nodes==0
    fresh=player(s);fresh.proof_search=forbidden
    fallback=fresh.choose(s,max_nodes=64,seconds=3.,allow_new_proof=False)
    assert fallback.choice.kind=='ACTION' and fallback.proof_reason=='new_proof_disabled'
    assert fallback.proof_nodes==fallback.verification_nodes==0

@pytest.mark.parametrize('proof_depth',[0,1])
def test_phase_cost_receipts_cover_actual_calls_without_changing_node_allocation(proof_depth):
    s=session(claim(0,'WIN')) if proof_depth else session()
    p=player(s,proof_depth=proof_depth,max_depth=1)
    d=p.choose(s,max_nodes=4096,seconds=3.)
    parts=[d.admission_seconds,d.proof_seconds,d.verification_seconds,d.normal_seconds]
    assert all(x>=0 for x in parts) and sum(parts)<=d.seconds+.000001
    assert d.admission_seconds>0 and d.proof_seconds>0
    if proof_depth:
        assert d.source=='PROOF' and d.verification_seconds>0 and d.normal_seconds==0
    else:
        assert d.verification_seconds==0 and d.normal_seconds==d.normal_receipt.seconds>0
    assert d.nodes==d.proof_nodes+d.verification_nodes+d.search_nodes<=4096
