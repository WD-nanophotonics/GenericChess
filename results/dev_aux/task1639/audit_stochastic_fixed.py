from pathlib import Path
import json,importlib.util,collections,numpy as np
from fractions import Fraction
from functools import lru_cache
R=Path.cwd();O=R/'results/dev_aux/task1650';O.mkdir(exist_ok=False);counts=collections.Counter();summaries=[]
# Independentlyvalidate certificates andexactrational short-horizon recurrence; code doesnotimport originalproducer.
for price in [[720,720,720],[1440,720,720]]:
 prefix=f'R{price[0]}_N{price[1]}_B{price[2]}';g=json.loads((R/f'results/dev_aux/task1631/{prefix}_graph.json').read_bytes());n=len(g['keys']);base=np.array(json.loads((R/f'results/dev_aux/task1646/{prefix}_base.json').read_bytes()));closed=set(json.loads((R/f'results/dev_aux/task1646/{prefix}_closed.json').read_bytes())['closed_state_ids']);records=json.loads((R/f'results/dev_aux/task1646/{prefix}_records.json').read_bytes());record={x['H']:x for x in records};adj=g['adj']
 assert base.shape==(n,10) and np.all(base[:,:5].sum(axis=1)==1) and np.all(base[:,5:].sum(axis=1)==1)
 for i in closed:assert adj[i] and all(j in closed for j in adj[i]) and g['basis'][i] not in ['UNKNOWN_FRONTIER','COMMON_PERFECT_4_ORACLE','TERMINAL'];assert base[i,2]==base[i,7]==1
 @lru_cache(None)
 def exact(i,h):
  ll=adj[i]
  if not ll or i in closed or h==0:return tuple(Fraction(int(x)) for x in base[i])
  a=[exact(j,h-1) for j in ll];return tuple(sum(x[c] for x in a)/len(ll) for c in range(10))
 for h in [0,1,2,4,8]:
  for x in record[h]['roots']:
   a=exact(x['sid'],h);assert max(abs(float(a[c])-x['probabilities'][c]) for c in range(10))<1e-13;counts['exact_rational_root_horizons']+=1
 trans=[i for i,ll in enumerate(adj) if ll and i not in closed];edge_src=np.array([i for i in trans for j in adj[i]],dtype=np.int64);edge_dst=np.array([j for i in trans for j in adj[i]],dtype=np.int64);weights=np.array([1/len(adj[i]) for i in trans for j in adj[i]]);transset=set(trans);absorbing=np.array([i for i in range(n) if i not in transset],dtype=np.int64);mass=np.zeros(n)
 for fam,i in g['roots']:mass[i]+=1/32
 cumul=np.zeros(10);maxdiff=0
 for h in range(385):
  cumul+=mass[absorbing]@base[absorbing];mass[absorbing]=0
  if h in record:
   expected=np.mean([x['probabilities'] for x in record[h]['roots']],axis=0);actual=cumul.copy();actual[4]=actual[9]=mass.sum();diff=float(np.max(np.abs(actual-expected)));assert diff<1e-11;maxdiff=max(maxdiff,diff);counts['forward_backward_mean_horizons']+=1
  if h==384:break
  mass=np.bincount(edge_dst,weights=mass[edge_src]*weights,minlength=n)
 last=record[3072];final=np.load(R/f'results/dev_aux/task1646/{prefix}_final.npy');assert final.shape==(n,10)
 for x in last['roots']:assert np.array_equal(final[x['sid']],np.array(x['probabilities']))
 for offset in [0,5]:assert np.max(np.abs(final[:,offset:offset+5].sum(axis=1)-1))<1e-9
 counts['graph_states']+=n;summaries.append({'price':price,'max_forward_backward_abs_diff':maxdiff,'closed_certified_states':len(closed)})
z=json.loads((R/'results/dev_aux/task1646/result.json').read_bytes());a,b=z['profiles'];gain=[]
for j in [0,1]:
 aa=a['summary'][j];bb=b['summary'][j];gain.append({'scope':aa['scope'],'gain_bounds':[bb['net_lower']-aa['net_upper'],bb['net_upper']-aa['net_lower']]})
out={'status':'PASS_EXACT_SHORT_RATIONAL_FORWARD_BACKWARD_PROBABILITIES_CLOSED_CLASSES','counts':dict(counts),'profiles':summaries,'pricegain_bounds':gain,'scope':'16exposedPILOTfamilies mean, conditionalcomposite probabilities notactualphysicalwholegame. Float64 longiteratedbounds use disclosed1e-8numericalreserve, notformal intervalarithmetic/exactrational cert; gain magnitude .04 doesnotrequiremoreprecision.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

