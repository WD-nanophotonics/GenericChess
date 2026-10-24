"""One existing PVS switch at fixed requested depth; no selective pruning/default."""
from pathlib import Path
import argparse,json,time,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import guard,append
from scripts.search_performance_study import stamp
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json


def run(d):
    reg=L.load(d/'pvs-plan.json');guard(d);assert L.load(d/'bench-receipt.json')['status']=='CLOSED'
    cases=L.load(d/'inputs.json')['cases'];out=d/'pvs.jsonl'
    if out.exists():raise ValueError('no automatic PVS rerun/refill')
    began=stamp();t=time.perf_counter();cpu=time.process_time();calls=0
    try:
        for key in reg['cases']:
            case=next(c for c in cases if c['key']==key);c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);depth=reg['requested_depths'][key]
            for rep in range(reg['repetitions']):
                pair=[]
                for enabled in ((False,True)if rep==0 else(True,False)):
                    guard(d);start=stamp();q=time.perf_counter();cp=time.process_time();p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_availability=True,tuning=SearchTuning(use_pvs=enabled));setup=time.perf_counter()-q;before=L.record_value(s.to_record());limits=SearchLimits(max_depth=depth,max_nodes=524288,max_time_seconds=45,quiescence_max_depth=4,quiescence_hard_max_depth=8);dec=p.choose_action(s,limits)
                    row=dict(case=key,input_sha256=case['input_sha256'],rep=rep,pvs_enabled=enabled,availability_enabled=True,requested_depth=depth,limits=L.record_value(limits),started_at=start,ended_at=stamp(),wall_seconds=time.perf_counter()-q,cpu_seconds=time.process_time()-cp,setup_seconds=setup,decision=L.record_value(dec),availability_metrics=p.native_legality_provider.availability_metrics,complete=dec.completed_depth>=depth or dec.termination_reason=='terminal_position')
                    assert before==L.record_value(s.to_record());assert dec.action in s.legal_actions();append(out,row);pair.append(row);calls+=1
                    print('PVS',key,rep,enabled,'requested',depth,'completed',dec.completed_depth,'work',dec.nodes+dec.qnodes,'score',dec.score,round(row['wall_seconds'],3),flush=True)
                if all(x['complete']for x in pair):assert pair[0]['decision']['score']==pair[1]['decision']['score'],'PVS completed-value contract mismatch; investigate,neverrewriteexpectation'
        status='CLOSED'
    except Exception:
        status='FAILED';raise
    finally:
        write_json(d/'pvs-receipt.json',dict(status=locals().get('status','FAILED'),started_at=began,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu,queries=calls,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();run(a.directory)
