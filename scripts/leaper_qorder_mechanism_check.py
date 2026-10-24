"""One frozen lexical-versus-existing-q-order diagnostic on two metadata roots."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import argparse,hashlib,json,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    plan=L.load(d/'plan.json');inp=Path(plan['inputs']);data=L.load(inp)
    assert hashlib.sha256(inp.read_bytes()).hexdigest()==plan['inputs_sha256']
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==plan['source_sha256']
    assert L.load(Path(plan['preceding_panel'])/'receipt.json')['status']=='CLOSED'
    assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists()
    began=stamp();tick=time.perf_counter();cpu=time.process_time();original=S.negamax;calls=0;status='FAILED'
    class Stop:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:
                self.last=now;self.flag=stopped()or now-tick>=plan['batch_seconds']
            return self.flag
    try:
        for slot in plan['slots']:
            if Stop().is_cancelled():raise RuntimeError('stop/batch deadline: missing slots UNKNOWN')
            case=next(x for x in data['cases']if x['key']==slot['key'])
            c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
            sess=replay(c,case['record']);assert L.state_sha(sess.state)==case['state_sha256']
            def label(raw):return next(x['truth']['value']for x in case['labelled_actions']if x['action']==raw)
            tuning=SearchTuning(use_ordered_qsearch=slot['ordered'])
            p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=tuning);probe=p._tt.probe
            stack=[];counts=Counter();depth_delta=Counter();root=[];its=[]
            def tracked_probe(key):
                entry=probe(key);counts['probes']+=1
                assert stack,'all default probe calls must belong to negamax'
                depth,alpha,beta,ply,ctx=stack[-1]
                if entry is not None:
                    counts['hits']+=1;depth_delta[str(entry.depth-depth)]+=1
                    if entry.depth>=depth:
                        counts['depth_eligible']+=1;counts['eligible_'+entry.bound.name]+=1
                        assert not ctx.tuning.require_full_pv
                return entry
            p._tt.probe=tracked_probe
            def observe(*args,**kwargs):
                stack.append(args[1:6])
                try:r=original(*args,**kwargs)
                finally:stack.pop()
                if args[4]==0:root[:]=[(args[1],r)]
                return r
            S.negamax=observe;begin=stamp();qt=time.perf_counter();qc=time.process_time()
            def progress(depth,nodes,qnodes):
                assert root[0][0]==depth;r=root[0][1]
                it=dict(depth=depth,nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt,score=r.score,action=L.record_value(r.best_action),chosen_global_WDL=label(L.record_value(r.best_action)),TT=dict(counts))
                its.append(it);append(d/'iterations.jsonl',dict(slot=slot,**it))
            dec=p.choose_action(sess,SearchLimits(**plan['limits']),cancel_token=Stop(),progress_callback=progress)
            ended=stamp();seconds=time.perf_counter()-qt
            assert counts['probes']==dec.tt_probes and counts['hits']==dec.tt_hits
            assert L.state_sha(sess.state)==case['state_sha256'] and not stack
            leaf=replay(c,case['record'])
            for a in dec.principal_variation:assert a in leaf.legal_actions();leaf.submit(a)
            row=dict(slot=slot,started_at=begin,query_ended_at=ended,ended_at=stamp(),query_seconds=seconds,outer_seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,decision=L.record_value(dec),iterations=its,tuning=L.record_value(tuning),root_global_WDL=case['root_global_WDL'],chosen_global_WDL=label(L.record_value(dec.action)),TT=dict(counts),TT_depth_delta=dict(depth_delta),PV_final_result=L.record_value(leaf.result))
            append(d/'queries.jsonl',row);calls+=1
            print('QORDER',slot,'D',dec.completed_depth,'chosen',row['chosen_global_WDL'],'seconds',round(seconds,3),'TT',dict(counts),flush=True)
        status='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(when=stamp(),traceback=traceback.format_exc()));raise
    finally:
        S.negamax=original
        write_json(d/'receipt.json',dict(status=status,started_at=began,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,queries=calls,planned=len(plan['slots']),source_sha256=plan['source_sha256']))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);run(a.parse_args().directory)
