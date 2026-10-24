"""Frozen default-only complete-history diagnostic; labels never enter search."""
from pathlib import Path
from datetime import datetime,timezone
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
    plan=L.load(d/'plan.json'); inp=Path(plan['inputs']); data=L.load(inp)
    assert hashlib.sha256(inp.read_bytes()).hexdigest()==plan['inputs_sha256']
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==plan['source_sha256']
    assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists(),'no refill/restart'
    assert [c['key']for c in data['cases']]==plan['slots']
    started=stamp(); tick=time.perf_counter(); cpu=time.process_time(); original=S.negamax; calls=0; state='FAILED'
    class Stop:
        last=0.; flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:
                self.last=now;self.flag=stopped() or datetime.now(timezone.utc)>=datetime.fromisoformat(plan['deadline'])
            return self.flag
    try:
        for case in data['cases']:
            if Stop().is_cancelled():raise RuntimeError('stop/deadline: remaining slots UNKNOWN')
            c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
            sess=replay(c,case['record']); assert L.state_sha(sess.state)==case['state_sha256']
            labels=case['labelled_actions']; legal=sess.legal_actions()
            assert sorted(json.dumps(L.record_value(a),sort_keys=True)for a in legal)==sorted(json.dumps(x['action'],sort_keys=True)for x in labels)
            def label(a):return next(x['truth']['value']for x in labels if x['action']==L.record_value(a))
            tuning=SearchTuning(); p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=tuning)
            root=[]; its=[]; begin=stamp(); qt=time.perf_counter(); qc=time.process_time()
            def observe(*args,**kwargs):
                r=original(*args,**kwargs)
                if args[4]==0:root[:]=[(args[1],r)]
                return r
            S.negamax=observe
            def progress(depth,nodes,qnodes):
                assert root and root[0][0]==depth
                r=root[0][1]; v=label(r.best_action)
                it=dict(depth=depth,nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt,score=r.score,action=L.record_value(r.best_action),chosen_global_WDL=v,preserves_root_value=v==case['root_global_WDL'])
                its.append(it); append(d/'iterations.jsonl',dict(key=case['key'],**it))
            limits=SearchLimits(**plan['limits'])
            dec=p.choose_action(sess,limits,cancel_token=Stop(),progress_callback=progress)
            query_end=stamp(); qseconds=time.perf_counter()-qt; qcpu=time.process_time()-qc
            assert L.state_sha(sess.state)==case['state_sha256']
            chosen=label(dec.action); pv=replay(c,case['record'])
            for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
            row=dict(key=case['key'],actor=case['actor'],state_sha256=case['state_sha256'],root_global_WDL=case['root_global_WDL'],chosen_global_WDL=chosen,preserves_root_value=chosen==case['root_global_WDL'],started_at=begin,query_ended_at=query_end,ended_at=stamp(),query_seconds=qseconds,cpu_seconds=qcpu,outer_seconds=time.perf_counter()-qt,decision=L.record_value(dec),iterations=its,tuning=L.record_value(tuning),evaluation_profile=L.record_value(p.evaluation_profile),native_availability=p.native_legality_provider.availability_metrics,PV_final_result=L.record_value(pv.result))
            append(d/'queries.jsonl',row);calls+=1
            print('PANEL',calls,case['key'],'root/chosen',case['root_global_WDL'],chosen,'D',dec.completed_depth,'seconds',round(qseconds,3),flush=True)
        state='CLOSED'
    except Exception:
        write_json(d/'failure.json',dict(when=stamp(),traceback=traceback.format_exc(),next_key=case['key']if 'case'in locals()else None));raise
    finally:
        S.negamax=original
        write_json(d/'receipt.json',dict(status=state,started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,queries=calls,planned=len(plan['slots']),source_sha256=plan['source_sha256']))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);run(ap.parse_args().directory)
