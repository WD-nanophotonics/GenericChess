"""Saved root-scheduling records: literal Core replay, no Player/solver."""
from pathlib import Path
import json,hashlib
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(base,out):
 b=Path(base);p=json.loads((b/'frozen.json').read_text());assert sha(b/'inputs.json')==p['input_sha256'];rows=json.loads((b/'inputs.json').read_text())['rows'];rs=[];plies=0
 for slot,f in enumerate(sorted(b.glob('return-*.json'))):
  r=json.loads(f.read_text());ri=r['root'];assert r['slot']==slot and ri==slot//2
  assert r['on']==((slot%2==1) if ri%2==0 else (slot%2==0));c,s=make_session(rows[ri]);assert record_value(s.to_record())==r['record_before'];d=r['decision'];trace=r['completed_iteration_trace'];depths=[x['depth'] for x in trace];assert depths==sorted(set(depths)) and depths[-1]==d['completed_depth']
  assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert r['actual_tuning']['skip_one_stable_root_iteration']==r['on'];assert r['actual_limits']['quiescence_max_depth']==4 and r['actual_limits']['quiescence_hard_max_depth']==8 and r['actual_limits']['max_nodes']==500000
  assert d['root_stability_skips'] in (0,1)
  if d['root_stability_skips']:
   assert r['on'] and d['root_stability_skipped_depth'] not in depths and d['root_stability_skipped_depth']<64
  else:assert d['root_stability_skipped_depth'] is None
  assert r['timing_eligible']==(r['wall_seconds']<=1.1)
  assert action(d['action'],s) in s.legal_actions();clone=type(s).replay(c,s.to_record())
  for a in d['principal_variation']:clone.submit(action(a,clone));plies+=1
  rs.append(r)
 summary=json.loads((b/'summary.json').read_text());assert len(rs)==summary['returns'] and summary['NOT_RUN']==list(range(len(rs),32));pairs=[]
 for ri,row in enumerate(rows):
  pair=[next((r for r in rs if r['root']==ri and r['on']==on),None) for on in [False,True]]
  if not all(pair):continue
  off,on=pair;ta=dict(off['actual_tuning']);tb=dict(on['actual_tuning']);ta.pop('skip_one_stable_root_iteration');tb.pop('skip_one_stable_root_iteration');assert ta==tb
  identical=off['decision']['action']==on['decision']['action'] and off['decision']['declaration']==on['decision']['declaration'];pairs.append(dict(root=ri,family=row['family'],identical_choice=identical,relative_value_interval=[0,0] if identical else [-2,2],active=on['decision']['root_stability_skips']==1,timed=off['timing_eligible'] and on['timing_eligible'],OFF_depth=off['decision']['completed_depth'],ON_depth=on['decision']['completed_depth']))
 active=sorted({f for f in range(8) if sum(r['family']==f and r['active'] and r['timed'] for r in pairs)==2});changed=sorted({r['family'] for r in pairs if not r['identical_choice']});assert active==summary['stable_active_families'] and changed==summary['changed_choice_families']
 gate=len(rs)==32 and len(active)>=4 and bool(changed) and all(r['timed'] for r in pairs);assert summary['status']==('QUALIFIED_PENDING_BOUNDED_WDL' if gate else 'STOP_INSUFFICIENT_MECHANISM_OR_DIFFERENCE')
 result=dict(status='PASS_SAVED_SCOPE',returns=len(rs),pairs=len(pairs),literal_Core_PV_plies=plies,stable_active_families=active,changed_choice_families=changed,identical_choice_pairs=sum(r['identical_choice'] for r in pairs),qualified_to_grade=gate,PN_calls=0,PN_status=summary['PN_qualification_status'],records=pairs,new_Player=0,new_solver=0,limits='SharedCore/savedsource,not independenthardware. No periterationtypedaction snapshot;source+scriptedcontrolsupports predicate,not literalrawtriggerreconstruction. Sameaction=>relative0 without WDLlabels. Root0shallowerretaineddepth doesnotprovequalityregression.');write_record(out,result);print(json.dumps(result));return result
if __name__=='__main__':
 import sys;verify(sys.argv[1],sys.argv[2])
