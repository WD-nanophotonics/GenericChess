from pathlib import Path
import json,random,collections,hashlib,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1503';O.mkdir(exist_ok=False);old=json.loads((R/'results/dev_aux/task1498/study.json').read_bytes());G=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));index={s:i for i,s in enumerate(states)};data=json.loads((G/'values.json').read_bytes());v=data['value'];rank=data['rank'];edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').read_text().splitlines()]
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1490/tiny_rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
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
exposed={min(orbit(i)) for f in old['families'] for i in f['state_ids']};groups={}
for i,s in enumerate(states):
 if 9 in s[:6] or len(edges[i])<2 or len({-v[j] for u,j in edges[i]})<2 or any(v[j]==-1 and rank[j]==0 for u,j in edges[i]):continue
 oo=orbit(i);key=min(oo)
 if key in exposed:continue
 groups[key]=oo
rng=random.Random(2026620000);keys=sorted(groups);rng.shuffle(keys);assert len(keys)>=192;fam=[]
for n,key in enumerate(keys[:192]):
 oo=groups[key];i=rng.choice(oo);j=index[transform(states[i],2,False,True)];assert i!=j
 fam.append({'family':n,'phase':'TRAIN' if n<128 else 'DEV','full_orbit_id':key,'all_symmetry_ids':oo,'state_ids':[i,j],'fens':[T.fen(states[k]) for k in [i,j]]})
plan=dict(old,families=fam,family_basis='FULL D4xcolorswap orbits assigned before choices, excluding all165previously used fullorbits; each selectedorbit two predetermined180+colorswap representatives. Seed2026620000. Graphlabels define conflictmu, never candidate/humanprices.',eligible_families=len(groups),excluded_exposed_full_orbits=len(exposed),correction='Old1498 incomplete180color split has12crosssplitfullorbits: preserved/downgraded, not repaired retroactively. Freshstudy new unexposed orbits, no old outcomes/rerununtilsuccess.',selection='TRAIN-only eachbudgetglobal lowesttie; NEW1505selector then DEVunion dedup. Three simultaneous primary ownminus720 gains, zero-gain means sameconfig not equivalence.');(O/'study.json').write_text(json.dumps(plan,indent=2));print('NEW_FULL_ORBIT eligible',len(groups),'exposed excluded',len(exposed),'TRAIN128 DEV64')
# Copy runners/selectors to new immutable source names, not overwrite executed old sources or results.
src=(R/'results/dev_aux/task1490/tiny_runner.py').read_text(encoding='utf-8-sig').replace('task1498/study.json','task1503/study.json').replace('task1500/selection.json','task1505/selection.json');(R/'results/dev_aux/task1490/tiny_runner_full_orbits.py').write_text(src)
src=(R/'results/dev_aux/task1490/tiny_select.py').read_text(encoding='utf-8-sig').replace('task1500','task1505').replace('task1498/study.json','task1503/study.json').replace('task1499/choices.jsonl','task1504/choices.jsonl');(R/'results/dev_aux/task1490/tiny_select_full_orbits.py').write_text(src)
