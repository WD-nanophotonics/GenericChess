"""Actual Session/cache/player integration, paid checks and deadline controls."""
from dataclasses import replace
import pytest
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_proof_player import commit_session_decision
from test_generic_session_win_proof import session, claim


def player(s, **kw):
    return SessionCachedPhasePlayer(s.compiled, lambda p,t:0, **kw)


def test_miss_and_hit_pay_current_verification_and_single_actual_commit():
    s=session(claim(0,'WIN'));bank=SessionLogicalProofBank(prove_session_win_batch_pn)
    p=player(s,bank=bank);a=p.choose(s,seconds=2.75)
    b=player(s,bank=bank).choose(s,seconds=2.75)
    assert a.source==b.source=='PROOF' and a.choice==b.choice
    assert not a.bank_hit and a.bank_stored and b.bank_hit
    assert a.proof_nodes==a.logical_proof_nodes==b.logical_proof_nodes==2
    assert b.proof_nodes==0 and dict(b.proof_stats)['transitions']==0
    assert dict(b.logical_proof_stats)['transitions']>0
    assert a.fill_verification_nodes>0 and b.fill_verification_nodes==0
    assert a.verification_nodes==b.verification_nodes>0
    assert b.bank_verification_scope=='HISTORICAL_SAME_LIMITS'
    assert a.nodes==a.proof_nodes+a.fill_verification_nodes+a.verification_nodes
    assert commit_session_decision(s,a,[p]).winner==0
    with pytest.raises(ValueError):commit_session_decision(s,a,[p])


def test_unknown_hit_never_becomes_terminal_and_normal_keeps_full_cap():
    s=session();bank=SessionLogicalProofBank(prove_session_win_batch_pn);seen=[]
    def normal(state,n,seconds,cancel):
        seen.append((n,seconds));return s.legal_actions()[0],n
    kw=dict(bank=bank,normal_search=normal,limits=PhaseLimits(proof_nodes=1))
    a=player(s,**kw).choose(s,max_nodes=64)
    b=player(s,**kw).choose(s,max_nodes=64)
    assert a.logical_reason==b.logical_reason=='node_budget'
    assert b.logical_status=='UNKNOWN' and b.bank_hit and b.proof_nodes==0
    assert a.source==b.source=='EXTERNAL_SEARCH' and s.result.winner is None
    assert seen[0][0]==seen[1][0]==64 and all(0<t<=.1 for n,t in seen)
    assert a.nodes==65 and b.nodes==64


def test_actual_failed_fill_check_cannot_install_cursor_or_enter_bank():
    s=session(claim(0,'WIN'));bank=SessionLogicalProofBank(prove_session_win_batch_pn)
    for _ in range(2):
        p=player(s,bank=bank,limits=PhaseLimits(verification_nodes=0))
        d=p.choose(s,max_nodes=64)
        assert d.source!='PROOF' and p.cursor is None and not d.bank_stored and not d.bank_hit
        assert d.proof_reason=='bank_fill_verification_node_budget'
        assert d.logical_status=='PROVEN_WIN' and d.proof_nodes==2
        assert d.verification_nodes==d.fill_verification_nodes==0


def test_warm_hit_still_runs_actual_current_verifier_and_can_fail(monkeypatch):
    import scripts.generic_session_phase_player as m
    actual=m.SessionStrategyCursor;s=session(claim(0,'WIN'))
    bank=SessionLogicalProofBank(prove_session_win_batch_pn)
    assert player(s,bank=bank).choose(s).source=='PROOF'
    seen=[]
    def zero_current(*a,**kw):
        seen.append(kw);kw['max_nodes']=0
        return actual(*a,**kw)
    monkeypatch.setattr(m,'SessionStrategyCursor',zero_current)
    p=player(s,bank=bank);d=p.choose(s,max_nodes=64)
    assert d.bank_hit and len(seen)==1 and d.source!='PROOF'
    assert d.proof_reason=='verification_node_budget' and p.cursor is None
    assert d.bank_verification_scope=='HISTORICAL_SAME_LIMITS'


def test_total_deadline_during_fill_has_no_free_adoption_or_extra_normal(monkeypatch):
    import scripts.generic_session_proof_bank as m
    actual=m.verify_session_certificate;clock=[0.];s=session(claim(0,'WIN'))
    def crossed(*a,**kw):
        out=actual(*a,**kw);clock[0]=3.;return out
    monkeypatch.setattr(m,'verify_session_certificate',crossed)
    p=player(s);d=p.choose(s,seconds=2.75,_clock=lambda:clock[0])
    assert d.choice is None and d.exit_cause=='time_budget' and p.cursor is None
    assert not d.bank_stored and d.fill_verification_nodes>0 and d.proof_nodes>0
    assert d.search_nodes==d.verification_nodes==0


def test_user_cancel_during_fill_preserves_cost_but_no_choice(monkeypatch):
    import scripts.generic_session_proof_bank as m
    actual=m.verify_session_certificate;flag=[False];s=session(claim(0,'WIN'))
    def crossed(*a,**kw):
        out=actual(*a,**kw);flag[0]=True;return out
    monkeypatch.setattr(m,'verify_session_certificate',crossed)
    d=player(s).choose(s,cancel=lambda:flag[0])
    assert d.choice is None and d.exit_cause=='cancelled' and not d.bank_stored
    assert d.proof_nodes>0 and d.fill_verification_nodes>0
    assert dict(d.proof_stats).get('frontiers',0)>0
    assert dict(d.proof_stats).get('transitions',0)==d.proof_nodes-1


def test_continuation_uses_existing_checked_cursor_and_observes_other_writer():
    from copy import copy
    from scripts.generic_session_win_proof import SessionStrategyCursor,execute
    s=session(k=0,b=2,r=10,turn=1);p=player(s)
    r=prove_session_win_batch_pn(s,target=0,max_nodes=65536,max_depth=8,seconds=3.)
    p.cursor=SessionStrategyCursor(s,r.certificate,seconds=3.)
    before=copy(s);choice=p.cursor.node.edges[0][0]
    execute(s,choice);p.observe(before,choice,s)
    d=p.choose(s,allow_new_proof=False)
    assert d.source=='PROOF_CONTINUATION' and d.logical_status=='NOT_QUERIED'
    assert d.proof_nodes==d.fill_verification_nodes==d.verification_nodes==0


def test_cancel_before_lookup_and_zero_total_do_not_access_bank():
    s=session(claim(0,'WIN'));p=player(s)
    a=p.choose(s,cancel=lambda:True);b=p.choose(s,seconds=0.)
    assert a.choice is b.choice is None and a.exit_cause=='cancelled' and b.exit_cause=='time_budget'
    assert a.logical_status==b.logical_status=='NOT_QUERIED' and not p.bank._entries


def test_disabled_proof_and_new_proof_horizon_do_not_consult_bank():
    s=session(claim(0,'WIN'))
    a=player(s,proof_enabled=False).choose(s,max_nodes=8)
    b=player(s).choose(s,max_nodes=8,allow_new_proof=False)
    assert a.logical_status==b.logical_status=='NOT_QUERIED'
    assert b.proof_reason=='new_proof_disabled' and a.proof_reason=='disabled'


def test_reentrant_player_rejected_and_exception_clears_context():
    s=session();p=player(s)
    p._query_context=1.
    with pytest.raises(ValueError):p.choose(s)
    p._query_context=None
    with pytest.raises(ValueError):p.choose(s,seconds=-1.)
    assert p._query_context is None
