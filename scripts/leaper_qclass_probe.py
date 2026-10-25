"""Two frozen complete-history observer pairs, no policy prototype."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_native_default_study import context,player,metrics,delta
from scripts.leaper_qclass_observer import QClassificationObserver
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
 plan=L.load(d/'probe-plan.json');data=L.load(d/'inputs.json');assert not(d/'probe-queries.jsonl').exists();tick=time.perf_counter();count=0;status='FAILED'
 for f,h in plan['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
 class Cancel:
  last=0.;flag=False
  def is_cancelled(self):
   t=time.perf_counter()
   if t-self.last>=.25:self.last=t;self.flag=session.stopped()or t-tick>=plan['batch_seconds']
   return self.flag
 token=Cancel()
 try:
  for slot in plan['slots']:
   assert not token.is_cancelled();c,s=context(data,slot['case']);p=player(c,'both');before=L.record_value(s.to_record());m=metrics(p);observer=QClassificationObserver()if slot['observed']else None;begin=stamp();t=time.perf_counter()
   try:
    if observer:observer.__enter__()
    dec=p.choose_action(s,SearchLimits(max_depth=5,max_nodes=200000,max_time_seconds=20),cancel_token=token)
   except BaseException:
    write_json(d/'probe-failure.json',dict(slot=slot,started_at=begin,ended_at=stamp(),observer=observer.result()if observer else None,error=traceback.format_exc()));raise
   finally:
    if observer:observer.__exit__(None,None,None)
   row=dict(slot=slot,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-t,before_record=before,decision=L.record_value(dec),provider_delta=delta(m,metrics(p)),observer=observer.result()if observer else None);append(d/'probe-queries.jsonl',row);count+=1
   if row['ended_at']>begin:session.record_work(begin,row['ended_at'],'research',f'{d.as_posix()}/probe-queries.jsonl actualQclassificationobserver query{count},frozenD5/no newsemanticqueries')
   assert before==L.record_value(s.to_record())and dec.runtime_pushes==dec.runtime_pops
   pv=replay(c,before)
   for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
  rr=[json.loads(x)for x in(d/'probe-queries.jsonl').read_text().splitlines()];fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_hits','tt_probes','tt_cutoffs','runtime_pushes','runtime_pops']
  for i in range(0,len(rr),2):
   a,b=rr[i:i+2];assert a['slot']['case']==b['slot']['case'];assert all(x['decision']['completed_depth']==5 for x in(a,b));assert all(a['decision'][f]==b['decision'][f]for f in fields)
   assert a['provider_delta']==b['provider_delta']
  write_json(d/'probe-assessment.json',dict(passed=True,pairs=len(rr)//2,fields=fields,observations=[dict(case=r['slot']['case'],seconds=r['seconds'],observer=r['observer'])for r in rr if r['observer']],scope='Actualvisitedclassifications/fullpush+pop cost, no valuecausalclaim/costproportionalestimate. Observerperturbswalltime, not newevaluator/semanticcalls.'))
  status='CLOSED'
 finally:write_json(d/'probe-receipt.json',dict(status=status,queries=count,ended_at=stamp(),seconds=time.perf_counter()-tick))
 print('QPROBE',status,count,flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
