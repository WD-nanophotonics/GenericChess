import json,time,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task724';d=json.loads((R/'results/dev_aux/task720/declaration.json').read_bytes());ep=json.loads((R/'results/dev_aux/task721/endpoints.json').read_bytes());r=json.loads((R/'results/dev_aux/task722/result.json').read_bytes());gs=[json.loads(t) for t in (R/'results/dev_aux/task722/games.jsonl').open(encoding='utf-8')];freeze=json.loads((R/'results/dev_aux/task720/all_endpoints_frozen.json').read_bytes());assert freeze['before_any_new_development'] and r['status']=='COMPLETE';models=[]
def val(g,m):
 if m=='meanqty':return F(g['quantity12']+g['quantity24'],38)
 if m=='qty12':return F(g['quantity12'],19)
 if m=='qty24':return F(g['quantity24'],19)
 w=g['termination']['winner']
 if w is None:return F(0)
 if m=='terminal':return F(32 if w==g['color'] else -32)
 return F(25-len(g['actions']),25) if w==g['color'] else F(-1)
for e in ep['endpoints']:
 a=next(x['batch'] for x in r['rows'] if e['start']+'-initial' in x['names']);b=next(x['batch'] for x in r['rows'] if e['start']+'-endpoint' in x['names']);aa=[gs[x['line']-1] for x in a['sources']];bb=[gs[x['line']-1] for x in b['sources']];assert len(aa)==len(bb)==32 and [(g['replica'],g['root'],g['color']) for g in aa]==[(g['replica'],g['root'],g['color']) for g in bb];families=sorted({g['root']['source_family'] for g in aa});metrics=[]
 for metric in ['meanqty','qty12','qty24','common_fast','terminal']:
  dd=[val(y,metric)-val(x,metric) for x,y in zip(aa,bb)];metrics.append(dict(metric=metric,gain=str(sum(dd)/32),initial_mean=str(sum(val(x,metric) for x in aa)/32),endpoint_mean=str(sum(val(x,metric) for x in bb)/32),by_replica=[dict(replica=ri,gain=str(sum(dd[i] for i,g in enumerate(aa) if g['replica']==ri)/16)) for ri in [0,1]],by_family=[dict(family=f,gain=str(sum(dd[i] for i,g in enumerate(aa) if g['root']['source_family']==f)/4)) for f in families],leave_one=[dict(omit=f,gain=str(sum(dd[i] for i,g in enumerate(aa) if g['root']['source_family']!=f)/28)) for f in families]))
 models.append(dict(start=e['start'],initial=e['initial'],endpoint=e['endpoint'],accepted=sum(F(u['accepted_gain'])>0 for u in ep['updates'] if u['start']==e['start']),metrics=metrics))
out=dict(status='ALL_RICH_ROOT_MULTI_HORIZON_DEV_SCORES_FROZEN',models=models,source_sha256=hashlib.sha256((R/'results/dev_aux/task722/games.jsonl').read_bytes()).hexdigest(),reference_read_here=False,new_go=0,scope='ALLinitial+endpoint32cells perprofile onpreassignedNEW8devfamilies/twofixedRNG, allmean/H12/H24/commonfast/terminal/family omissions. Models/endpointshavefrozenbeforephysicaldev; quantitativegain table beforeanydescriptive reference. Independent723fullphysicalaudit required forfinalclaim. 719changedmechanicscoverage premise: root/RNG distribution changes, exploratory methodselection; allnewendpointsscoresfrozen, no same-rootA/Bcontrol.');(O/'score_table_frozen.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(start=m['start'],accepted=m['accepted'],gains={x['metric']:x['gain'] for x in m['metrics']}) for m in models]))
