import json,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task572';start=time.perf_counter();axes=[2,3,4,5,6,7,9,10,11,12,13,14];MAP={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8}
def features(sfen):
 board,turn,hand,num=sfen.split();v=[0]*16;prom=False
 for x in board:
  if x=='+':prom=True;continue
  if x=='/' or x.isdigit():continue
  v[MAP[x.upper()]+(8 if prom else 0)]+=1 if x.isupper() else -1;prom=False
 n=''
 for x in hand:
  if x=='-':continue
  if x.isdigit():n+=x;continue
  v[MAP[x.upper()]]+=(int(n or '1') if x.isupper() else -int(n or '1'));n=''
 return v
rows=[]
for task,route,opp in [(554,'pure24','unit'),(555,'pure24','random'),(565,'mixed12','unit'),(566,'mixed12','random')]:
 seen={a:set() for a in axes};changed={a:set() for a in axes};changes={a:0 for a in axes};nonzero={a:0 for a in axes};states=0
 for line in (R/f'results/dev_aux/task{task}/games.jsonl').open():
  g=json.loads(line);seed=g['root']['seed'];v=features(g['root']['expected_sfen']);states+=1
  for a in axes:
   if v[a]:seen[a].add(seed);nonzero[a]+=1
  for ac in g['actions']:
   nv=features(ac['after_sfen']);states+=1
   for a in axes:
    if nv[a]:seen[a].add(seed);nonzero[a]+=1
    if nv[a]!=v[a]:changed[a].add(seed);changes[a]+=1
   v=nv
 rows.append(dict(route=route,opponent=opp,played_states=states,signed_feature_nonzero_states=nonzero,signed_feature_changed_actions=changes,families_nonzero={a:sorted(seen[a]) for a in axes},families_changed={a:sorted(changed[a]) for a in axes}))
out=dict(status='PASS_SIGNED_FEATURE_DIAGNOSIS',rows=rows,new_go=0,seconds=time.perf_counter()-start,scope='Owner-signedboard+hand count features distinct from571totaltypeoccupancy. Goldgrandtotalconserved DOESNOTimply Goldpriceunidentifiable: captures/dropownership affect signedfeatures. Presence/change/rank notfitnessidentifiability orcausalparameter recovery; no referencefit orselectedroot.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}));print([{k:r[k] for k in ['route','opponent','signed_feature_changed_actions']} for r in rows])
