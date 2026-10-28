"""Cold scalar follow-up of ONE already sealed H6 witness, never a Player panel."""
import argparse,json,time
from pathlib import Path
from scripts.leaper_quiet_root_intervention import S,SearchPathRuntime,SearchStatistics,SearchLimits,TranspositionTable,SearchTuning,EvaluationConfig,EvaluationProfileCache,Evaluator,make_session,root_snapshot,record_value,write_record,sha,stamp,stopped,record_interval


def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert p['source_sha256']==sha(__file__);assert sha(p['candidate'])==p['candidate_sha256'];assert not out.exists();out.mkdir();write_record(out/'frozen.json',p)
 begin=stamp();tick=time.perf_counter();rows=[];attempts=0;status='FAILED';failure=None
 try:
  c,s=make_session(json.loads(Path(p['candidate']).read_bytes()));cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);ev=Evaluator(c,profile,cfg);original=record_value(s.to_record())
  for first in p['first_main_iteration_complete']:
   for kind,index in [('CHILD',i) for i in range(len(s.legal_actions()))]+[('MAIN',d) for d in p['depths']]:
    if stopped() or time.perf_counter()-tick>=p['batch_seconds']:raise RuntimeError('frozen_batch_or_stop')
    rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);snapshot=root_snapshot(rt);stats=SearchStatistics();lim=SearchLimits(max_depth=max(p['depths']),max_nodes=p['max_nodes'],max_time_seconds=p['query_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8)
    ctx=S._Context(c,ev,TranspositionTable(1),stats,S._Budget(lim,None),SearchTuning(),False,False,4,8,p['max_nodes'],runtime=rt,first_main_iteration_complete=first)
    trace=dict(kind=kind,index=index,first_main_iteration_complete=first,TT_enabled=False,entry_window=[-S.INF,S.INF]);qt=time.perf_counter();attempts+=1
    try:
     if kind=='CHILD':
      a=s.legal_actions()[index];trace['action']=record_value(a)
      with rt.pushed(a,checkpoint=ctx.checkpoint):raw=S._quiescence_runtime(-S.INF,S.INF,1,1,ctx)
      trace.update(raw_child_return=raw,root_perspective_value=-raw,pv=[])
     else:
      result=S.negamax(rt.state,index,-S.INF,S.INF,0,ctx);trace.update(root_perspective_value=result.score,best_action=record_value(result.best_action),pv=record_value(result.pv))
      check=type(s).replay(c,s.to_record())
      for a in result.pv:check.submit(a)
      trace['PV_Core_legal']=True
     trace['status']='RETURNED'
    except S.SearchAborted as e:trace.update(status='ABORTED',reason=str(e))
    write_record(out/'latest-before-validation.json',trace);rt.assert_balanced();assert root_snapshot(rt)==snapshot and record_value(s.to_record())==original
    trace.update(seconds=time.perf_counter()-qt,stats=record_value(stats),root_preserved=True);rows.append(trace);write_record(out/'queries.json',rows)
  status='CLOSED'
 except Exception as e:failure=type(e).__name__+':'+str(e);raise
 finally:
  end=stamp();r=dict(status=status,failure=failure,attempted=attempts,completed_rows=len(rows),started_at=begin,ended_at=end,seconds=time.perf_counter()-tick,new_Player_calls=0,new_games=0,new_solver=False,scope='Current cold direct Q/main calls on one original H6record;manual Qphase settings,not actual iterative service history or all-defense certificate')
  write_record(out/'summary.json',r);record_interval(begin,end,'research',str(out/'summary.json'),out);print(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();run(x.plan,x.output)
