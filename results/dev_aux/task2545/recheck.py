"""Independent reconstruction of every saved offline role delta and group mean."""
from pathlib import Path
from math import tanh,isclose
from collections import defaultdict,Counter
import json,time
D=Path('results/dev_aux/task2545');T=Path('results/dev_aux/task2539')
def same(a,b):assert len(a)==len(b)and all(isclose(x,y,abs_tol=1e-11,rel_tol=1e-10)for x,y in zip(a,b))
def run(stop_root=None):
 from results.dev_aux.task2392.reader import SharedDeleteStopReader
 began=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();plan=json.loads((D/'plan.json').read_text());saved={r['gameid']:r for r in map(json.loads,(D/'games.jsonl').read_text().splitlines())};original={};rolecounts=defaultdict(Counter)
 for line in(T/'games.jsonl').open():
  r=json.loads(line)
  if r['method']=='WDL':original[r['gameid']]=r
  else:rolecounts[r['generator_seed'],r['seed']][r['color']]+=1
 assert original.keys()==saved.keys();obs=defaultdict(list);scanned=0
 for line in(T/'queries.jsonl').open():
  r=json.loads(line);scanned+=1
  if r['method']=='WDL'and r['complete']and r['actor']==r['color']:obs[r['gameid']].append(r)
  if scanned%4096==0:stop()
 groups=defaultdict(lambda:defaultdict(list));maxerr=0.;fd=0;terms=0
 for gid,g in original.items():
  w=g['initial_weights'];qs=obs[gid];vals=[tanh(q['value']/10)for q in qs];res=[vals[i+1]-vals[i]for i in range(len(vals)-1)]
  if vals and g['outcome']is not None:res.append(g['outcome']-vals[-1])
  targets=[];acc=0.;derivative=[0.]*6
  for i in reversed(range(len(res))):
   acc=res[i]+plan['lam']*acc;q=qs[i];v=vals[i];grad=[0.]*6 if q['pv_terminal']else[(1-v*v)*x/10 for x in q['pv_phi']];derivative=[a+plan['eta']*acc*b for a,b in zip(derivative,grad)];targets.append((q['pv_terminal'],q['pv_phi'],v,v+acc))
  row=saved[gid];same(row['delta'],derivative);assert row['terms']==len(res)and row['observations']==len(qs)and row['outcome']==g['outcome'];terms+=len(res)
  def loss(w2):return sum(((v if terminal else tanh(sum(a*b for a,b in zip(w2,phi))/10))-target)**2/2 for terminal,phi,v,target in targets)
  h=1e-5;numeric=[]
  for j in range(6):
   a=list(w);b=list(w);a[j]+=h;b[j]-=h;numeric.append(-plan['eta']*(loss(a)-loss(b))/(2*h))
  err=max(abs(a-b)for a,b in zip(numeric,derivative));maxerr=max(maxerr,err);assert err<2e-8;fd+=1;groups[g['generator_seed'],g['seed'],g['block'],g['treatment']][g['color']].append(row['delta'])
 for c in json.loads((D/'cells.json').read_text()):
  rows=groups[tuple(c['key'])]
  for color in(0,1):
   st=c['roles'][color]
   if not rows[color]:assert st is None;continue
   m=[sum(v[j]for v in rows[color])/len(rows[color])for j in range(6)];same(st['mean'],m)
 weighted=json.loads((D/'training-role-weights.json').read_text())
 for c in weighted['rows']:
  key=c['key'];n=rolecounts[key[0],key[1]];assert c['role_counts']==[n[0],n[1]];same(c['role_weights'],[n[0]/sum(n.values()),n[1]/sum(n.values())])
 out=dict(status='PASS_INDEPENDENT_ALL_REUSED_GAME_DELTAS_GROUP_MEANS_AND_ACTUAL_ROLE_WEIGHTS',games=len(saved),queries_scanned=scanned,candidate_observations=sum(len(v)for v in obs.values()),TD_terms=terms,finite_difference_games=fd,max_finite_difference_error=maxerr,cells=len(groups),actual_weight_cells=len(weighted['rows']),seconds=time.perf_counter()-began,scope='Independent finite-difference fixed-target local proxy and replay of saved arithmetic, no newsearch/priceupdate or actualWDLgradient. Original92publictypedhistoryalreadyaudited separately; currentrolecheck notexternalrulesengine/fullhistoricalrerun. Allzeros/U retained.')
 (D/'recheck.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
