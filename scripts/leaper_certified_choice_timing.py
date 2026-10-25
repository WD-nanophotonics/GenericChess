"""Bounded certificate-tier timing observation under unchanged Nativeboth/PVS.
Measures selected completed-iteration actions, not causal Q provenance/solver truth.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player,metrics,delta
from scripts.leaper_iteration_choice_observer import IterationChoiceObserver
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent import session
from generic_chess.ai.limits import SearchLimits

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def label(case,action):
 found=[a for a in case['action_labels']if a['action']==action]
 if not found:return dict(known=False,own_WDL=None,goal_met=None,tier=case['label_tier'])
 assert len(found)==1;v=found[0]['own_WDL'];goal=v>=0 if case['goal']=='certified_nonloss'else v==case['root_own_WDL']
 return dict(known=True,own_WDL=v,goal_met=goal,tier=case['label_tier'])
def run(d,phase):
 plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert L.load(Path(plan['parent_receipt']))['status']=='CLOSED';assert sha(Path(plan['parent_receipt']))==plan['parent_sha256'];assert sha(d/'inputs.json')==plan['inputs_sha256'];assert session.status()['id']==plan['session_id']
 for p,h in plan['sources'].items():assert sha(p)==h
 if phase=='measurement':assert L.load(d/'qualification-assessment.json')['passed']
 assert not(d/(phase+'-queries.jsonl')).exists();cases={c['key']:c for c in data['cases']};slots=plan[phase];tick=time.perf_counter();count=0;status='FAILED'
 class Cancel:
  last=0.;flag=False
  def is_cancelled(self):
   t=time.perf_counter()
   if t-self.last>=.25:self.last=t;self.flag=session.stopped()or t-tick>=plan['batch_seconds'][phase]
   return self.flag
 cancel=Cancel()
 try:
  for slot in slots:
   assert not cancel.is_cancelled();case=cases[slot['case']];c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);before=L.record_value(s.to_record());begin=stamp();t=time.perf_counter();p=player(c,'baseline');setup=time.perf_counter()-t;m=metrics(p);obs=IterationChoiceObserver(t)if slot['observed']else None
   limits=SearchLimits(max_depth=plan['qualification_depth']if phase=='qualification'else 8,max_nodes=200000,max_time_seconds=15 if phase=='qualification'else 30)
   dec=p.choose_action(s,limits,cancel_token=cancel,progress_callback=obs)
   end=stamp();row=dict(slot=slot,started_at=begin,ended_at=end,seconds=time.perf_counter()-t,setup_seconds=setup,limits=L.record_value(limits),before_record=before,decision=L.record_value(dec),profile=L.record_value(p.evaluation_profile),tuning=L.record_value(p._tuning),use_ordering=p._use_ordering,provider_delta=delta(m,metrics(p)),iterations=obs.events if obs else[],label_tier=case['label_tier'],final_label=label(case,L.record_value(dec.action)))
   # No oracle labels are read by the observer/player; postclassify only now.
   for e in row['iterations']:e['label']=label(case,e['action'])
   append(d/(phase+'-queries.jsonl'),row);count+=1
   if end>begin:session.record_work(begin,end,'research',f'{d.as_posix()}/{phase}-queries.jsonl actual unchanged-controller iteration-choice observation{count}; no policy or label-fed ordering')
   assert before==L.record_value(s.to_record())and dec.runtime_pushes==dec.runtime_pops
   pv=replay(c,before)
   for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
   if obs and dec.result_source=='main_iteration':assert obs.events[-1]['depth']==dec.completed_depth and obs.events[-1]['action']==L.record_value(dec.action)and obs.events[-1]['score']==dec.score
   print('ITERATION-CHOICE',phase,count,slot['case'],dec.completed_depth,dec.result_source,row['final_label'],flush=True)
  status='CLOSED'
 except BaseException:write_json(d/(phase+'-failure.json'),dict(at=stamp(),queries=count,error=traceback.format_exc()));raise
 finally:write_json(d/(phase+'-receipt.json'),dict(status=status,queries=count,seconds=time.perf_counter()-tick,ended_at=stamp(),plan_sha256=sha(d/'plan.json')))
 if phase=='qualification':
  rr=[json.loads(x)for x in(d/'qualification-queries.jsonl').read_text().splitlines()];fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_hits','tt_probes','tt_cutoffs','runtime_pushes','runtime_pops']
  for a,b in zip(rr[::2],rr[1::2]):
   assert a['decision']['completed_depth']==b['decision']['completed_depth']==plan['qualification_depth']
   assert all(a['decision'][f]==b['decision'][f]for f in fields)and a['provider_delta']==b['provider_delta']
  write_json(d/'qualification-assessment.json',dict(passed=True,queries=len(rr),fields=fields,scope='Fixed requested-depth parity incl actual provider calls. Callback serialization perturbs time; timed deadlines can differ. No full-tree/Q causal observer.'))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['qualification','measurement']);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();run(a.directory,a.phase)
