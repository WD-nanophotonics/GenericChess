import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task733';assert json.loads((R/'results/dev_aux/task732/result.json').read_bytes())['status']=='PASS_ALL_ACTUAL_FIXED_UNIT_OPPONENT_PROBES';p=R/'results/dev_aux/task731';r=json.loads((p/'result.json').read_bytes());gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];by={(pool,n):[gs[x['line']-1] for x in row['batch']['sources']] for row in r['rows'] for pool in [row['pool']] for n in row['names']};models=[]
def val(g,m):
 if m=='q12':return F(g['quantity12'],19)
 if m=='q24':return F(g['quantity24'],19)
 if m=='mean':return F(g['quantity12']+g['quantity24'],38)
 w=g['termination']['winner']
 if w is None:return F(0)
 if m=='terminal':return F(32 if w==g['color'] else -32)
 return F(25-len(g['actions']),25) if w==g['color'] else F(-1)
for pool in ['quiet','rich']:
 for label in ['A','B','C']:
  for start in ['unit','random2514']:
   aa=by[(pool,start+'-initial')];bb=by[(pool,label+'-'+start+'-endpoint')];assert len(aa)==len(bb)==16 and [(g['root'],g['color']) for g in aa]==[(g['root'],g['color']) for g in bb];metrics=[]
   for metric in ['q12','q24','mean','fast','terminal']:
    dd=[val(y,metric)-val(x,metric) for x,y in zip(aa,bb)];metrics.append(dict(metric=metric,gain=str(sum(dd)/16),negative_cells=sum(x<0 for x in dd),by_family=[dict(family=f,gain=str(sum(z for z,g in zip(dd,aa) if g['root']['source_family']==f)/2)) for f in sorted({g['root']['source_family'] for g in aa})]))
   models.append(dict(pool=pool,method=label,start=start,metrics=metrics))
out=dict(status='ALL12_MODEL_POOL_FIXED_OPPONENT_SCORES_FROZEN',models=models,source_sha256=hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest(),new_go=0,scope='All6endpoints/twooriginalinitials onALL8quiet+8richpreassigneddevfamilies bothcolors, fixedunitprice samebackend1024BOTHplayers. Actualunitopponent notrandom, no fakeRNGreplicates. Frozen730plan beforeCrichfitends; method/rootpoolsalreadyexposed, exploratory transfernotblindvalidation. No modelselection/refit/defaultupdates; allnegative/terminal/unknown kept. NotfullmatureNNUE opponent orwholegameWDL.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(pool=m['pool'],method=m['method'],start=m['start'],gains={x['metric']:x['gain'] for x in m['metrics']}) for m in models]))
