"""Frozen two cold-child scalar dependency queries, no tree change or refill."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_scalar_dependency import ScalarDependencies
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(d):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert not(d/'receipt.json').exists()and not(d/'queries.jsonl').exists()
    assert sha(__file__)==plan['source_sha256']and sha(d/'inputs.json')==plan['inputs_sha256']
    for f,h in plan['dependencies'].items():assert sha(f)==h
    started=stamp();tick=time.perf_counter();attempted=0;calls=0;status='FAILED'
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()or now-tick>=plan['batch_seconds']
            return self.flag
    try:
        for branch in plan['branches']:
            if Cancel().is_cancelled():raise RuntimeError('role/batch stop; missing slots UNKNOWN')
            child=data['children'][str(branch)];c=L.compile_rule(L.ruleset_from_dict(data['ruleset']));s=replay(c,child['record']);assert L.state_sha(s.state)==child['state_sha256']
            p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());observer=ScalarDependencies(depths=(5,6));its=[]
            start=stamp();qt=time.perf_counter();qc=time.process_time()
            try:
                with observer:
                    attempted+=1;dec=p.choose_action(s,SearchLimits(**plan['limits']),cancel_token=Cancel(),progress_callback=lambda dep,n,qn:its.append(dict(depth=dep,nodes=n,qnodes=qn,elapsed=time.perf_counter()-qt)))
            except Exception:
                write_json(d/('partial-branch'+str(branch)+'.json'),dict(branch=branch,started_at=start,ended_at=stamp(),iterations=its,trace=observer.export()));raise
            end=stamp();row=dict(branch=branch,started_at=start,ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,state_sha256=L.state_sha(s.state),actual_tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(p.evaluation_profile))
            append(d/'queries.jsonl',row);calls+=1;write_json(d/('trace-branch'+str(branch)+'.json'),observer.export());assert row['state_sha256']==child['state_sha256']
            pv=replay(c,child['record']);steps=0
            for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a);steps+=1
            append(d/'qualification.jsonl',dict(branch=branch,pv_steps=steps,result=L.record_value(pv.result),complete=dec.completed_depth>=plan['limits']['max_depth']))
            print('SCALAR',branch,dec.completed_depth,dec.score,dec.termination_reason,round(row['seconds'],3),'trace roots',len(observer.records),flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc(),attempted=attempted,queries=calls));raise
    finally:write_json(d/'receipt.json',dict(status=status,started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=calls,source_sha256=plan['source_sha256']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
