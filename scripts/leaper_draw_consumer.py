"""One frozen small scalar consumer survey; all inputs full-history paid records."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import nullcontext
import time,hashlib,json,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from scripts.leaper_draw_observer import DrawObserver
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(d):
    d.mkdir(exist_ok=False)
    paid=L.load(Path('.local_agent/lmr-f538/inputs.json')); opportunities=L.load(Path('.local_agent/leaper-draw-opportunity-f538.json'))
    cases=[]
    for c in paid['cases']:
        if c['actual_ply']==0:cases.append(dict(id=c['key']+'-initial',rule=c['rule'],record=c['record'],kind='full_inventory'))
    bykey={c['key']:c for c in paid['cases']};seen=set()
    for x in opportunities['twoK_records']:
        c=bykey[x['case']];fp=c['semantic_fingerprint']
        if fp in seen:continue
        seen.add(fp);cases.append(dict(id=x['game']+'-first-twoK',rule=c['rule'],record=x['full_record'],kind='paid_twoK_root'))
    assert len(cases)==6+len(seen) and len(seen)>0
    write_json(d/'inputs.json',dict(cases=cases,selection='All6initial rules plus FIRST paid twoK occurrence per full fingerprint in chronological original record order, no quality-label selection. Missing twoK root for one rule retained, no synthetic positive. Exposed old histories; this is new instrumentation not frozen-slot refill.'))
    sources={p:sha(p) for p in ['scripts/leaper_draw_observer.py','scripts/leaper_draw_consumer.py','generic_chess/ai/alphabeta/search.py']}
    slots=[dict(case=c['id'],observed=o) for i,c in enumerate(cases) for o in ((False,True) if i%2==0 else (True,False))]
    write_json(d/'plan.json',dict(at=stamp(),question='Do fully-admitted twoKing states occur at actual costly nonterminal nonroot calls, beyond realCoreterminal/TT handling, and is classifier overhead small enough to justify a separate cutoff experiment?',slots=slots,nodes=10000,per_query_seconds=10,batch_seconds=270,inputs_sha256=sha(d/'inputs.json'),sources=sources,prior_chain_cost='Carry12.527s prior finite invariant plus earlier untimed proposal/inventory engineering; no newUUID budget reset. Conservative whole-chain engineering+survey+conditional prototype/quality expected100min<120; stop forUSER if forecast grows>=120.',scope='No cutoff, product flag, solver, AUX source execution, oldslotrefill or WDLclaim. Instrumented top-regiontime NOT savedtime. Fixednode actual equality checked; timecensored pairs UNKNOWN.'))
def run(d):
    p=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(d/'inputs.json')==p['inputs_sha256']
    for f,h in p['sources'].items():assert sha(f)==h
    assert not (d/'queries.jsonl').exists();tick=time.perf_counter();start=stamp();status='FAILED';count=0
    cases={c['id']:c for c in data['cases']}
    class Cancel:
        last=0.;stop=False
        def is_cancelled(self):
            t=time.perf_counter()
            if t-self.last>=.25:self.last=t;self.stop=session.stopped() or t-tick>=p['batch_seconds']
            return self.stop
    cancel=Cancel()
    try:
        for slot in p['slots']:
            if cancel.is_cancelled():status='STOPPED_UNKNOWN';break
            case=cases[slot['case']];r=L.ruleset_from_dict(case['rule']);c=L.compile_rule(r);s=replay(c,case['record']);before=L.record_value(s.to_record())
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True));observer=DrawObserver(r) if slot['observed'] else None
            begin=stamp();qt=time.perf_counter();cpu=time.process_time()
            try:
                with observer if observer else nullcontext():dcn=player.choose_action(s,SearchLimits(max_depth=64,max_nodes=p['nodes'],max_time_seconds=p['per_query_seconds']),cancel_token=cancel)
                row=dict(slot=slot,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-cpu,decision=L.record_value(dcn),observer=observer.summary() if observer else None,root_record=before,state_sha256=L.state_sha(s.state))
                append(d/'queries.jsonl',row);count+=1
                session.record_work(row['started_at'],row['ended_at'],'research',f'{d.as_posix()}/queries.jsonl slot{count} actualCore consumer scalar query; frozen source/input/node/time caps')
                assert L.record_value(s.to_record())==before
                print('DRAW-CONSUMER',count,slot['case'],slot['observed'],dcn.completed_depth,dcn.nodes+dcn.qnodes,round(row['seconds'],3),flush=True)
            except BaseException:
                write_json(d/f'partial-{count}.json',dict(slot=slot,started_at=begin,ended_at=stamp(),observer=observer.summary() if observer else None,traceback=traceback.format_exc()));raise
        else:status='CLOSED'
    finally:
        write_json(d/'receipt.json',dict(status=status,queries=count,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick))
if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','run']);a.add_argument('--directory',type=Path,required=True);x=a.parse_args();globals()[x.phase](x.directory)
