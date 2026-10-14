from pathlib import Path
import json,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1660';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
oldplans=[json.loads((R/f'results/dev_aux/task{x}/plan.json').read_bytes()) for x in [1630,1633,1640,1651]]
seen={min(tuple(s) for s in f['orbit_states']) for p in oldplans for f in p['families']};rng=random.Random(2026681600);families=[];attempts=0;pairs=[(1,2,7),(1,3,6),(2,3,5)]
def orbit(s):
 out=[]
 for swap in [False,True]:
  for fx in [False,True]:
   for fy in [False,True]:
    a=[]
    for z in s[:8]:
     if z==16:a.append(16);continue
     x,y=z%4,z//4
     if swap:x,y=y,x
     a.append((3-x if fx else x)+4*(3-y if fy else y))
    out.extend([tuple(a+[s[8]]),tuple(a[4:]+a[:4]+[1-s[8]])])
 return sorted(set(out))
while len(families)<256:
 attempts+=1;f=len(families);a,b,c=pairs[(f//2)%3]
 if f%2:a,b,c=a+4,b+4,c-4
 positions=rng.sample(range(16),5);s=[16]*8
 for i,p in zip([0,4,a,b,c],positions):s[i]=p
 s=tuple(s+[0])
 if max(abs(s[0]%4-s[4]%4),abs(s[0]//4-s[4]//4))>2 or not T.valid(s) or not T.attacked(s,s[0],1):continue
 ll=T.moves(s)
 if len(ll)<2 or any(not T.moves(t) and T.attacked(t,t[4*t[8]],1-t[8]) for u,t in ll):continue
 oo=orbit(s);key=min(oo)
 if key in seen:continue
 seen.add(key);q=rng.choice([t for t in oo if t[8]==0]);other=q[4:8]+q[:4]+(1-q[8],)
 assert sum(x!=16 for x in q[:4])== (3 if f%2==0 else 2)
 families.append({'family':f,'phase':'TRAIN1' if f<64 else 'TRAIN2' if f<128 else 'DEV','stock':('OWN2_' if f%2==0 else 'OWN1_')+['RNvsB','RBvsN','NBvsR'][(f//2)%3],'orbit_states':oo,'roots':[q,other]})
plan=dict(oldplans[-1]);plan.update({'status':'FROZEN_BALANCED_ROLES_NEW_ORBITS_BEFORE_QUERIES','families':families,'seed':2026681600,'attempts':attempts,'root_exclusions':['task1630','task1633','task1640','task1651'],'rootlaw':'Activecandidate one/twononkings equalbyparity:32each perTRAIN64 and64each DEV128, otherwisesamepressurelaw. BothKingswithinCheby2, activeKingchecked>=2evasions, noimmediatewinmate; priceblindroot selection, randomD4white representative+colorpair. Changedrootlaw notsamecohortreplication.','expected_seconds':700})
(O/'plan.json').write_text(json.dumps(plan,indent=2));print('FROZEN_BALANCED',len(families),attempts)
s=(R/'results/dev_aux/task1639/physical_train.py').read_text(encoding='utf-8-sig').replace("task1652'","task1661'").replace('task1651/plan.json','task1660/plan.json')
s=s.replace("sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))","sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1652').glob('*choices.jsonl'))")
(R/'results/dev_aux/task1639/balanced_train_fixed.py').write_text(s,encoding='utf8')
for i,reason in [(1658,'OriginalpreparedgeneratorNameError positions initializedinsideoddrole branch, beforefirstroot query; preserve source, new fixedstandalone1660 succeeds.'),(1659,'Notexecuted because1658preparation failed; nolearning source/generatedplan/noenginequery.')]:
 d=R/f'results/dev_aux/task{i}';d.mkdir(exist_ok=True);(d/'failure.json').write_text(json.dumps({'status':'PREQUERY_FAILURE_OR_UNEXECUTED','reason':reason,'actual_go':0},indent=2))

