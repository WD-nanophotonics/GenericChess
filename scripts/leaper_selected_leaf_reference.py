"""Two full remaining-clock Player references at observed q frontier histories."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

class LocalStop:
    """Bound stop-file transport overhead; never alters search's own time cap."""
    def __init__(self,deadline,clock=time.perf_counter,stop=stopped):self.deadline=deadline;self.clock=clock;self.stop=stop;self.last=float('-inf');self.flag=False
    def is_cancelled(self):
        now=self.clock()
        if now-self.last>=.25:self.last=now;self.flag=self.stop()or now>=self.deadline
        return self.flag

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(d):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    p=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(__file__)==p['source_sha256']and sha(d/'inputs.json')==p['inputs_sha256'];assert not(d/'queries.jsonl').exists()and not(d/'receipt.json').exists()
    tick=time.perf_counter();start=stamp();attempted=0;count=0;status='FAILED'
    cancel=LocalStop(tick+p['batch_seconds'])
    try:
        for b in p['branches']:
            if cancel.is_cancelled():raise RuntimeError('role/batch stop')
            leaf=data['leaves'][str(b)];c=L.compile_rule(L.ruleset_from_dict(data['ruleset']));s=replay(c,leaf['child_record'])
            for a in leaf['actions']:s.submit(L.match_action(s,a))
            assert L.state_sha(s.state)==leaf['state_sha256']and c.max_ply-s.state.ply_count==leaf['remaining']==4
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());ts=stamp();qt=time.perf_counter();attempted+=1;decision=player.choose_action(s,SearchLimits(**p['limits']),cancel_token=cancel);te=stamp()
            row=dict(branch=b,started_at=ts,ended_at=te,seconds=time.perf_counter()-qt,decision=L.record_value(decision),state_sha256=L.state_sha(s.state),tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile));append(d/'queries.jsonl',row);count+=1
            pv=replay(c,leaf['child_record'])
            for a in leaf['actions']:pv.submit(L.match_action(pv,a))
            for a in decision.principal_variation:pv.submit(a)
            append(d/'qualification.jsonl',dict(branch=b,pv_steps=len(decision.principal_variation),PV_result=L.record_value(pv.result),complete_clock=decision.completed_depth>=leaf['remaining'],leaf_actor=s.state.position.side_to_move))
            print('LEAF',b,decision.completed_depth,decision.score,decision.termination_reason,round(row['seconds'],4),flush=True)
        status='CLOSED'
    except Exception:write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc()));raise
    finally:write_json(d/'receipt.json',dict(status=status,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=p['source_sha256']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);run(p.parse_args().directory)
