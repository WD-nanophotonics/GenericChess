import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task703';assert json.loads((R/'results/dev_aux/task702/result.json').read_bytes())['status']=='PASS_ALL_ACTUAL_12_AXIS_ROLLBACKS'
p=R/'results/dev_aux/task701';r=json.loads((p/'result.json').read_bytes());gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];by={n:[gs[s['line']-1] for s in row['batch']['sources']] for row in r['rows'] for n in row['names']};axes=json.loads((R/'results/dev_aux/task700/declaration.json').read_bytes())['axes'];out=[]
def v(g,m):
 if m=='q12':return F(g['quantity12'],19)
 if m=='q24':return F(g['quantity24'],19)
 if m=='mean':return F(g['quantity12']+g['quantity24'],38)
 w=g['termination']['winner']
 if w is None:return F(0)
 if m=='terminal':return F(32 if w==g['color'] else -32)
 return F(25-len(g['actions']),25) if w==g['color'] else F(-1)
def paired(aa,bb):
 assert len(aa)==len(bb)==64;assert [(g['root'],g['replica'],g['color']) for g in aa]==[(g['root'],g['replica'],g['color']) for g in bb];rows=[]
 for m in ['q12','q24','mean','fast','terminal']:
  dif=[v(y,m)-v(x,m) for x,y in zip(aa,bb)];fam=sorted({g['root']['source_family'] for g in aa});rows.append(dict(metric=m,gain=str(sum(dif)/64),negative_cells=sum(z<0 for z in dif),positive_cells=sum(z>0 for z in dif),by_replica=[dict(replica=i,gain=str(sum(z for z,g in zip(dif,aa) if g['replica']==i)/32)) for i in [0,1]],by_family=[dict(family=f,gain=str(sum(z for z,g in zip(dif,aa) if g['root']['source_family']==f)/4)) for f in fam]))
 return rows
for label in ['A','B']:
 for start in ['unit','random2514']:
  name=label+'-'+start;ep=by[name+'-endpoint'];initial=by[start+'-initial'];out.append(dict(method=label,start=start,endpoint_vs_initial=paired(initial,ep),rollbacks=[dict(axis=a,rollback_vs_endpoint=paired(ep,by[name+'-rollback-'+str(a)]),rollback_vs_initial=paired(initial,by[name+'-rollback-'+str(a)]),unchanged=ep[0]['weights']==by[name+'-rollback-'+str(a)][0]['weights']) for a in axes]))
res=dict(status='ALL48_ROLLBACKS_FIVE_METRICS_FROZEN',models=out,source_sha256=hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest(),new_go=0,scope='ALL4models/12axes under16previouslyexposedordinaryfamilies/twoNEWdraws bothcolors. No select/fit using scores or human labels; marginalrollback in learned vector isinteraction-context dependent, notglobalaxisvalue contribution. ALLnegativecells/families retained, samephysicalcaller, notcleanexclusive timing orfinalWDL.');(O/'result.json').write_text(json.dumps(res,indent=2),encoding='utf-8');print(json.dumps([dict(method=x['method'],start=x['start'],ep={m['metric']:m['gain'] for m in x['endpoint_vs_initial']},changed_axes=sum(not z['unchanged'] for z in x['rollbacks'])) for x in out]))
