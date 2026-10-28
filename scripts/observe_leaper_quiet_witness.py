"""Bounded return-site observation of three already sealed Q4 scalar contexts."""
import argparse,json,time
from pathlib import Path
from scripts.leaper_scalar_dependency import ScalarDependencies
from scripts.leaper_quiet_root_intervention import S,SearchPathRuntime,SearchStatistics,SearchLimits,TranspositionTable,SearchTuning,EvaluationConfig,EvaluationProfileCache,Evaluator,make_session,record_value,write_record,sha,stamp,stopped,record_interval

class RootQ(ScalarDependencies):
 def returned(self,kind,site,value,env):
  result=super().returned(kind,site,value,env)
  if kind=='q' and len(self.stack)==1:self.root=self.stack[-1];self.root_children=list(self.root['children'])
  return result

def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert sha(__file__)==p['source_sha256'];assert not out.exists();out.mkdir();write_record(out/'frozen.json',p);begin=stamp();tick=time.perf_counter();rows=[];status='FAILED'
 try:
  c,s=make_session(json.loads(Path(p['candidate']).read_bytes()));cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);ev=Evaluator(c,profile,cfg);prior=json.loads(Path(p['prior']).read_bytes())
  for window in p['windows']:
   if stopped() or time.perf_counter()-tick>p['batch_seconds']:raise RuntimeError('frozen_stop')
   rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);before=(rt.position,tuple(rt.history),rt.search_key());stats=SearchStatistics();limits=SearchLimits(max_nodes=100000,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8);ctx=S._Context(c,ev,TranspositionTable(1),stats,S._Budget(limits,None),SearchTuning(),False,False,4,8,100000,runtime=rt,first_main_iteration_complete=True)
   obs=RootQ(depths=(),max_classifications=24);obs.active=True;obs.iteration=0
   with obs:value=S._quiescence_runtime(*window,0,0,ctx)
   original=next(x for x in prior if x['mode']=='BASELINE' and x['first_main_iteration_complete'] and x['entry_window']==window)
   assert value==original['value'];assert stats.nodes==original['stats']['nodes'] and stats.qnodes==original['stats']['qnodes'] and stats.evaluation_calls==original['stats']['evaluation_calls'];assert before==(rt.position,tuple(rt.history),rt.search_key());rt.assert_balanced()
   rows.append(dict(window=window,value=value,original_value_matched=True,work_matched=True,root=obs.root,root_children=obs.root_children,observer=obs.export()));write_record(out/'traces.json',rows)
  status='PASS'
 finally:
  end=stamp();r=dict(status=status,calls=len(rows),expected=3,started_at=begin,ended_at=end,seconds=time.perf_counter()-tick,scope='AST return and actual on-demand classification observations only. No extra legalactiongeneration/evaluation;no proof from equal values. SourceSites included;bounded24 classificationspercall.',lost_Q0_slot='UNKNOWN,not retried',new_Player_calls=0,new_games=0)
  write_record(out/'summary.json',r);record_interval(begin,end,'validation',str(out/'summary.json'),out);print(r)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--plan',type=Path,required=True);a.add_argument('--output',type=Path,required=True);x=a.parse_args();run(x.plan,x.output)
