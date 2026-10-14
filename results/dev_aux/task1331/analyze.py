from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1331'
source=R/'results/dev_aux/task1329'
assert json.loads((source/'result.json').read_bytes())['complete']
gs=[json.loads(v) for v in (source/'games.jsonl').read_text().splitlines()]
by={p:{} for p in 'BJLO'}
for g in gs:by[g['arm']][(g['root']['seed'],g['color'],g['opponent'])]=g
assert all(set(x)==set(by['B']) for x in by.values()) and len(by['B'])==256
seeds=sorted({k[0] for k in by['B']});assert len(seeds)==64
y=lambda g:F((g['label']=='W')-(g['label']=='L'))
coeff={'joint':dict(J=1,B=-1),'leaf':dict(L=1,B=-1),'native_compound':dict(O=1,B=-1),'interaction':dict(J=1,L=-1,O=-1,B=1)}
rows=[]
for wstr in ['0','1/2','1']:
 w=F(wstr)
 for effect,cc in coeff.items():
  fd={}
  for s in seeds:
   fd[s]=sum((w if opp=='unit_search' else 1-w)*sum(sum(a*y(by[p][s,c,opp]) for p,a in cc.items()) for c in [False,True])/2 for opp in ['unit_search','uniform_random'])
  mean=sum(fd.values())/64;rng=random.Random(2026379500);fv=[float(v) for v in fd.values()];boot=sorted(sum(rng.choices(fv,k=64))/64 for _ in range(5000))
  rows.append(dict(weight=wstr,effect=effect,mean=str(mean),bootstrap95=[boot[124],boot[4874]],family_deltas={s:str(v) for s,v in fd.items()}))
counts={p:{opp:dict(collections.Counter(g['label'] for k,g in bb.items() if k[2]==opp)) for opp in ['unit_search','uniform_random']} for p,bb in by.items()}
work={}
for p,bb in by.items():
 qq=[q for g in bb.values() for q in g['queries']]
 last=[]
 for q in qq:
  ll=[l.split() for l in q['metadata']['uci_info'] if ' nodes ' in l]
  if ll:last.append(ll[-1])
 work[p]=dict(search_go=len(qq),actual_reported_last_nodes=sum(int(l[l.index('nodes')+1]) for l in last),mean_last_depth=sum(int(l[l.index('depth')+1]) for l in last)/len(last),plies=sum(len(g['actions']) for g in bb.values()))
out=dict(status='PROSPECTIVE64_TRUE_WL_FACTORIAL',rows=rows,counts=counts,work=work,scope=json.loads((O/'plan.json').read_bytes()),producer=json.loads((source/'result.json').read_bytes())|{'rows':'stored original'})
(O/'result.json').write_text(json.dumps(out,indent=2));print(counts);print([{k:v for k,v in r.items() if k!='family_deltas'} for r in rows]);print(work)
