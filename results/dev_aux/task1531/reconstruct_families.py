from pathlib import Path
import json,random,collections
R=Path.cwd();O=R/'results/dev_aux/task1571';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1532';full=list(map(tuple,json.loads((G/'states.json').read_bytes())));val=json.loads((G/'values.json').read_bytes());all_edges=[json.loads(z)['moves'] for z in (G/'edges.jsonl').open()];out=[]
for tid,seed,n in [(1535,2026670000,64),(1538,2026671000,128),(1549,2026672000,128)]:
 P=json.loads((R/f'results/dev_aux/task{tid}/study.json').read_bytes());states=list(map(tuple,json.loads((R/P['source_graph']/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};vd=json.loads((R/P['source_graph']/'values.json').read_bytes());v=vd['value'];rank=vd['rank'];groups={};invalid=0
 def trans(s,fx,fy,c):
  pp=[]
  for k in ([3,4,5,0,1,2] if c else range(6)):
   z=s[k]
   if z==12:pp.append(z);continue
   x,y=z%3,z//3;pp.append((3-y if fy else y)*3+(2-x if fx else x))
  return tuple(pp+[1-s[6] if c else s[6]])
 for line in (R/P['source_graph']/'edges.jsonl').open():
  e=json.loads(line);i=e['id'];s=states[i];ll=e['moves']
  if tid==1535:
   if 12 in s[:6]:continue
  elif tid==1538:
   if sum(x!=12 for x in s[:3])!=2 or sum(x!=12 for x in s[3:6])!=2 or not ((s[1]!=12 and s[5]!=12) or (s[2]!=12 and s[4]!=12)):continue
  else:
   own=s[6]*3;opp=(1-s[6])*3
   if s[own+1]==12 or s[own+2]==12 or sum(x!=12 for x in s[opp:opp+3])!=2:continue
   a=list(s);a[own+1]=12;b=list(s);b[own+2]=12;aa=ix.get(tuple(a));bb=ix.get(tuple(b))
   if aa is None or bb is None:invalid+=1;continue
   if v[i]<=max(v[aa],v[bb]):continue
  if len(ll)<2 or len({-v[j] for u,j in ll})<2 or any(v[j]==-1 and rank[j]==0 for u,j in ll):continue
  oo=sorted({ix[trans(s,x,y,c)] for x in (0,1) for y in (0,1) for c in (0,1)});groups[min(oo)]=oo
 rng=random.Random(seed);keys=sorted(groups);rng.shuffle(keys);expected=[]
 for f,k in enumerate(keys[:n]):
  i=rng.choice(groups[k]);j=ix[trans(states[i],1,1,1)];expected.append((f,k,groups[k],[i,j]))
 actual=[(f['family'],f['full_orbit_id'],f['all_symmetry_ids'],f['state_ids']) for f in P['families']];assert expected==actual and len(groups)==P['eligible_families'];out.append({'task':tid,'families':n,'eligible':len(groups),'seed':seed,'all_original_frozen_family_outputs_reproduced':True,'invalid_marginals':invalid})
res={'status':'PASS_PRICE_BLIND_FAMILY_GENERATION_RECONSTRUCTION','rows':out,'scope':'Post-execution independentlysavedreconstruction code reproducesfrozenoriginaldatasets exactly usingstatedrulelabels/seed; notclaimingthesearehistoricalinlinegeneratorbytes. Originalstudy hashes bound toactualenginequeryresults; no candidate/humanprice outcomes used togeneratefamilies.'};(O/'result.json').write_text(json.dumps(res,indent=2));print(out)
