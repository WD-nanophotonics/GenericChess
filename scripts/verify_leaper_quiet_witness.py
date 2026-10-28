"""Independent immutable-Core audit of sealed single-witness scalar evidence."""
import argparse,json,time
from pathlib import Path
from scripts.leaper_quiet_root_intervention import S,SearchStatistics,SearchLimits,TranspositionTable,SearchTuning,EvaluationConfig,EvaluationProfileCache,Evaluator,make_session,record_value,write_record,sha,stamp,stopped,record_interval,bound
from generic_chess.ai.alphabeta.quiescence import classify_noisy


def context(c,ev,first):
 stats=SearchStatistics();limits=SearchLimits(max_depth=6,max_nodes=100000,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8)
 return S._Context(c,ev,TranspositionTable(1),stats,S._Budget(limits,None),SearchTuning(),False,False,4,8,100000,first_main_iteration_complete=first)


def reference(s,c,ctx,a,b,mode):
 if mode=='BASELINE':return S.quiescence(s.state,a,b,0,0,ctx)
 assert not s.state.terminal_status.is_terminal
 decl=S._declaration_options(s.state,c,ctx.stats);assert not decl,'this fixedsource candidate has no declarations'
 if mode=='ADD_QUIET':
  sp=S._evaluate(s.state,ctx.evaluator,ctx)
  if sp>=b:return sp
  a=max(a,sp)
  if S._ordinary_qdepth_limit(ctx)<=0:return a
 for action in sorted(s.legal_actions(),key=str):
  child=type(s).replay(c,s.to_record());child.submit(action)
  if mode=='NO_SP_NOISY' and not classify_noisy(s.state,[(action,child.state)],c):continue
  value=-S.quiescence(child.state,-b,-a,1,1,ctx)
  if value>=b:return value
  a=max(a,value)
 return a


def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert sha(__file__)==p['source_sha256'];assert not out.exists();out.mkdir();write_record(out/'frozen.json',p)
 for f,h in p['inputs'].items():assert sha(f)==h
 begin=stamp();tick=time.perf_counter();checks=[];status='FAILED';error=None
 try:
  c,s=make_session(json.loads(Path(p['candidate']).read_bytes()));cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);ev=Evaluator(c,profile,cfg);original=record_value(s.to_record())
  source=json.loads(Path(p['candidate']).read_bytes());facts={str(x['action']):x for x in source['actions']}
  q=json.loads(Path(p['interventions']).read_bytes())
  for i,x in enumerate(q):
   if stopped() or time.perf_counter()-tick>=p['batch_seconds']:raise RuntimeError('bounded_validation_stop')
   ctx=context(c,ev,x['first_main_iteration_complete']);a,b=x['entry_window'];v=reference(s,c,ctx,a,b,x['mode']);assert x['status']=='RETURNED' and v==x['value'];assert bound(v,a,b)==x['bound_vs_original_entry'];assert record_value(s.to_record())==original
   checks.append(dict(kind='intervention',index=i,immutable_value=v,match=True));write_record(out/'checks.json',checks)
  q=json.loads(Path(p['followup']).read_bytes())
  for i,x in enumerate(q):
   if stopped() or time.perf_counter()-tick>=p['batch_seconds']:raise RuntimeError('bounded_validation_stop')
   ctx=context(c,ev,x['first_main_iteration_complete'])
   if x['kind']=='CHILD':
    a=s.legal_actions()[x['index']];assert record_value(a)==x['action'];child=type(s).replay(c,s.to_record());child.submit(a);v=-S.quiescence(child.state,-S.INF,S.INF,1,1,ctx)
   else:
    r=S.negamax(s.state,x['index'],-S.INF,S.INF,0,ctx);v=r.score;assert record_value(r.best_action)==x['best_action'];check=type(s).replay(c,s.to_record())
    for a in r.pv:check.submit(a)
   assert x['status']=='RETURNED' and v==x['root_perspective_value'];assert record_value(s.to_record())==original;checks.append(dict(kind='followup',index=i,immutable_value=v,match=True));write_record(out/'checks.json',checks)
  status='PASS'
 except Exception as e:error=type(e).__name__+':'+str(e);raise
 finally:
  end=stamp();r=dict(status=status,error=error,started_at=begin,ended_at=end,seconds=time.perf_counter()-tick,checked=len(checks),expected=39,route='ImmutableGameSession fullCorechild construction+immutableproductionQ/main;no mutableSearchPathRuntime',claim='Independent execution route agreement,not independent implementation of allsearch/evaluator or independent WDLproof',lost_original_slot='UNKNOWN,not replaced',new_Player_calls=0,new_games=0,new_solver=False)
  write_record(out/'summary.json',r);record_interval(begin,end,'validation',str(out/'summary.json'),out);print(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();run(x.plan,x.output)
