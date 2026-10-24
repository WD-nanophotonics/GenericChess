"""One opt-in hard-clock-cap comparison against already paid default controls."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    p=L.load(d/'plan.json');data=L.load(Path(p['inputs']))
    assert hashlib.sha256(Path(p['inputs']).read_bytes()).hexdigest()==p['inputs_sha256']
    for name,h in p['source_hashes'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
    assert not(d/'receipt.json').exists()and not(d/'queries.jsonl').exists()
    reference=Path('.local_agent/clock-completion-panel-20261025');assert L.load(reference/'receipt.json')['status']=='CLOSED'
    tick=time.perf_counter();cpu=time.process_time();begin=stamp();original=S.negamax;attempted=0;calls=0;status='FAILED'
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()or now-tick>p['batch_seconds']
            return self.flag
    try:
        for key in p['slots']:
            if Stop().is_cancelled():raise RuntimeError('stop/batch; missing UNKNOWN')
            case=next(x for x in data['cases']if x['key']==key);c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
            player=AlphaBetaPlayer(c,use_disk_cache=False,cap_pure_leaper_rule_clock=True);root=[];its=[]
            def observe(*args,**kw):
                r=original(*args,**kw)
                if args[4]==0:root[:]=[r]
                return r
            S.negamax=observe;start=stamp();qt=time.perf_counter();qc=time.process_time()
            def progress(depth,nodes,qnodes):
                r=root[0];it=dict(depth=depth,nodes=nodes,qnodes=qnodes,score=r.score,action=L.record_value(r.best_action),elapsed=time.perf_counter()-qt);its.append(it);append(d/'iterations.jsonl',dict(key=key,**it))
            attempted+=1;dec=player.choose_action(s,SearchLimits(**p['limits']),cancel_token=Stop(),progress_callback=progress);end=stamp()
            append(d/'queries.jsonl',dict(key=key,started_at=start,query_ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,actual_opt_in=True,actual_clock_depth_cap=player.last_rule_clock_cap,remaining=case['remaining'],state_sha256=case['state_sha256']))
            calls+=1;assert L.state_sha(s.state)==case['state_sha256'];print('RULECLOCK',key,case['remaining'],dec.completed_depth,dec.score,round(time.perf_counter()-qt,4),flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc(),attempted=attempted,returns=calls));raise
    finally:
        S.negamax=original;write_json(d/'receipt.json',dict(status=status,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,attempted=attempted,queries=calls,source_hashes=p['source_hashes']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);run(a.parse_args().directory)
