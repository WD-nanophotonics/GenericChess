"""One predeclared exposed clock-shield ablation, no production activation."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import nullcontext
import argparse,hashlib,inspect,json,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_last_clock_shield import LastClockShield
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
    p=L.load(d/'plan.json');inp=Path(p['inputs']);data=L.load(inp)
    assert sha(inp)==p['inputs_sha256'] and sha(Path(__file__))==p['source_sha256']
    assert sha(Path('scripts/leaper_last_clock_shield.py'))==p['policy_sha256']
    assert hashlib.sha256(inspect.getsource(S._quiescence_runtime).encode()).hexdigest()==p['original_q_sha256']
    assert L.load(Path('.local_agent/qorder-prospective-20261025/receipt.json'))['status']=='CLOSED'
    assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists(),'no refill'
    tick=time.perf_counter();cpu=time.process_time();begin=stamp();original=S.negamax;attempted=0;calls=0;status='FAILED'
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()or now-tick>p['batch_seconds']
            return self.flag
    try:
        for slot in p['slots']:
            if Stop().is_cancelled():raise RuntimeError('stop/batch; missing slots UNKNOWN')
            case=next(x for x in data['cases']if x['key']==slot['key']);c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
            s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());root=[];its=[]
            def observe(*args,**kw):
                r=original(*args,**kw)
                if args[4]==0:root[:]=[r]
                return r
            S.negamax=observe;qt=time.perf_counter();qc=time.process_time();beg=stamp()
            def progress(depth,nodes,qnodes):
                r=root[0];it=dict(depth=depth,nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt,score=r.score,action=L.record_value(r.best_action));its.append(it);append(d/'iterations.jsonl',dict(slot=slot,**it))
            policy=LastClockShield() if slot['shield']else None
            attempted+=1
            with policy if policy is not None else nullcontext():
                dec=player.choose_action(s,SearchLimits(**p['limits']),cancel_token=Stop(),progress_callback=progress)
            end=stamp();seconds=time.perf_counter()-qt
            # Save actual return before any truth or legality qualification.
            row=dict(slot=slot,started_at=beg,query_ended_at=end,seconds=seconds,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,policy_counts=dict(policy.counts)if policy else{},policy='last_clock_noncheck_no_neutral_alllegal'if policy else'original',actual_tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile),state_sha256=case['state_sha256'])
            append(d/'queries.jsonl',row);calls+=1
            assert L.state_sha(s.state)==case['state_sha256']
            print('SHIELD',slot,'D',dec.completed_depth,dec.score,dec.termination_reason,round(seconds,3),row['policy_counts'],flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc(),attempted=attempted,returns=calls));raise
    finally:
        S.negamax=original
        write_json(d/'receipt.json',dict(status=status,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,attempted=attempted,queries=calls,source_sha256=p['source_sha256'],policy_sha256=p['policy_sha256']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);run(a.parse_args().directory)
