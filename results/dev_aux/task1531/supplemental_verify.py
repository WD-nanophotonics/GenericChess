from pathlib import Path
import json,random,importlib.util
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1572';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1532';s=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={z:i for i,z in enumerate(s)};v=json.loads((G/'values.json').read_bytes())['value'];sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
counts={}
for tid in [1547,1550]:
 n=0;pv=0
 for line in (R/f'results/dev_aux/task{tid}/choices.jsonl').open():
  x=json.loads(line);z=s[x['state_id']];m=dict(T.moves(z));assert ix[m[x['move']]]==x['child_id'] and x['chosen_WDL']==-v[x['child_id']] and x['position']=='position fen '+T.fen(z);n+=1
  for line in x['uci_info']:
   fs=line.split()
   if 'pv' in fs:
    q=z
    for u in fs[fs.index('pv')+1:]:mm=dict(T.moves(q));assert u in mm;q=mm[u];pv+=1
  if tid==1547:assert x['leafN']==int(720*x['scale']) and x['leafR']==int(720*x['scale']*x['ratio'])
 counts[tid]={'queries':n,'PVmoves':pv}
xs=[json.loads(z) for z in (R/'results/dev_aux/task1550/choices.jsonl').open()];old=json.loads((R/'results/dev_aux/task1558/result.json').read_bytes());vectors={}
for b in [64,256]:
 dd=[F(sum(x['chosen_WDL'] for x in xs if x['node_budget']==b and x['family']==f and x['leafR']==1728)-sum(x['chosen_WDL'] for x in xs if x['node_budget']==b and x['family']==f and x['leafR']==720),2) for f in range(128)];vv=list(map(float,dd));vectors[b]=vv;row=next(x for x in old['rows'] if x['budget']==b);assert str(sum(dd)/128)==row['mean'];rng=random.Random(2026672500+b);bs=sorted(sum(rng.choices(vv,k=128))/128 for j in range(10000));assert [bs[249],bs[9749]]==row['bootstrap95']
means={b:sum(z)/128 for b,z in vectors.items()};rng=random.Random(2026672503);mx=[]
for j in range(10000):
 ss=[rng.randrange(128) for i in range(128)];mx.append(max(abs(sum(z[i] for i in ss)/128-means[b]) for b,z in vectors.items()))
mx.sort();radius=mx[9499];assert {str(b):[m-radius,m+radius] for b,m in means.items()}==old['simultaneous2_95']
kept=json.loads((R/'results/dev_aux/task1538/original_ids.json').read_bytes());assert kept==[i for i,z in enumerate(s) if sum(x!=12 for x in z[:6])<=4] and [s[i] for i in kept]==list(map(tuple,json.loads((R/'results/dev_aux/task1538/states.json').read_bytes())))
(O/'result.json').write_text(json.dumps({'status':'PASS_SAVED_RECONSTRUCTION_OF_SUPPLEMENTAL_AUDITS_STATISTICS_AND_SUBSET','counts':counts,'subset_states':len(kept),'cooperation_allmeans_CIs_jointbands_exactly_reproduced':True,'scope':'Savedpostexecutionindependentverification, nothistoricalinlinebytes; no enginequeries orhumanfit'},indent=2));print(counts,'jointstatistics exact')
