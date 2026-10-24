"""Frozen paired first-action references, not regret or independent WDL truth."""
from pathlib import Path
import argparse,json,time,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import guard,append,player
from scripts.search_performance_study import stamp
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json


def run(d):
    guard(d);reg=L.load(d/'execution-plan.json')['reference'];supp=L.load(d/'reference-plan-supplement.json');receipt=L.load(d/'bench-receipt.json');assert receipt['status']=='CLOSED'
    cases=L.load(d/'inputs.json')['cases'];bench=[json.loads(l)for l in(d/'bench.jsonl').read_text().splitlines()];out=d/'reference.jsonl'
    if out.exists():raise ValueError('fresh references only; no refill')
    write_json(d/'reference-selection.json',dict(registered_at=stamp(),selection='percase rep0 wall only; no selecting best replicate/result;otherrepeat changes descriptive',rule_order=[c['key']for c in cases],max_queries=48,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    began=stamp();t=time.perf_counter();cpu=time.process_time();count=0
    try:
        for case in cases:
            rr=[x for x in bench if x['case']==case['key']and x['mode']=='wall'and x['rep']==0];assert len(rr)==2
            rr=sorted(rr,key=lambda x:x['availability_enabled']);aa=[x['decision']['action']for x in rr]
            if aa[0]==aa[1]:continue
            c=L.compile_rule(L.ruleset_from_dict(case['rule']))
            for depth in reg['depths']:
                for arm,action in zip(['core','native'],aa):
                    guard(d);s=replay(c,case['record']);s.submit(L.match_action(s,action));before=L.record_value(s.to_record());p=player(c,False);start=stamp();q=time.perf_counter();cp=time.process_time();limits=SearchLimits(max_depth=depth,max_nodes=reg['nodes'],max_time_seconds=reg['seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8);dec=p.choose_action(s,limits)
                    row=dict(case=case['key'],arm=arm,action=action,requested_depth=depth,limits=L.record_value(limits),started_at=start,ended_at=stamp(),wall_seconds=time.perf_counter()-q,cpu_seconds=time.process_time()-cp,after_forced_action_record=before,decision=L.record_value(dec),root_score=-dec.score,completed=dec.completed_depth>=depth or dec.termination_reason=='terminal_position',quality_scope='sameEvaluator pairedactiondifference;not independenttruth/globalregret')
                    assert before==L.record_value(s.to_record());append(out,row);count+=1
                    print('reference',case['key'],arm,depth,dec.completed_depth,row['root_score'],row['completed'],flush=True)
        status='CLOSED'
    except Exception:
        status='FAILED';raise
    finally:
        write_json(d/'reference-receipt.json',dict(status=locals().get('status','FAILED'),started_at=began,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu,queries=count,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();run(a.directory)
