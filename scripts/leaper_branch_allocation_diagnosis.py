"""Cold equal-allocation complete-history child diagnostics; no policy modification."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, time, traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'))

def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    p=L.load(d/'plan.json'); data=L.load(d/'inputs.json')
    assert sha(Path(__file__))==p['source_sha256'] and sha(d/'inputs.json')==p['inputs_sha256']
    for name,digest in p['backend_sources'].items(): assert sha(Path(name))==digest
    assert not(d/'receipt.json').exists() and not(d/'queries.jsonl').exists(), 'no refill'
    c=L.compile_rule(L.ruleset_from_dict(data['ruleset']));case=data['root']
    root=replay(c,case['record']);assert L.state_sha(root.state)==case['state_sha256']
    actions=sorted(root.legal_actions(),key=lambda a:canonical(L.record_value(a)))
    assert [L.record_value(a)for a in actions]==data['actions']
    tick=time.perf_counter();beg=stamp();original=S.negamax;count=0;attempted=0;status='FAILED'
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped() or now-tick>=p['batch_seconds']
            return self.flag
    try:
        for slot in p['slots']:
            if Stop().is_cancelled():raise RuntimeError('stopped/batch cap: missing slots UNKNOWN')
            s=replay(c,case['record']);a=actions[slot['branch']];s.submit(a)
            assert L.state_sha(s.state)==data['children'][slot['branch']]['state_sha256']
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());roots=[];its=[]
            def observe(*args,**kw):
                r=original(*args,**kw)
                if args[4]==0:roots[:]=[r]
                return r
            S.negamax=observe;start=stamp();qt=time.perf_counter();qc=time.process_time()
            def progress(depth,nodes,qnodes):
                r=roots[0];it=dict(depth=depth,score=r.score,nodes=nodes,qnodes=qnodes,action=L.record_value(r.best_action),elapsed=time.perf_counter()-qt)
                its.append(it);append(d/'iterations.jsonl',dict(slot=slot,**it))
            attempted+=1
            dec=player.choose_action(s,SearchLimits(**slot['limits']),cancel_token=Stop(),progress_callback=progress)
            end=stamp();row=dict(slot=slot,started_at=start,ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,child_state_sha256=L.state_sha(s.state),actual_tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile))
            append(d/'queries.jsonl',row);count+=1
            assert row['child_state_sha256']==data['children'][slot['branch']]['state_sha256']
            pv=replay(c,data['children'][slot['branch']]['record']);steps=0
            for action in dec.principal_variation:
                assert action in pv.legal_actions();pv.submit(action);steps+=1
            append(d/'qualification.jsonl',dict(slot=slot,pv_steps=steps,result=L.record_value(pv.result)))
            print('BRANCH',slot['phase'],slot['branch'],'D',dec.completed_depth,'score',dec.score,dec.termination_reason,round(row['seconds'],3),flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),attempted=attempted,returns=count,traceback=traceback.format_exc()));raise
    finally:
        S.negamax=original
        write_json(d/'receipt.json',dict(status=status,started_at=beg,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=p['source_sha256']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);run(a.parse_args().directory)
