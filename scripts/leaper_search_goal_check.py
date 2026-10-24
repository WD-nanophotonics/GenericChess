"""One exposed any-win caller check and one default-controller scope check."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, time
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
    reg=L.load(d/'plan.json');case=L.load(d/'case.json');old=L.load(Path(reg['original_directory'])/'ordering-receipt.json')
    assert old['status']=='CLOSED','one owned producer at a time'
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==reg['source_sha256']
    assert not(d/'queries.jsonl').exists(),'No refill/restart'
    baseline=next(json.loads(x)for x in (Path(reg['original_directory'])/'ordering-queries.jsonl').read_text().splitlines()if json.loads(x)['slot']=={'arm':'baseline','ply':50})
    assert hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest()==reg['reused_baseline_sha256']
    began=stamp();tick=time.perf_counter();cpu=time.process_time();calls=0;original=S.negamax
    class Material:
        def evaluate(self,state):
            v=sum((1 if p.owner==0 else -1)for p in state.position.board if p is not None and p.current_type_id in ('A','B'))
            return v if state.position.side_to_move==0 else -v
        def capture_order_value(self,mover,victim):return 0
    class Stop:
        last=0.; flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25:
                self.last=now;self.flag=stopped()or datetime.now(timezone.utc)>=datetime.fromisoformat(reg['deadline'])
            return self.flag
    try:
        for slot in reg['slots']:
            if Stop().is_cancelled():raise RuntimeError('stop/shared deadline; missing slots UNKNOWN')
            c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
            anywin=slot['controller']=='unit_anywin';tuning=SearchTuning(use_root_tactical=not anywin,require_full_pv=anywin,stop_after_root_win=anywin)
            p=AlphaBetaPlayer(c,use_disk_cache=False,evaluator_override=Material()if anywin else None,tuning=tuning)
            root=[];its=[];start=stamp();qt=time.perf_counter();qc=time.process_time()
            def observe(*args,**kwargs):
                r=original(*args,**kwargs)
                if args[4]==0:root[:]=[(args[1],r)]
                return r
            S.negamax=observe
            def progress(depth,nodes,qnodes):
                assert root[0][0]==depth;r=root[0][1]
                label=next(ch['truth']['value']for ch in case['children']if ch['action']==L.record_value(r.best_action))
                it=dict(depth=depth,nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-qt,score=r.score,action=L.record_value(r.best_action),published_child_WDL=label,principal_variation=L.record_value(r.pv))
                its.append(it);append(d/'iterations.jsonl',dict(controller=slot['controller'],**it));print('GOAL ITER',slot['controller'],depth,round(it['elapsed'],3),r.score,label,flush=True)
            limits=SearchLimits(max_depth=14,max_nodes=10000000,max_time_seconds=slot['seconds'],quiescence_max_depth=0 if anywin else 4,quiescence_hard_max_depth=0 if anywin else 8)
            dec=p.choose_action(s,limits,cancel_token=Stop(),progress_callback=progress);query_end=stamp();query_seconds=time.perf_counter()-qt
            assert L.state_sha(s.state)==case['state_sha256'];label=next(ch['truth']['value']for ch in case['children']if ch['action']==L.record_value(dec.action))
            leaf=replay(c,case['record'])
            for action in dec.principal_variation:assert action in leaf.legal_actions();leaf.submit(action)
            if anywin:
                for a,b in zip(its,baseline['iterations']):
                    assert all(a[k]==b[k]for k in ('depth','nodes','qnodes','score','action')),'before-goal tree prefix differs; diagnose rather than revise expectation'
                if dec.result_source=='completed_root_win' or dec.termination_reason=='root_win_found':
                    assert label==1 and leaf.result.winner==0 and leaf.result.status.value!='ongoing'
            row=dict(controller=slot['controller'],started_at=start,query_ended_at=query_end,ended_at=stamp(),query_seconds=query_seconds,outer_seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,tuning=L.record_value(tuning),limits=L.record_value(limits),actual_default_profile=L.record_value(p.evaluation_profile),decision=L.record_value(dec),published_child_WDL=label,iterations=its,PV_final_result=L.record_value(leaf.result),PV_plies=len(dec.principal_variation),native_availability=p.native_legality_provider.availability_metrics)
            append(d/'queries.jsonl',row);calls+=1;print('GOAL DONE',slot['controller'],dec.completed_depth,dec.termination_reason,dec.result_source,label,round(row['outer_seconds'],3),flush=True)
        status='CLOSED'
    except Exception:
        status='FAILED';raise
    finally:
        S.negamax=original
        write_json(d/'receipt.json',dict(status=locals().get('status','FAILED'),started_at=began,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,queries=calls,source_sha256=reg['source_sha256']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();run(a.directory)
