"""Predeclared repair-first falsifier; no automatic large panel after a failed pilot."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_forced_quiet_q import ForcedQuietQ
from scripts.leaper_forced_branch_depth import ForcedBranchDepth
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    p=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(Path(__file__))==p['source_sha256'] and sha(Path(p['policy_source']))==p['policy_sha256'] and sha(d/'inputs.json')==p['inputs_sha256']
    assert L.load(Path(p['prior_branch_receipt']))['status']=='CLOSED','no concurrent producer'
    assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists(),'no refill'
    assert set(p['keys']) <= {x['key']for x in data['cases']}, 'all keys must bind before any query'
    tick=time.perf_counter();begin=stamp();oq=S.negamax;attempted=0;calls=0;status='FAILED'
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()or now-tick>p['batch_seconds']
            return self.flag
    try:
        for key in p['keys']:
            if Stop().is_cancelled():raise RuntimeError('stop/batch; missing UNKNOWN')
            case=next(x for x in data['cases']if x['key']==key);c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
            sess=replay(c,case['record']);assert L.state_sha(sess.state)==case['state_sha256']
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());roots=[];its=[]
            def observe(*args,**kw):
                r=impl(*args,**kw)
                if args[4]==0:roots[:]=[r]
                return r
            start=stamp();qt=time.perf_counter();qc=time.process_time()
            def progress(depth,nodes,qnodes):
                r=roots[0];it=dict(depth=depth,score=r.score,action=L.record_value(r.best_action),nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt);its.append(it);append(d/'iterations.jsonl',dict(key=key,**it))
            with (ForcedBranchDepth() if p['policy']=='forced_main_branch_depth' else ForcedQuietQ())as policy:
                impl=S.negamax;S.negamax=observe
                try:
                    attempted+=1;dec=player.choose_action(sess,SearchLimits(**p['limits']),cancel_token=Stop(),progress_callback=progress)
                finally:S.negamax=impl
            end=stamp();row=dict(key=key,started_at=start,ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,policy_counts=dict(policy.counts),state_sha256=L.state_sha(sess.state),tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile))
            append(d/'queries.jsonl',row);calls+=1
            assert row['state_sha256']==case['state_sha256']
            matches=[x for x in case['labelled_actions']if x['action']==L.record_value(dec.action)]
            value=matches[0]['truth']['value']if len(matches)==1 else None
            pv=replay(c,case['record']);steps=0
            for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a);steps+=1
            append(d/'qualification.jsonl',dict(key=key,chosen_global_WDL=value,root_global_WDL=case['root_global_WDL'],preserves=value==case['root_global_WDL'],pv_steps=steps))
            print('FORCED',key,dec.completed_depth,dec.score,value,dict(policy.counts),round(row['seconds'],3),flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc(),attempted=attempted,queries=calls));raise
    finally:
        S.negamax=oq;write_json(d/'receipt.json',dict(status=status,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=calls,source_sha256=p['source_sha256'],policy_sha256=p['policy_sha256']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);run(a.parse_args().directory)
