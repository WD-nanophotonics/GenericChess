"""All-seed raw-order stability along fixed paid-node checkpoints; no labels/selection."""
from pathlib import Path
from collections import Counter
from itertools import combinations
from math import sqrt
import json
D=Path('results/dev_aux/task2558');A=Path('results/dev_aux/task2560')
def cosine(a,b):
 den=sqrt(sum(x*x for x in a)*sum(y*y for y in b));return sum(x*y for x,y in zip(a,b))/den if den else None

def run():
 t=json.loads((D/'result.json').read_text());edges=[0,50000,100000,150000,200000];models={};times={}
 for a in t['arms']:
  k=a['generator_seed'],a['method'],a['seed'];models[k]={n:list(a['initial'])for n in edges};times[k]={n:0 for n in edges}
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if not q['observed']:continue
  k=q['generator_seed'],q['method'],q['seed']
  for n in edges[1:]:
   if q['total_nodes']<=n:models[k][n]=q['weights_after'];times[k][n]=q['total_nodes']
 for a in t['arms']:
  k=a['generator_seed'],a['method'],a['seed'];assert models[k][200000]==a['weights']
 rows=[]
 for g in sorted({k[0]for k in models}):
  for m in ['Mean','CostClock']:
   kk=sorted([k for k in models if k[:2]==(g,m)])
   for n in edges:
    order={};board=Counter();hand=Counter();raw=[]
    for k in kk:
     w=models[k][n];bo=tuple(sorted(range(3),key=lambda i:(w[i],i)));ha=tuple(sorted(range(3,6),key=lambda i:(w[i],i)));board['<'.join(['P','A','X'][i]for i in bo)]+=1;hand['<'.join(['A','P','X'][i-3]for i in ha)]+=1;raw.append(dict(seed=k[2],weights=w,last_observation_nodes=times[k][n],board_exact_ties=len(set(w[:3]))<3,hand_exact_ties=len(set(w[3:]))<3))
    pair=[dict(seeds=[a[2],b[2]],cosine=cosine(models[a][n],models[b][n]))for a,b in combinations(kk,2)]
    rows.append(dict(rule=g,method=m,node_edge=n,raw=raw,board_orders=dict(board),hand_orders=dict(hand),pairwise_raw_vector_cosines=pair))
 out=dict(status='PASS_ALL_ENDPOINTS_AND_FIXED_NODEEDGE_SNAPSHOTS',rows=rows,edges=edges,scope='Descriptive all4initializations within each alreadyexposed rule; checkpoints are lastcompletecandidateobservation at/before fixed paidnodeedge, not identical visiteddata or independent samples. Raw sixfree signed weights; L2 appears only in descriptive cosine, never normalized deployment or fitting. Exact ties disclosed; order display uses IDs only to deterministically display ties. No human-price/expectedorder labels, bestseed selection, universalprice/convergence theorem or WLD inference. Diagnostic added duringTRAIN before EVAL outcomes inspected.')
 (A/'ordering.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],groups=len(rows))))
if __name__=='__main__':run()
