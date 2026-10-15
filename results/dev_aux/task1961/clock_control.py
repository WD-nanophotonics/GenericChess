"""One controlled-clock mechanism witness; actual certificate, no game reward."""
from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,str(Path('tests/development').resolve()))
from test_generic_session_win_proof import session,claim
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_proof_player import commit_session_decision
OUT=Path('results/dev_aux/task1961')
def run():
    clock=[0.];latency=[1.4];calls=[]
    s=session(claim(0,'WIN'));record=s.to_record()
    def delayed_actual_solver(current,**kw):
        result=prove_session_win_batch_pn(current,**kw)
        assert result.status=='PROVEN_WIN'
        assert verify_session_certificate(current,result.certificate,seconds=3.)['verified']
        calls.append(dict(status=result.status,nodes=result.nodes,charged_seconds=latency[0]))
        clock[0]+=latency[0]
        return result
    bank=SessionLogicalProofBank(delayed_actual_solver)
    limits=PhaseLimits(proof_nodes=4096,verification_nodes=16384,proof_seconds=1.5,verification_seconds=.5,normal_seconds=.1)
    def normal(state,n,seconds,cancel):return s.legal_actions()[0],1
    def choose(bank):
        clock[0]=0.
        p=SessionCachedPhasePlayer(s.compiled,lambda pos,side:0,bank=bank,normal_search=normal,limits=limits)
        d=p.choose(s,max_nodes=4096,seconds=2.75,_clock=lambda:clock[0])
        assert s.to_record()==record
        return p,d
    _,fill=choose(bank);assert fill.source=='PROOF' and fill.bank_stored
    latency[0]=1.6
    warm_p,warm=choose(bank)
    cold_p,cold=choose(SessionLogicalProofBank(delayed_actual_solver))
    assert warm.bank_hit and warm.source=='PROOF' and warm.verification_nodes>0
    assert not cold.bank_hit and cold.logical_status=='UNKNOWN' and cold.logical_reason=='time_budget'
    assert cold.source=='EXTERNAL_SEARCH' and cold.choice!=warm.choice
    # Actual public declaration executes; no theoretical WIN rewarded as a game.
    result=commit_session_decision(s,warm,[warm_p])
    assert result.winner==0
    out=dict(status='PASS',scope='CONTROLLED_CLOCK_NOT_EMPIRICAL_WDL_OR_TIMING',real_solver_calls=calls,
        root_unchanged_until_commit=True,actual_current_verification=True,actual_committed_winner=result.winner,
        explanation='Valid identical key warmed under shorter latency; slower cold actual solver crosses proof deadline while warm hit executes independently verified winning choice. New cold game/player prevents prior-game inheritance; OS latency simulated, not measured.',
        decisions=[dict(name=name,source=d.source,choice_kind=d.choice.kind,logical_status=d.logical_status,logical_reason=d.logical_reason,bank_hit=d.bank_hit,bank_stored=d.bank_stored,proof_nodes=d.proof_nodes,fill_verification_nodes=d.fill_verification_nodes,verification_nodes=d.verification_nodes,seconds=d.seconds) for name,d in [('fill',fill),('warm',warm),('cold',cold)]])
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps(out))
if __name__=='__main__':run()
