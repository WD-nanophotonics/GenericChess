from pathlib import Path
import json,math,itertools,collections,time,chess
R=Path('results/dev_aux');A=R/'task2521';OUT=R/'task2523'
def rank(matrix,tol=1e-10):
 a=[list(map(float,row))for row in matrix];n=len(a);j=0
 for col in range(4):
  k=next((k for k in range(j,n)if abs(a[k][col])>tol),None)
  if k is None:continue
  a[j],a[k]=a[k],a[j];v=a[j][col];a[j]=[x/v for x in a[j]]
  for k in range(n):
   if k!=j:
    v=a[k][col];a[k]=[x-v*y for x,y in zip(a[k],a[j])]
  j+=1
  if j==n:break
 return j
class Coverage:
 def __init__(self):self.n=0;self.nz=0;self.gram=[[0.]*4 for _ in range(4)];self.sq=0.
 def add(self,x):
  self.n+=1;self.nz+=any(abs(v)>1e-12 for v in x);self.sq+=sum(v*v for v in x)
  for i in range(4):
   for j in range(4):self.gram[i][j]+=x[i]*x[j]
 def result(self):return dict(count=self.n,nonzero=self.nz,rank=rank(self.gram),RMSnorm=math.sqrt(self.sq/max(1,self.n)),gram=self.gram)
def consistency(vectors):
 pairs=list(itertools.combinations(vectors,2));dist=math.sqrt(sum(sum((a-b)**2 for a,b in zip(x[1:],y[1:]))/4 for x,y in pairs)/len(pairs));agree=[]
 for i,j in itertools.combinations(range(1,5),2):
  signs=[0 if abs(w[i]-w[j])<1e-12 else 1 if w[i]>w[j]else-1 for w in vectors];agree.append(dict(pair=[i,j],signs=signs,agreement=sum(a==b for a,b in itertools.combinations(signs,2))/len(pairs)))
 return dict(pairwise_free_coordinate_RMS=dist,mean_pair_order_agreement=sum(x['agreement']for x in agree)/6,orders=agree,weights=vectors)
def run():
 start=time.perf_counter();p=json.loads((A/'plan.json').read_text());done=json.loads((A/'result.json').read_text());eps=[json.loads(x)for x in(A/'episodes.jsonl').read_text().splitlines()];cov=collections.defaultdict(Coverage);term=collections.Counter();details=[]
 for ep in eps:
  b=chess.Board(ep['initial_record']['initial'])
  for u in ep['initial_record']['moves']:b.push_uci(u)
  phi=[len(b.pieces(t,True))-len(b.pieces(t,False))for t in range(2,6)];cov[(ep['method'],'episode_start')].add(phi);term[(ep['method'],'start_terminal')]+=b.outcome(claim_draw=True)is not None
  details.append(dict(seed=ep['seed'],method=ep['method'],game=ep['game'],prefix_plies=len(ep['initial_record']['moves']),pieces=len(b.piece_map()),phi=phi,terminal=b.outcome(claim_draw=True)is not None))
 for line in(A/'decisions.jsonl').open():
  d=json.loads(line)
  if not d['complete']:continue
  b=chess.Board(d['root_fen']);phi=[len(b.pieces(t,True))-len(b.pieces(t,False))for t in range(2,6)]
  cov[(d['method'],'queried_root')].add(phi);cov[(d['method'],'returned_PV_gradient')].add(d['gradient'][1:]);term[(d['method'],'terminal_PV')]+=d['pv_terminal']
 panels=[]
 for target in(0,500000,1000000,1500000):
  for method in('p16','p64'):
   rows=[];nodes=[]
   for seed in(1977,8173,27182,31415):
    arm=next(a for a in done['arms']if(a['seed'],a['method'])==(seed,method));w=arm['initial'];n=0
    if target==1500000:w=arm['weights'];n=arm['nodes']
    elif target:
     for c in arm['checkpoints']:
      if c['nodes']<=target:w=c['weights'];n=c['nodes']
    rows.append(w);nodes.append(n)
   panels.append(dict(method=method,target_nodes=target,actual_nodes=nodes,**consistency(rows)))
 result=dict(status='PASS_DESCRIPTIVE_EXPOSURE_AND_PREDECLARED_CONSISTENCY',coverage=[dict(method=k[0],location=k[1],**v.result())for k,v in sorted(cov.items())],counts=[dict(method=k[0],event=k[1],count=v)for k,v in sorted(term.items())],starts=details,consistency=panels,scope='ActualvisitedTRAIN states underdifferentonpolicy trajectories; sameepisode seeds doNOTensure same numberofepisodes/equal states. Gramrank/RMS localdescriptors, no globalidentifiability/strength. All4fixedinitials, rawpawn1scale/freeweights; nohumanorder reference. Closedepisode snapshots belowthreshold exceptfinalincludesvalidcensoredbootstrap; no choosingbest. Original64prefix distributions includeearlieractualterminals withoutfilter. Not literalhistoricalreplication.',audit_seconds=time.perf_counter()-start)
 (OUT/'exposure-consistency.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k not in('starts','consistency')}))
if __name__=='__main__':run()
