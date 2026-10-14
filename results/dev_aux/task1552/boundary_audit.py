from pathlib import Path
import json,collections,sys
R=Path.cwd();O=R/'results/dev_aux/task1554';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1538';s=json.loads((G/'states.json').read_bytes());orig=json.loads((G/'values.json').read_bytes())['value'];es=[json.loads(z) for z in (G/'edges.jsonl').open()];edges=[x['moves'] for x in es];cache={};counts=collections.Counter()
for line in (R/'results/dev_aux/task1539/choices.jsonl').open():
 x=json.loads(line);cache.setdefault((x['node_budget'],x['leafR']),{})[x['state_id']]=x['child_id']
for (b,p),pol in cache.items():
 for color in [0,1]:
  B=json.loads((R/f'results/dev_aux/task1553/B{b}_R{p}_C{color}.json').read_bytes());A=json.loads((R/f'results/dev_aux/task1555/B{b}_R{p}_C{color}.json').read_bytes());v=B['value'];rank=B['rank']
  for i,z in enumerate(s):
   sign=1 if z[6]==color else -1;cv=v[i]*sign;assert cv>=A['value'][i]*sign and cv<=orig[i]*sign
   if sum(x!=12 for x in z[:6])<=3:assert v[i]==orig[i] and rank[i]==0;counts['exact_boundary_states']+=1;continue
   adj=[pol[i]] if z[6]==color and edges[i] else [j for u,j in edges[i]];child=[v[j]*(1 if s[j][6]==color else -1) for j in adj]
   if not adj:assert v[i]==(-1 if es[i]['checked'] else 0) and rank[i]==0
   elif z[6]==color:
    assert len(adj)==1 and cv==child[0]
    if cv:assert rank[adj[0]]<rank[i]
   else:
    assert cv==min(child)
    if cv==1:assert all(rank[j]<rank[i] for j in adj)
    elif cv==-1:assert any(child[k]==-1 and rank[j]<rank[i] for k,j in enumerate(adj))
   if cv==0 and adj:assert child[0]==0 if z[6]==color else all(y>=0 for y in child) and 0 in child
   counts['nonboundary_candidate_centric_states']+=1
out={'status':'PASS_INDEPENDENT_SHARED_BOUNDARY_CANDIDATE_CENTRIC_PROOFS','counts':dict(counts),'new_go':0,'scope':'All12budget/price/color solutions, boundaryexactoriginalWDL, ownoneactualcachededge/opminALL, strictabstractrank anddrawsafety. Allstates B>=pureA candidateframe andB<=perfectgame. Ranks tocutoffboundary NOT realmate lengths.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
