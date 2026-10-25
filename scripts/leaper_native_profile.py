"""Two-call preregistered remaining-cost diagnostic; no policy changes."""
from pathlib import Path
from datetime import datetime,timezone
import cProfile,pstats,time,json,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_native_default_study import player,context,metrics,delta
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from tools.local_agent import session
from tools.local_agent.common import write_json

def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
 plan=L.load(d/'profile-plan.json');assert L.load(d/'fitness-receipt.json')['status']=='CLOSED';data=L.load(d/'inputs.json');assert not(d/'profile-queries.jsonl').exists();tick=time.perf_counter();rows=[];status='FAILED'
 class Cancel:
  last=0.;flag=False
  def is_cancelled(self):
   t=time.perf_counter()
   if t-self.last>=.25:self.last=t;self.flag=session.stopped()or t-tick>=plan['batch_seconds']
   return self.flag
 cancel=Cancel()
 try:
  for slot in plan['slots']:
   assert not cancel.is_cancelled();c,s=context(data,plan['case']);before=L.record_value(s.to_record());p=player(c,'both');m=metrics(p);pr=cProfile.Profile()if slot=='cProfile'else None;begin=stamp();t=time.perf_counter()
   try:
    if pr:pr.enable()
    dec=p.choose_action(s,SearchLimits(max_depth=plan['depth'],max_nodes=plan['max_nodes'],max_time_seconds=plan['max_time_seconds']),cancel_token=cancel)
   except BaseException:
    append(d/'profile-failures.jsonl',dict(slot=slot,started_at=begin,ended_at=stamp(),traceback=traceback.format_exc()));raise
   finally:
    if pr:pr.disable()
   ended=stamp();elapsed=time.perf_counter()-t
   if pr:pr.dump_stats(str(d/'profile-private.pstats'))
   row=dict(slot=slot,started_at=begin,ended_at=ended,seconds=elapsed,before_record=before,decision=L.record_value(dec),provider_delta=delta(m,metrics(p)));append(d/'profile-queries.jsonl',row);rows.append(row);session.record_work(begin,row['ended_at'],'research',f'{d.as_posix()}/profile-queries.jsonl {slot}:registeredremainingcostdiagnostic,notWDLfitness')
   assert before==L.record_value(s.to_record())and dec.runtime_pushes==dec.runtime_pops
   pv=replay(c,before)
   for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
   if pr:
    stats=pstats.Stats(pr);flat=[];root=Path.cwd().resolve()
    for (filename,line,name),(primitive,calls,selfseconds,cumulative,callers)in stats.stats.items():
     f=Path(filename)
     try:shown=f.resolve().relative_to(root).as_posix()
     except ValueError:shown=f.name
     flat.append(dict(file=shown,line=line,function=name,primitive_calls=primitive,calls=calls,self_seconds=selfseconds,cumulative_seconds=cumulative))
    write_json(d/'profile-functions.json',dict(timer='cProfiledefaultelapsedtimer; selfcostdiagnosticunderinstrumentation, not unbiasedunprofiledfraction',total_calls=stats.total_calls,total_self_seconds=stats.total_tt,functions=sorted(flat,key=lambda r:r['self_seconds'],reverse=True)))
  fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','result_source'];passed=all(r['decision']['completed_depth']==plan['depth']for r in rows)and all(rows[0]['decision'][f]==rows[1]['decision'][f]for f in fields)
  write_json(d/'profile-assessment.json',dict(parity_passed=passed,fields=fields,queries=len(rows),unprofiled_seconds=rows[0]['seconds'],profiled_seconds=rows[1]['seconds'],limitations='Onefullhistory, completed-depthobserverparityonly. Functiontimingisperturbed; no newquality/strengthclaim. Incomplete/parityfailure staysUNKNOWN, no retry.'))
  status='CLOSED'if passed else'CLOSED_UNKNOWN'
 finally:write_json(d/'profile-receipt.json',dict(status=status,queries=len(rows),ended_at=stamp(),seconds=time.perf_counter()-tick,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
 print('PROFILE',status,len(rows),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
