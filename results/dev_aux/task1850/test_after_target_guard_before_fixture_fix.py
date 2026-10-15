"""Real Session cache integrity, unknown semantics and physical accounting."""
from dataclasses import replace
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof import SessionProofResult
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from test_generic_session_win_proof import session,claim


def counting():
    calls=[]
    def solver(*a,**kw):
        calls.append(1)
        return prove_session_win_pn(*a,**kw)
    return SessionLogicalProofBank(solver),calls


def test_real_verified_win_reused_without_recharging_physical_proof():
    s=session(claim(0,'WIN'));bank,calls=counting();root=s.to_record()
    a=bank.query(s,max_depth=2,seconds=3.)
    assert not a.hit and a.stored and a.logical_result.status=='PROVEN_WIN'
    assert a.actual_proof_nodes==2 and a.actual_verification_nodes>0 and a.verification['verified']
    a.verification['verified']=False
    b=bank.query(s,max_depth=2,seconds=3.)
    assert b.hit and b.actual_proof_nodes==b.actual_verification_nodes==0
    assert b.logical_result.nodes==2 and b.verification['verified'] and len(calls)==1
    assert s.to_record()==root and not hasattr(b,'nodes') and not hasattr(b,'status')


def test_completed_unknown_remains_unknown_on_hit():
    s=GameSession(compile_ruleset_for_execution(replace(krk_ruleset(4),max_ply=1)))
    bank,calls=counting()
    a=bank.query(s,max_nodes=65536,max_depth=2,seconds=3.)
    b=bank.query(s,max_nodes=65536,max_depth=2,seconds=3.)
    assert a.logical_result.status==b.logical_result.status=='UNKNOWN'
    assert a.logical_result.reason=='no_forced_win_in_exhausted_tree'
    assert a.stored and b.hit and len(calls)==1 and b.logical_result.certificate is None


def test_node_cap_unknown_has_exact_virtual_and_physical_counts():
    s=session();bank,calls=counting()
    a=bank.query(s,max_nodes=1,seconds=3.);b=bank.query(s,max_nodes=1,seconds=3.)
    assert a.logical_result.reason==b.logical_result.reason=='node_budget'
    assert a.actual_proof_nodes==a.logical_result.nodes==b.logical_result.nodes==1
    assert b.actual_proof_nodes==0 and b.hit and len(calls)==1


@pytest.mark.parametrize('reason',['time_budget','cancelled','depth_budget','unsupported_or_unreplayable_session'])
def test_incomplete_or_unsupported_response_never_cached(reason):
    calls=[]
    def incomplete(*args,**kwargs):
        calls.append(1);return SessionProofResult('UNKNOWN',None,reason,1,0.,0)
    bank=SessionLogicalProofBank(incomplete);s=session()
    for _ in range(2):
        q=bank.query(s,seconds=3.);assert not q.stored and not q.hit and q.logical_result.status=='UNKNOWN'
    assert len(calls)==2


def test_bad_certificate_cannot_enter_bank():
    s=session(claim(0,'WIN'));good=prove_session_win_pn(s,seconds=3.)
    bad=replace(good,certificate=replace(good.certificate,target=1))
    bank=SessionLogicalProofBank(lambda *a,**k:bad)
    for _ in range(2):
        q=bank.query(s,seconds=3.)
        assert not q.hit and not q.stored and not q.verification['verified']


def test_cancelled_hit_never_returns_a_cached_win():
    s=session(claim(0,'WIN'));bank,_=counting();assert bank.query(s,seconds=3.).stored
    q=bank.query(s,seconds=3.,cancel=lambda:True)
    assert not q.hit and q.logical_result.status=='UNKNOWN' and q.logical_result.reason=='cancelled'


def test_full_actual_played_record_target_and_budgets_have_separate_keys():
    s=session();bank,_=counting()
    assert bank.query(s,max_nodes=1,seconds=3.).stored
    for kw in (dict(max_nodes=2),dict(target=1),dict(max_depth=9),dict(seconds=4.)):
        args=dict(max_nodes=1,seconds=3.);args.update(kw)
        assert not bank.query(s,**args).hit
    s.submit(s.legal_actions()[0])
    assert not bank.query(s,max_nodes=1,seconds=3.).hit


def test_bounded_lru_eviction_and_parameter_validation():
    s=session();bank=SessionLogicalProofBank(capacity=1)
    assert bank.query(s,target=0,max_nodes=1,seconds=3.).stored
    assert bank.query(s,target=1,max_nodes=1,seconds=3.).stored
    assert not bank.query(s,target=0,max_nodes=1,seconds=3.).hit
    with pytest.raises(ValueError):SessionLogicalProofBank(capacity=0)


def test_cancellation_during_independent_verification_preserves_cost_no_entry(monkeypatch):
    import scripts.generic_session_proof_bank as m
    actual=m.verify_session_certificate;flag=[False]
    def crossed(*a,**kw):
        out=actual(*a,**kw);flag[0]=True;return out
    monkeypatch.setattr(m,'verify_session_certificate',crossed)
    s=session(claim(0,'WIN'));bank=SessionLogicalProofBank()
    q=bank.query(s,seconds=3.,cancel=lambda:flag[0])
    assert q.logical_result.status=='UNKNOWN' and q.logical_result.reason=='cancelled'
    assert not q.stored and q.actual_proof_nodes==2 and q.actual_verification_nodes>0


def test_valid_other_target_certificate_is_not_a_requested_target_win():
    from scripts.generic_session_win_proof import verify_session_certificate
    s=session(claim(0,'WIN'));actual=prove_session_win_pn(s,target=0,seconds=3.)
    assert verify_session_certificate(s,actual.certificate,seconds=3.)['verified']
    bank=SessionLogicalProofBank(lambda *a,**k:actual)
    q=bank.query(s,target=1,seconds=3.)
    assert q.logical_result.status=='UNKNOWN' and q.logical_result.reason=='certificate_target_mismatch'
    assert not q.stored and not q.hit and q.actual_proof_nodes==actual.nodes
