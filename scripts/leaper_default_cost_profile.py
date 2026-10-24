"""Single bounded profiler diagnostic, never a performance comparator."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,cProfile,hashlib,json,pstats,time
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json,ROOT
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    plan=L.load(d/'plan.json');data=L.load(Path(plan['inputs']))
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==plan['source_sha256']
    assert hashlib.sha256(Path(plan['inputs']).read_bytes()).hexdigest()==plan['inputs_sha256']
    assert L.load(Path(plan['previous'])/'receipt.json')['status']=='CLOSED'
    assert not(d/'receipt.json').exists(),'one diagnostic,no refill'
    case=next(c for c in data['cases']if c['key']==plan['key'])
    c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
    sess=replay(c,case['record']);assert L.state_sha(sess.state)==case['state_sha256']
    p=AlphaBetaPlayer(c,use_disk_cache=False);prof=cProfile.Profile()
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()
            return self.flag
    began=stamp();tick=time.perf_counter();cpu=time.process_time();status='FAILED'
    try:
        prof.enable()
        try:dec=p.choose_action(sess,SearchLimits(**plan['limits']),cancel_token=Stop())
        finally:prof.disable()
        ended=stamp();seconds=time.perf_counter()-tick;cpu_seconds=time.process_time()-cpu
        assert L.state_sha(sess.state)==case['state_sha256']
        chosen=next(a['truth']['value']for a in case['labelled_actions']if a['action']==L.record_value(dec.action))
        prof.dump_stats(str(d/'raw-private.pstats'))
        rows=[]
        for (fn,line,name),(primitive,total,selftime,cumulative,callers)in pstats.Stats(prof).stats.items():
            try:public_name=Path(fn).resolve().relative_to(ROOT.resolve()).as_posix()
            except (ValueError,OSError):public_name=Path(fn).name
            rows.append(dict(file=public_name,line=line,function=name,primitive_calls=primitive,total_calls=total,self_seconds=selftime,cumulative_seconds=cumulative))
        write_json(d/'profile.json',dict(status='PASS',started_at=began,query_ended_at=ended,query_seconds=seconds,cpu_seconds=cpu_seconds,key=case['key'],decision=L.record_value(dec),chosen_global_WDL=chosen,root_global_WDL=case['root_global_WDL'],function_rows=sorted(rows,key=lambda x:x['cumulative_seconds'],reverse=True),limitations='cProfile overhead changes throughput and reachable search; not an unprofiled latency estimate, quality comparator or completion of old frozen slots. Cumulative nested rows must not be summed. Native internal work appears only in calling boundary.'))
        status='CLOSED'
        print('PROFILE DONE',round(seconds,3),'D',dec.completed_depth,'WDL',chosen,flush=True)
    finally:write_json(d/'receipt.json',dict(status=status,started_at=began,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,queries=1 if status=='CLOSED'else 0))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);run(ap.parse_args().directory)
