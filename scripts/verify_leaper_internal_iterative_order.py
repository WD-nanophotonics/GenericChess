"""Read frozen IID returns; replay legal PVs only, never rerun Player/source."""
from pathlib import Path
import json,hashlib
from scripts.research_record import write_record
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action


def verify(base,output):
 b=Path(base);f=json.loads((b/'frozen.json').read_text(encoding='utf-8'))
 assert hashlib.sha256((b/'qualified-inputs.json').read_bytes()).hexdigest()==f['input_sha256']
 for p,h in f['sources'].items():assert hashlib.sha256((b/'frozen-source'/p).read_bytes()).hexdigest()==h
 inputs=json.loads((b/'qualified-inputs.json').read_text(encoding='utf-8'))['rows']
 returns=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(b.glob('return-*.json'))]
 assert len(returns)==32 and sorted(r['slot'] for r in returns)==list(range(32))
 plies=0;byroot={}
 for r in returns:
  row=inputs[r['root']];c,s=make_session(row);d=r['decision']
  assert r['record_before']==row['record'] and r['actual_tuning']['use_internal_iterative_order']==r['on']
  assert r['actual_tuning']['use_pvs'] and r['actual_limits']['quiescence_max_depth']==4
  assert r['actual_limits']['max_nodes']==2000000 and r['wall_seconds']<=3.1
  assert d['iid_attempts']==d['iid_completed']==d['iid_hints']==d['iid_budget_events']==0
  assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  if d['action'] is not None:action(d['action'],s)
  for a in d['principal_variation']:s.submit(action(a,s));plies+=1
  byroot.setdefault(r['root'],{})[r['on']]=r
 changed=[]
 for i in range(16):
  off,on=byroot[i][False],byroot[i][True]
  fields=lambda r:tuple(r['decision'][k] for k in ('choice_kind','action','declaration'))
  if fields(off)!=fields(on):changed.append(dict(root=i,OFFdepth=off['decision']['completed_depth'],ONdepth=on['decision']['completed_depth'],actualIID=0))
 result=dict(status='PASS_SAVED32_INACTIVE',returns=32,PVplies=plies,ONattempts=0,changed=changed,minimum_depth=min(r['decision']['completed_depth'] for r in returns),maximum_depth=max(r['decision']['completed_depth'] for r in returns),newPlayer=0,newSolver=0,limits='onewallpairchangedwithoutcandidatework;cannotattributetoIID;CorePVlegalitynotindependentWDL;alloldslotsCLOSED')
 write_record(output,result);return result
if __name__=='__main__':
 import sys;print(json.dumps(verify(sys.argv[1],sys.argv[2])))
