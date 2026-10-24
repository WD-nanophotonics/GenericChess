"""One full remaining-clock endpoint query using the existing searcher, not a graph solver."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    plan=L.load(d/'plan.json');inp=L.load(d/'input.json');case=inp['case']
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==plan['source_sha256']
    assert hashlib.sha256((d/'input.json').read_bytes()).hexdigest()==plan['input_sha256']
    assert not(d/'receipt.json').exists()and not(d/'query.json').exists()
    c=L.compile_rule(L.ruleset_from_dict(inp['rules'][case['rule_sha256']]))
    sess=replay(c,case['record']);assert L.state_sha(sess.state)==case['state_sha256']
    assert c.max_ply-sess.state.ply_count==case['remaining']==plan['limits']['max_depth']==4
    player=AlphaBetaPlayer(c,use_disk_cache=False);original=S.negamax;root=[];its=[];ctxs=[]
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:self.last=now;self.flag=stopped()
            return self.flag
    def observe(*args,**kw):
        r=original(*args,**kw)
        if args[4]==0:root[:]=[r];ctxs[:]=[args[5]]
        return r
    begin=stamp();tick=time.perf_counter();cpu=time.process_time();status='FAILED'
    def progress(depth,nodes,qnodes):
        r=root[0];its.append(dict(depth=depth,nodes=nodes,qnodes=qnodes,score=r.score,action=L.record_value(r.best_action),evaluation_calls=ctxs[0].stats.evaluation_calls))
    try:
        S.negamax=observe;dec=player.choose_action(sess,SearchLimits(**plan['limits']),cancel_token=Stop(),progress_callback=progress)
        end=stamp();write_json(d/'query.json',dict(started_at=begin,ended_at=end,seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,decision=L.record_value(dec),iterations=its,root_static=player._evaluator.evaluate(sess.state),scope=inp['scope']))
        assert L.state_sha(sess.state)==case['state_sha256']
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc(),iterations=its));raise
    finally:
        S.negamax=original;write_json(d/'receipt.json',dict(status=status,attempted=1,queries=int((d/'query.json').exists()),started_at=begin,ended_at=stamp(),source_sha256=plan['source_sha256']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);run(p.parse_args().directory)
