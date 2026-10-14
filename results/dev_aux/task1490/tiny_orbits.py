from pathlib import Path
import json,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1502';O.mkdir(exist_ok=False);study=json.loads((R/'results/dev_aux/task1498/study.json').read_bytes());states=list(map(tuple,json.loads((R/'results/dev_aux/task1495/states.json').read_bytes())));index={s:i for i,s in enumerate(states)}
def transform(s,rot,flip,swap):
 p=[]
 for i in ([3,4,5,0,1,2] if swap else range(6)):
  z=s[i]
  if z==9:p.append(9);continue
  x,y=z%3,z//3
  if flip:x=2-x
  for _ in range(rot):x,y=2-y,x
  p.append(y*3+x)
 return tuple(p+[1-s[6] if swap else s[6]])
def orbit(i):return sorted({index[transform(states[i],r,f,c)] for r in range(4) for f in [False,True] for c in [False,True]})
train={min(orbit(i)) for f in study['families'] if f['phase']=='TRAIN' for i in f['state_ids']};dev={min(orbit(i)) for f in study['families'] if f['phase']=='DEV' for i in f['state_ids']};overlap=train&dev;counts=collections.Counter()
for f in study['families']:counts[(f['phase'],min(orbit(f['state_ids'][0])))]+=1
out={'status':'ACTUAL_FULL_GEOMETRIC_ORBIT_OVERLAP_CHECK','TRAIN_180color_families':128,'DEV_180color_families':64,'TRAIN_full_orbits':len(train),'DEV_full_orbits':len(dev),'overlap_full_orbits':len(overlap),'overlap_ids':sorted(overlap),'affected_DEV_families':[f['family'] for f in study['families'] if f['phase']=='DEV' and min(orbit(f['state_ids'][0])) in overlap],'scope':'Current frozen split only180+colorswap. CompleteD4+color symmetries can crosssplit; preserve executedstudy/training/DEV, downgrade independence claims. New study must split entire orbits beforepricechoices; no posthoc deletingoldDEV or labelingclean.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['overlap_ids','affected_DEV_families']})
