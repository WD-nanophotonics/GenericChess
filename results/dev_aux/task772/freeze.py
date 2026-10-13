import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task772';ep=json.loads((R/'results/dev_aux/task763/endpoints.json').read_bytes());r=json.loads((R/'results/dev_aux/task764/result.json').read_bytes());ss={n:[json.loads(t) for t in (R/f'results/dev_aux/task{n}/games.jsonl').open(encoding='utf-8')] for n in [744,750,764]};freeze=json.loads((R/'results/dev_aux/task762/all_endpoints_frozen.json').read_bytes());assert freeze['before_any_new_development'] and r['status']=='COMPLETE';models=[]
def val(g,m):
 if m=='fitness12':
  q=g['quantity12'];w=g['termination']['winner'];return F((q>0)-(q<0)) if len(g['actions'])>12 or g['termination']['kind'].startswith('cap') else F(0 if w is None else 1 if w==g['color'] else -1)
 if m=='qty12':return F(g['quantity12'],19)
 if m=='qty24':return F(g['quantity24'],19)
 if m=='meanqty':return F(g['quantity12']+g['quantity24'],38)
 w=g['termination']['winner']
 if m=='royalfirst_sign24':return F((g['quantity24']>0)-(g['quantity24']<0)) if g['termination']['kind'].startswith('cap') else F(0 if w is None else 1 if w==g['color'] else -1)
 if w is None:return F(0)
 if m=='terminal':return F(32 if w==g['color'] else -32)
 return F(25-len(g['actions']),25) if w==g['color'] else F(-1)
for e in ep['endpoints']:
 a=next(x['batch'] for x in r['rows'] if e['start']+'-initial' in x['names']);b=next(x['batch'] for x in r['rows'] if e['start']+'-endpoint' in x['names']);aa=[ss[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in a['sources']];bb=[ss[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in b['sources']];assert len(aa)==len(bb)==16 and [(g['root'],g['color']) for g in aa]==[(g['root'],g['color']) for g in bb];metrics=[]
 for m in ['fitness12','royalfirst_sign24','qty12','qty24','meanqty','fast','terminal']:
  diff=[val(y,m)-val(x,m) for x,y in zip(aa,bb)];families=sorted({g['root']['source_family'] for g in aa});metrics.append(dict(metric=m,gain=str(sum(diff)/16),initial_mean=str(sum(val(x,m) for x in aa)/16),endpoint_mean=str(sum(val(x,m) for x in bb)/16),negative_cells=sum(z<0 for z in diff),by_family=[dict(family=f,gain=str(sum(z for z,g in zip(diff,aa) if g['root']['source_family']==f)/2)) for f in families],leave_one=[dict(omit=f,gain=str(sum(z for z,g in zip(diff,aa) if g['root']['source_family']!=f)/14)) for f in families]))
 models.append(dict(start=e['start'],initial=e['initial'],endpoint=e['endpoint'],accepted=sum(F(u['accepted_gain'])>0 for u in ep['updates'] if u['start']==e['start']),metrics=metrics))
out=dict(status='ALL_TERMINAL_GUARDED_DEV_SCORES_FROZEN',models=models,source_sha256={str(n):hashlib.sha256((R/f'results/dev_aux/task{n}/games.jsonl').read_bytes()).hexdigest() for n in [744,750,764]},reference_read_here=False,new_go=0,scope='ALL16preassigned7408devfamilies nowEXPOSED, fullvectorqualified744750reuse explicit; guard protectsTRAINH12only, no blindmethodvalidation. ALL16cells/fixedunit perprofile, allendpoints beforedev; ALLgoals/quantities/H24/fast/terminal/negativefamilies beforedescriptive reference. Independent765physicalaudit requiredbeforevalidatedclaim. No fakeRNGreplicates/equal-time/wholegameWDL/humanpriceproof.');(O/'score_table_frozen.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(start=m['start'],accepted=m['accepted'],gains={x['metric']:x['gain'] for x in m['metrics']}) for m in models]))
