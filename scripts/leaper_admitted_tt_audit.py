"""Fixed new-geometry numeric-TT validation, not strength or a new solver.

Direct main D3/Q4, e=0/1, cold/hot-other-bank/noTT. Aborts are UNKNOWN;
matching values are checked only where both necessary searches completed.
"""
from __future__ import annotations
import argparse,json,time,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
from scripts.research_record import record_value,write_record
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline
from tools.local_agent import session
from tools.local_agent.common import read_json
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.session.session import GameSession

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(prepared,plan_path,out):
    assert not out.exists();plan=read_json(plan_path)
    assert sha(prepared/'inputs.json')==plan['input_sha256']
    for p,h in plan['sources'].items():assert sha(p)==h
    rows=json.loads((prepared/'inputs.json').read_bytes())['rows'];byid={r['id']:r for r in rows}
    assert len(plan['root_ids'])==8 and len({byid[x]['family'] for x in plan['root_ids']})==8
    out.mkdir();write_record(out/'frozen.json',dict(plan=plan,sources={p:Path(p).read_text(encoding='utf8') for p in plan['sources']}))
    import generic_chess.native as native
    module=native._module();binary=Path(module.__file__);write_record(out/'loaded-binary.json',dict(module=binary.name,sha256=sha(binary),bytes=binary.stat().st_size,python=sys.version))
    results=[];tick=time.perf_counter();halt=None
    for rid in plan['root_ids']:
        row=byid[rid];c,s=make_session(row);p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_one_check_extension=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
        provider=p._native_legality_provider;tables={0:TranspositionTable(),1:TranspositionTable()};answers={}
        for mode,e in [('cold',0),('cold',1),('hot-other',0),('hot-other',1),('noTT',0),('noTT',1)]:
            begin=stamp();t=time.perf_counter();x=dict(case_id=rid,family=row['family'],mode=mode,entry_bank=e,status='NOT_RUN')
            if time.perf_counter()-tick+plan['call_seconds']+2>=plan['batch_seconds']:halt=halt or 'batch_reserve'
            if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<plan['call_seconds']+plan['delivery_reserve_seconds']:halt=halt or 'whole_reserve'
            for name in ('rollout','advisor','slack'):
                if any(read_json(Path('.local_agent')/(name+'.json')).get(k,False) for k in ('stopped','stop_requested','research_stopped','user_paused')):halt='scoped_stop'
            if not halt:
                rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check)
                table=tables[e] if mode=='cold' else tables[1-e] if mode=='hot-other' else TranspositionTable()
                ctx=S._Context(c,p._evaluator,table,SearchStatistics(),S._Budget(SearchLimits(max_nodes=500000,max_time_seconds=plan['call_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8),CallerDeadline(t+plan['call_seconds'])),SearchTuning(use_one_check_extension=True,require_full_pv=True),mode!='noTT',True,4,8,None,runtime=rt)
                before=s.to_record()
                try:
                    got=S.negamax(rt.state,3,-S.INF,S.INF,0,ctx,remaining_extensions=e)
                    replay=GameSession.replay(c,before)
                    for a in got.pv:replay.submit(a)
                    assert got.best_action in s.legal_actions()
                    x.update(status='RETURNED',score=got.score,pv=record_value(got.pv),best_action=record_value(got.best_action))
                    answers[mode,e]=got.score
                except S.SearchAborted as exc:x.update(status='UNKNOWN',reason=str(exc))
                except Exception as exc:x.update(status='FAILED',error_type=type(exc).__name__,error=str(exc));halt='semantic_failure'
                rt.assert_balanced();assert s.to_record()==before
                x['statistics']=record_value(ctx.stats)
                if x['status']=='RETURNED':
                    for other in ('cold','hot-other','noTT'):
                        if (other,e) in answers and answers[other,e]!=x['score']:
                            x.update(status='FAILED_NUMERIC_TT',other_mode=other,other_score=answers[other,e]);halt='numeric_TT_mismatch'
            else:x['reason']=halt
            x.update(started_at=begin,ended_at=stamp(),wall_seconds=time.perf_counter()-t);results.append(x)
            write_record(out/'queries.json',results)
            if x['status']!='NOT_RUN' and begin<x['ended_at']:session.record_work(begin,x['ended_at'],'validation',str(out/'queries.json')+':'+rid+':'+mode+':'+str(e))
        print(json.dumps(dict(case_id=rid,statuses=[x['status'] for x in results if x['case_id']==rid])),flush=True)
    summary=dict(planned=48,returned=sum(x['status']=='RETURNED' for x in results),unknown=sum(x['status']=='UNKNOWN' for x in results),not_run=sum(x['status']=='NOT_RUN' for x in results),failed=sum(x['status'].startswith('FAILED') for x in results),halt=halt,interpretation='Finite directD3/Q4 new-geometry equality control;UNKNOWN not exact score. No Player games,solver/default change,all-domain theorem or search-strength evidence.')
    write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.prepared,a.plan,a.output)
