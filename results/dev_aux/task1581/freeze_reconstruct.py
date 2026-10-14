from pathlib import Path
import json,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1600';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1583';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};v=json.loads((G/'values.json').read_bytes())['value'];edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').open()];plan=json.loads((R/'results/dev_aux/task1586/study.json').read_bytes());families={}
def orbit(s):
 out=[]
 for fx in [False,True]:
  for fy in [False,True]:
   a=[12 if z==12 else (2-z%3 if fx else z%3)+3*(3-z//3 if fy else z//3) for z in s[:8]];out.extend([tuple(a+[s[8]]),tuple(a[4:]+a[:4]+[1-s[8]])])
 return sorted(set(ix[x] for x in out))
for i,s in enumerate(states):
 if sum(x!=12 for x in s[:8])!=5 or sum(x!=12 for x in s[4*s[8]:4*s[8]+4])!=3:continue
 ll=edges[i]
 if len(ll)<2 or len({-v[j] for u,j in ll})<2 or any(v[j]==-1 and not edges[j] for u,j in ll):continue
 ids=orbit(s);families.setdefault(min(ids),ids)
keys=sorted(families);random.Random(plan['seed']).shuffle(keys);out=[]
for f,key in enumerate(keys[:plan['TRAIN']+plan['DEV']]):
 ids=families[key];a=min(i for i in ids if states[i][8]==0);s=states[a];b=ix[tuple(s[4:8]+s[:4]+(1-s[8],))];out.append({'family':f,'phase':'TRAIN' if f<64 else 'DEV','orbit_id':key,'all_symmetry_ids':ids,'state_ids':[a,b]})
assert out==plan['families'] and len(keys)==plan['eligible_family_count'];result={'status':'PASS_ALL_FROZEN_FAMILIES_INDEPENDENTLY_RECONSTRUCTED','families':len(out),'eligible':len(keys),'new_go':0,'scope':'Original1586inlinegeneratorbytes notclaimedpreserved; savedpostexecutionindependentreconstructor reproduces exact rules/filter/allorbits/seed/shuffle/TRAINDEV roots. Frozenstudy beforeanycandidatequery remains authoritative.'};(O/'result.json').write_text(json.dumps(result,indent=2));print(result)
