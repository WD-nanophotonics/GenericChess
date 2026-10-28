"""Bounded actual-history coverage trace, not a WDL/quality proof."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
import json,time,argparse
from scripts.verify_leaper_pvs_quality_pilot import load,action
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.research_record import record_value,write_record
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime

def run(witness,inputs,out):
    assert not out.exists();out.mkdir(parents=True);rows={r['id']:r for r in load(inputs)['rows']};selected=load(witness/'witnesses.json')[1::2]
    assert len(selected)==6;write_record(out/'selected-before-query.json',dict(selection='second frozen Core witness per family; first was already used by contract tests; no score/outcome filter',rows=selected,max_calls=12,seconds_per_call=5,max_events=20000,depth=1,Q=4,hardQ=8,phase='DIRECT fixedQ4,NO iterative first-Q0 reserve; not desktop cost'))
    allresults=[];original_nega=S.negamax;original_eval=S._evaluate;original_push=SearchPathRuntime.pushed
    for row in selected:
        c,_=make_session(rows[row['case_id']]);root=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
        for on in (False,True):
            events=[];dropped=0;path=[];stack=[];counter=0
            def emit(x):
                nonlocal dropped
                if len(events)<20000:events.append(x)
                else:dropped+=1
            def traced_nega(*args,**kw):
                nonlocal counter
                counter+=1;cid=counter;ctx=args[5];emit(dict(kind='main_entry',call_id=cid,parent_id=stack[-1] if stack else None,path=list(path),depth=args[1],ply=args[4],entry_e=kw.get('remaining_extensions',int(ctx.tuning.use_one_check_extension))))
                stack.append(cid)
                try:
                    r=original_nega(*args,**kw);emit(dict(kind='main_return',call_id=cid,score=r.score,action=record_value(r.best_action)));return r
                except BaseException as e:
                    emit(dict(kind='main_exception',call_id=cid,type=type(e).__name__,reason=str(e)));raise
                finally:assert stack.pop()==cid
            def traced_eval(state,evaluator,ctx):
                value=original_eval(state,evaluator,ctx);emit(dict(kind='evaluation',parent_main=stack[-1] if stack else None,path=list(path),ply=state.ply_count,value=value));return value
            @contextmanager
            def pushed(rt,*args,**kw):
                with original_push(rt,*args,**kw) as value:
                    path.append(record_value(args[0]))
                    try:yield value
                    finally:path.pop()
            p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True);prov=p._native_legality_provider
            rt=SearchPathRuntime.from_state(root.state,c,history_witnesses=root._search_witnesses,legal_binding_provider=prov,availability_provider=prov.has_legal_action,check_provider=prov.in_check)
            limits=SearchLimits(max_nodes=200000,max_time_seconds=5,quiescence_max_depth=4,quiescence_hard_max_depth=8)
            ctx=S._Context(c,p._evaluator,TranspositionTable(),SearchStatistics(),S._Budget(limits,None),SearchTuning(use_one_check_extension=on),True,True,4,8,None,runtime=rt)
            begin=datetime.now(timezone.utc).isoformat();tick=time.perf_counter();result=None;failure=None
            S.negamax=traced_nega;S._evaluate=traced_eval;SearchPathRuntime.pushed=pushed
            try:result=S.negamax(rt.state,1,-S.INF,S.INF,0,ctx)
            except S.SearchAborted as e:failure=str(e)
            finally:S.negamax=original_nega;S._evaluate=original_eval;SearchPathRuntime.pushed=original_push
            rt.assert_balanced();assert not path and not stack
            if result:
                pv=GameSession.replay(c,root.to_record())
                for a in result.pv:pv.submit(a)
            item=dict(family=row['family'],root_record=row['record'],case_id=row['case_id'],on=on,started_at=begin,ended_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-tick,status='RETURNED' if result else 'ABORTED',result=record_value(result),failure=failure,stats=record_value(ctx.stats),events=events,dropped=dropped,limits=record_value(limits),root_restored=True,limits_of_inference='Passive main/eval coverage only. Qreturn bounds/TT producer chain not fully captured; no unique causal evaluation dependency or actual WDL claim. Observer overhead included; no performance comparison.')
            write_record(out/f'f{row["family"]}-on{int(on)}.json',item);allresults.append({k:v for k,v in item.items() if k!='events'})
    write_record(out/'summary.json',allresults);print(dict(calls=len(allresults),returned=sum(x['status']=='RETURNED' for x in allresults),dropped=sum(x['dropped'] for x in allresults),new_games=0,new_solver=0))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--witness',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.witness,a.inputs,a.output)
