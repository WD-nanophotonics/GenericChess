"""Tiny preregistered fullhistory/warmTT/cancel-recovery Native qualification.
Run after the primary timing producer closes. No fitness refills or defaults.
"""
from pathlib import Path
from datetime import datetime,timezone
import time,json,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_native_default_study import player,metrics,delta,context
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
 plan=L.load(d/'boundary-plan.json');data=L.load(d/'boundary-inputs.json');main=L.load(d/'inputs.json');assert L.load(d/'fitness-receipt.json')['status']=='CLOSED'
 assert hashlib.sha256((d/'boundary-inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
 assert not(d/'boundary-queries.jsonl').exists();tick=time.perf_counter();began=stamp();count=0;status='FAILED'
 class Stop(RuntimeError):pass
 class Cancel:
  last=0.;flag=False
  def is_cancelled(self):
   t=time.perf_counter()
   if t-self.last>=.25:self.last=t;self.flag=t-tick>=plan['batch_seconds']or session.stopped()
   return self.flag
 guard=Cancel()
 def query(c,s,p,arm,label,depth,token=None):
  nonlocal count
  if guard.is_cancelled():raise Stop('boundarycap/role stop')
  before=L.record_value(s.to_record());m=metrics(p);begin=stamp();t=time.perf_counter()
  try:dec=p.choose_action(s,SearchLimits(max_depth=depth,max_nodes=plan['max_nodes'],max_time_seconds=plan['max_time_seconds']),cancel_token=token or guard)
  except BaseException:
   append(d/'boundary-failures.jsonl',dict(id=count,label=label,arm=arm,started_at=begin,ended_at=stamp(),metrics=metrics(p),error=traceback.format_exc()));raise
  row=dict(id=count,arm=arm,label=label,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-t,before_record=before,decision=L.record_value(dec),provider_delta=delta(m,metrics(p)));append(d/'boundary-queries.jsonl',row);count+=1
  if row['ended_at']>begin:session.record_work(begin,row['ended_at'],'validation',f'{d.as_posix()}/boundary-queries.jsonl qualification{count}:newnearclock/warmTT/cancelrecovery,notfitnessrefill')
  assert before==L.record_value(s.to_record())and dec.runtime_pushes==dec.runtime_pops
  pv=replay(c,before)
  for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
  return row
 try:
  near=[];warm=[]
  for case in data['cases']:
   c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record'])
   for arm in plan['arms']:
    p=player(c,arm)
    for call in ('cold','warm'):near.append(query(c,s,p,arm,dict(case=case['key'],call=call),3))
   last=replay(c,case['expected_terminal_record']);assert last.result.status.value=='max_ply'and last.result.winner is None
  for key in plan['warm_cases']:
   c,s=context(main,key)
   for arm in plan['arms']:
    p=player(c,arm)
    for call in ('cold','warm'):warm.append(query(c,s,p,arm,dict(case=key,call=call),4))
  for arm in plan['arms']:
   c,s=context(main,plan['warm_cases'][0]);p=player(c,arm)
   class Poll:
    calls=0
    def is_cancelled(self):self.calls+=1;return self.calls>=100
   cancelled=query(c,s,p,arm,dict(cancel_after_polls=100),16,Poll());assert cancelled['decision']['termination_reason']=='cancelled'
   recovered=query(c,s,p,arm,dict(recovery_after_cancel=True),3);assert recovered['decision']['completed_depth']==3
  fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','result_source']
  for group,depth in ((near,3),(warm,4)):
   keys={(r['label']['case'],r['label']['call'])for r in group}
   for key,call in keys:
    rr=[r for r in group if r['label']==dict(case=key,call=call)];assert len(rr)==2
    assert all(r['decision']['completed_depth']==depth for r in rr)
    assert all(rr[0]['decision'][f]==rr[1]['decision'][f]for f in fields),(key,call)
  assert count==plan['expected_queries'];status='CLOSED'
 except Stop:status='STOPPED_UNKNOWN'
 finally:write_json(d/'boundary-receipt.json',dict(status=status,queries=count,started_at=began,ended_at=stamp(),seconds=time.perf_counter()-tick,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limitations='Nearclockthreeactualfullwalks, twowarmknownhistories; notallhistoryequivalence. Pollcancelnotmatchingsearchfrontier; existingproducttests cover required providerfailure and handoffconsumption.'))
 print('BOUNDARIES',status,count,flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
