"""Actual two-callback first-ordinary-Q consumer, paired across all frozen histories."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import nullcontext
import argparse,hashlib,json,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_first_q_refinement import FirstQRefinement
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    p=L.load(d/'plan.json');data=L.load(d/'inputs.json')
    assert sha(Path(__file__))==p['source_sha256']and sha(Path('scripts/leaper_first_q_refinement.py'))==p['policy_sha256']and sha(d/'inputs.json')==p['inputs_sha256']
    assert L.load(Path(p['guard_receipt']))['status']=='CLOSED','no second producer'
    assert not(d/'receipt.json').exists()and not(d/'queries.jsonl').exists(),'no refill'
    cases={c['key']:c for c in data['cases']};assert set(p['keys'])==set(cases)and len(p['keys'])==64
    oq=S.negamax;tick=time.perf_counter();begin=stamp();attempted=0;count=0;status='FAILED'
    try:
        for index,key in enumerate(p['keys']):
            for arm in (['default','refined']if index%2==0 else['refined','default']):
                if stopped()or time.perf_counter()-tick>p['batch_seconds']:raise RuntimeError('role/batch stop; missing slots UNKNOWN')
                case=cases[key];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
                player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());roots=[];stages=[];its=[]
                class Cancel:
                    last=0.;role=False;first_cancel_elapsed=None
                    def is_cancelled(self):
                        now=time.perf_counter()
                        if now-self.last>.25:self.last=now;self.role=stopped()or now-tick>p['batch_seconds']
                        cancel=self.role or len(its)>=2
                        if cancel and self.first_cancel_elapsed is None:self.first_cancel_elapsed=now-qt
                        return cancel
                def observe(*args,**kw):
                    reserve=args[5].first_main_iteration_complete is False;r=oq(*args,**kw)
                    if args[4]==0:roots[:]=[r];stages[:]=[0 if reserve else args[5].qdepth_limit]
                    return r
                def progress(dep,n,qn):
                    r=roots[0];its.append(dict(depth=dep,ordinary_qdepth=stages[0],score=r.score,action=L.record_value(r.best_action),nodes=n,qnodes=qn,elapsed=time.perf_counter()-qt))
                start=stamp();qt=time.perf_counter();qc=time.process_time();cancel=Cancel();S.negamax=observe;policy=FirstQRefinement()if arm=='refined'else None
                try:
                    with policy if policy is not None else nullcontext():
                        attempted+=1;dec=player.choose_action(s,SearchLimits(**p['limits']),cancel_token=cancel,progress_callback=progress)
                finally:S.negamax=oq
                end=stamp();row=dict(key=key,arm=arm,started_at=start,ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,state_sha256=L.state_sha(s.state),policy_counts=dict(policy.counts)if policy else{},tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile),cancel_observed_seconds=cancel.first_cancel_elapsed,returned_source=dec.result_source)
                row['cancel_to_return_seconds']=None if cancel.first_cancel_elapsed is None else row['seconds']-cancel.first_cancel_elapsed
                append(d/'queries.jsonl',row);count+=1
                assert row['state_sha256']==case['state_sha256']
                labels={json.dumps(x['action'],sort_keys=True):x['truth']['value']for x in case['labelled_actions']};value=labels[json.dumps(L.record_value(dec.action),sort_keys=True)]
                pv=replay(c,case['record']);steps=0
                for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a);steps+=1
                strong=dec.result_source in ['root_immediate_win','root_declaration','terminal']
                append(d/'qualification.jsonl',dict(key=key,arm=arm,chosen_global_WDL=value,correct=value==case['root_global_WDL'],ordinary_goal_complete=strong or any(i['ordinary_qdepth']==4 for i in its),pv_steps=steps,PV_result=L.record_value(pv.result)))
            print('FIRST-ORDINARY',index+1,key,flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),attempted=attempted,returns=count,traceback=traceback.format_exc()));raise
    finally:
        S.negamax=oq;write_json(d/'receipt.json',dict(status=status,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=p['source_sha256'],policy_sha256=p['policy_sha256']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);run(a.parse_args().directory)
