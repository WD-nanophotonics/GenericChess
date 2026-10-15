"""Separate real proof/normal budgets and actual single-writer phase policy."""
import pytest
from scripts.generic_session_phase_player import SessionPhasePlayer,PhaseLimits
from scripts.generic_session_proof_player import commit_session_decision
from test_generic_session_win_proof import session,claim


def player(s,**kw):return SessionPhasePlayer(s.compiled,lambda pos,target:0,**kw)


def test_unknown_real_node_cap_does_not_steal_normal_nodes_or_seconds():
    s=session();seen=[]
    def normal(state,n,seconds,cancel):
        seen.append((n,seconds));return s.legal_actions()[0],n
    p=player(s,normal_search=normal,limits=PhaseLimits(proof_nodes=1,normal_seconds=.07))
    d=p.choose(s,max_nodes=64,seconds=2.25)
    assert d.proof_nodes==1 and d.search_nodes==64 and seen[0][0]==64
    assert 0<seen[0][1]<=.07 and d.choice is not None
    assert dict(d.phase_limits)['normal_nodes']==64 and d.nodes==65
    assert dict(d.proof_stats)['eager_board_successors']>0


def test_actual_win_requires_verification_and_commits_once():
    s=session(claim(0,'WIN'));p=player(s);d=p.choose(s,max_nodes=64,seconds=3.)
    assert d.source=='PROOF' and d.proof_nodes==2 and d.verification_nodes>0
    assert commit_session_decision(s,d,[p]).winner==0 and p.cursor.node.rank==0
    with pytest.raises(ValueError):commit_session_decision(s,d,[p])


def test_failed_real_verifier_uses_full_frozen_normal_budget():
    s=session(claim(0,'WIN'));seen=[]
    def normal(state,n,seconds,cancel):
        seen.append(n);return s.legal_actions()[0],n
    p=player(s,normal_search=normal,limits=PhaseLimits(verification_nodes=0))
    d=p.choose(s,max_nodes=64,seconds=3.)
    assert d.source=='EXTERNAL_SEARCH' and d.proof_reason.startswith('verification_')
    assert d.proof_nodes==2 and d.verification_nodes==0 and seen==[64]
    assert p.cursor is None


def test_total_zero_and_cancel_stop_before_normal():
    s=session();p=player(s)
    a=p.choose(s,max_nodes=64,seconds=0.)
    b=p.choose(s,max_nodes=64,seconds=3.,cancel=lambda:True)
    assert a.choice is None and a.exit_cause=='time_budget'
    assert b.choice is None and b.exit_cause=='cancelled'


def test_normal_atomic_cancel_preserves_paid_nodes_and_discards_action():
    s=session();flag=[False]
    def normal(state,n,seconds,cancel):
        action=s.legal_actions()[0];flag[0]=True;return action,n+1
    p=player(s,proof_enabled=False,normal_search=normal);root=s.to_record()
    d=p.choose(s,max_nodes=64,seconds=3.,cancel=lambda:flag[0])
    assert d.choice is None and d.exit_cause=='cancelled' and d.search_nodes==65
    assert s.to_record()==root


def test_horizon_disables_new_proof_even_with_large_separate_cap():
    s=session(claim(0,'WIN'));p=player(s)
    def forbidden(*a,**k):raise AssertionError('new proof after frozen horizon')
    p.proof_search=forbidden
    d=p.choose(s,max_nodes=64,seconds=3.,allow_new_proof=False)
    assert d.proof_reason=='new_proof_disabled' and d.proof_nodes==0 and d.source!='PROOF'


def test_proof_continuation_observes_other_physical_writer():
    from scripts.generic_session_win_proof import SessionStrategyCursor
    from scripts.generic_session_win_proof_pn import prove_session_win_pn
    s=session(k=0,b=2,r=10,turn=1);p=player(s)
    r=prove_session_win_pn(s,target=0,max_nodes=65536,max_depth=8,seconds=3.)
    assert r.certificate
    p.cursor=SessionStrategyCursor(s,r.certificate,seconds=3.)
    # p controls target0; observer tracks the defender's actual move too.
    from copy import copy
    before=copy(s);choice=p.cursor.node.edges[0][0]
    from scripts.generic_session_win_proof import execute
    execute(s,choice);p.observe(before,choice,s)
    def forbidden(*a,**k):raise AssertionError('continuation reproved')
    p.proof_search=forbidden
    d=p.choose(s,max_nodes=64,seconds=3.,allow_new_proof=False)
    assert d.source=='PROOF_CONTINUATION' and d.proof_nodes==0


def test_phase_caps_validate_without_changing_old_chooser_contract():
    for kw in (dict(proof_nodes=-1),dict(proof_nodes=True),dict(normal_seconds=-1.),dict(proof_seconds=float('inf'))):
        with pytest.raises(ValueError):PhaseLimits(**kw)
