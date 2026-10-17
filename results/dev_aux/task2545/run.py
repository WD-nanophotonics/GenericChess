"""Offline frozen-theta candidate-clock diagnostic. No search/price deployment."""
from pathlib import Path
from collections import defaultdict,Counter
from math import tanh,sqrt,isclose
import json,time,hashlib,datetime
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2545');T=Path('results/dev_aux/task2539')
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def mean(vs):return [sum(v[j]for v in vs)/len(vs)for j in range(6)]
def norm(v):return sqrt(dot(v,v))
def stat(rows):
 ds=[r['delta']for r in rows];m=mean(ds);return dict(n=len(rows),mean=m,norm=norm(m),vector_rms_deviation=sqrt(sum(dot([a-b for a,b in zip(v,m)],[a-b for a,b in zip(v,m)])for v in ds)/len(ds)),zeros=sum(norm(v)==0 for v in ds),unknown=sum(r['outcome']is None for r in rows),no_observations=sum(r['observations']==0 for r in rows),terms=sum(r['terms']for r in rows))
def loss(w,samples):
 return sum((float(v)if terminal else tanh(dot(w,phi)/10)-target)**2/2 if False else ((float(v)if terminal else tanh(dot(w,phi)/10))-target)**2/2 for phi,v,terminal,target in samples)
def run():
 start=time.perf_counter();p=json.loads((D/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop();games={r['gameid']:r for l in(T/'games.jsonl').open()if(r:=json.loads(l))['method']=='WDL'};qs=defaultdict(list);counts=Counter()
 for line in(T/'queries.jsonl').open():
  q=json.loads(line);counts['all_queries_scanned']+=1
  if q['method']=='WDL':
   counts['WDL_queries']+=1
   if q['actor']==q['color']and q['complete']:qs[q['gameid']].append(q)
  if counts['all_queries_scanned']%4096==0:stop()
 groups=defaultdict(lambda:defaultdict(list));out=[];fd=[];maxdiff=0.;maxgrad=0.
 for gid,g in games.items():
  w=g['initial_weights'];m=FreeModel(w);rows=[]
  for q in qs[gid]:
   assert q['weights']==w and q['actor']==g['color'];v=tanh(q['value']/10);phi=q['pv_phi'];term=q['pv_terminal'];grad=[0.]*6 if term else list(m.gradient(phi))
   if not term:assert isclose(v,m.prediction(phi),abs_tol=1e-12)
   rows.append((v,phi,term,grad))
  es=[];delta=[0.]*6;elig=[0.]*6
  for i,(v,phi,term,grad)in enumerate(rows):
   target=rows[i+1][0]if i+1<len(rows)else g['outcome']
   if target is None:break
   e=target-v;es.append(e);elig=[p['lam']*a+b for a,b in zip(elig,grad)];delta=[a+p['eta']*e*b for a,b in zip(delta,elig)]
  reverse=[0.]*6;future=0.;samples=[]
  for i in reversed(range(len(es))):
   future=es[i]+p['lam']*future;v,phi,term,grad=rows[i];reverse=[a+p['eta']*future*b for a,b in zip(reverse,grad)];samples.append((phi,v,term,v+future))
  err=max([abs(a-b)for a,b in zip(delta,reverse)],default=0.);maxdiff=max(maxdiff,err);assert err<1e-11
  # All games independently differentiated against their frozen lambda targets.
  h=1e-5;numeric=[]
  for j in range(6):
   a=list(w);b=list(w);a[j]+=h;b[j]-=h;numeric.append(-(loss(a,samples)-loss(b,samples))/(2*h)*p['eta'])
  ge=max([abs(a-b)for a,b in zip(delta,numeric)],default=0.);maxgrad=max(maxgrad,ge);assert ge<2e-8
  row={k:g[k]for k in('gameid','generator_seed','seed','block','treatment','family','color','outcome','ending','nodes')};row.update(weights=w,delta=delta,reverse=reverse,observations=len(rows),terms=len(es),fixed_target_loss=loss(w,samples),gradient_max_error=ge)
  out.append(row);groups[g['generator_seed'],g['seed'],g['block'],g['treatment']][g['color']].append(row)
 with(D/'games.jsonl').open('x')as f:
  for row in out:f.write(json.dumps(row,separators=(',',':'))+'\n')
 cells=[];cnt=Counter()
 for key,roles in groups.items():
  s0=stat(roles[0])if roles[0]else None;s1=stat(roles[1])if roles[1]else None;ws={tuple(r['weights'])for rr in roles.values()for r in rr};assert len(ws)==1
  complete=s0 is not None and s1 is not None and s0['n']==s1['n']==4 and {r['family']for r in roles[0]}=={r['family']for r in roles[1]}
  cell=dict(key=key,weights=list(next(iter(ws))),complete_four_family_pair=complete,roles=[s0,s1])
  if s0 and s1:
   a=s0['mean'];b=s1['mean'];d=[(x+y)/2 for x,y in zip(a,b)];n0=norm(a);n1=norm(b);u=dot(a,d);v=dot(b,d);co=dot(a,b)/(n0*n1)if n0*n1 else None
   cell.update(mixed=d,d0_dot_d=u,d1_dot_d=v,cosine=co,negative_mixed_role0=u<0,negative_mixed_role1=v<0,scope='equal-role mean matches complete WDL block sampling; off-policy counterfactual TD on fixed TRAIN trajectories, not actual TD endpoint distribution or WDL gradient')
   if complete:
    cnt['complete_cells']+=1;cnt['negative_cosine']+=co is not None and co<0;cnt['negative_mixed_role0']+=u<0;cnt['negative_mixed_role1']+=v<0;cnt['both_positive']+=u>0 and v>0;cnt['zero_role_mean']+=n0==0 or n1==0;cnt['negative_cosine_but_both_positive']+=co is not None and co<0 and u>0 and v>0
  else:cnt['missing_role_cells']+=1
  cells.append(cell)
 (D/'cells.json').write_text(json.dumps(cells,indent=2));agg={}
 for gs in sorted({r['generator_seed']for r in out}):
  agg[str(gs)]={str(c):stat([r for r in out if r['generator_seed']==gs and r['color']==c])for c in(0,1)}
 result=dict(status='PASS_FROZEN_TRAIN_REUSE_DIAGNOSTIC',games=len(out),observations=sum(r['observations']for r in out),terms=sum(r['terms']for r in out),unknown=sum(r['outcome']is None for r in out),zero_game_vectors=sum(norm(r['delta'])==0 for r in out),cells=len(cells),counts=dict(cnt),incomplete_cells=sum(not c['complete_four_family_pair']for c in cells),max_forward_reverse_error=maxdiff,max_finite_difference_error=maxgrad,finite_difference_games=len(out),scanned=dict(counts),by_rule=agg,seconds=time.perf_counter()-start,pins={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in [T/'games.jsonl',T/'queries.jsonl',D/'plan.json',Path(__file__)]},scope='All existing WDL TRAIN trajectories, no new game/node or updates deployed. Four-family means limited/no population stability. Incomplete cells and UNKNOWN retained. No causal color/representation diagnosis or price selection; same full state cannot observe both learner roles. Aggregate across different theta descriptive only.')
 (D/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('pins','by_rule')}))
if __name__=='__main__':run()
