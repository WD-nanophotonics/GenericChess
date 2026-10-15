"""Post-training diagnosis, no new Native queries or selection on DEV."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,collections,random,itertools,math
import numpy as np
R=Path.cwd();D=R/'results/dev_aux/task1723';O=R/'results/dev_aux/task1725';O.mkdir(exist_ok=False)
plan=json.loads((D/'start.json').read_bytes())['plan'];run=json.loads((D/'result.json').read_bytes());assert run['status']=='COMPLETE'
games=[json.loads(l) for l in (D/'games.jsonl').open()];choices=[json.loads(l) for l in (D/'choices.jsonl').open()]
prices=sorted(map(tuple,plan['prices']));base=tuple(plan['baseline']);families={f['family']:f for f in plan['families']};trainids=sorted(f for f in families if families[f]['phase'].startswith('TRAIN'))
gm={(tuple(x['price']),x['family'],x['color'],x['opponent']):x for x in games};values={};rootchoices={};outcomefingerprints={};trajectoryfingerprints={}
for p in prices:
 values[p]=[sum(gm[p,f,c,op['id']]['payoff'] or 0 for c in (0,1) for op in plan['opponents'])/4 for f in trainids]
 outcomefingerprints[p]=tuple(gm[p,f,c,op['id']]['payoff'] for f in trainids for c in (0,1) for op in plan['opponents'])
 trajectoryfingerprints[p]=tuple(tuple(z['move'] for z in gm[p,f,c,op['id']]['trajectory']) for f in trainids for c in (0,1) for op in plan['opponents'])
 for f in trainids:
  for c in (0,1):
   aa=[gm[p,f,c,op['id']]['trajectory'][0]['move'] for op in plan['opponents']]
   assert len(set(aa))==1;rootchoices[p,f,c]=aa[0]
pairs=[]
for p,q in itertools.combinations(prices,2):
 pairs.append(dict(p=p,q=q,root_action_differences=sum(rootchoices[p,f,c]!=rootchoices[q,f,c] for f in trainids for c in (0,1)),outcome_differences=sum(a!=b for a,b in zip(outcomefingerprints[p],outcomefingerprints[q])),trajectory_differences=sum(a!=b for a,b in zip(trajectoryfingerprints[p],trajectoryfingerprints[q])),netdifference=sum(values[p])-sum(values[q])))
rng=random.Random(2026701505);boot=collections.Counter();ties=collections.Counter();loo=collections.Counter()
for _ in range(10000):
 ii=rng.choices([i for i,f in enumerate(trainids) if f%2==0],k=len(trainids)//2)+rng.choices([i for i,f in enumerate(trainids) if f%2],k=len(trainids)//2)
 score={p:sum(values[p][i] for i in ii) for p in prices};best=max(score.values());w=[p for p in prices if score[p]==best];boot[str(min(w))]+=1;ties[len(w)]+=1
for i in range(len(trainids)):
 score={p:sum(v for j,v in enumerate(values[p]) if j!=i) for p in prices};loo[str(min(prices,key=lambda p:(-score[p],p)))]+=1
A=np.asarray([values[p] for p in prices]);center=A-A[prices.index(base)];singular=np.linalg.svd(center,compute_uv=False)
bytype=[]
for op in plan['opponents']:
 for ph in ('TRAIN1','TRAIN2','DEV'):
  for p in sorted({tuple(z['price']) for z in games if z['phase']==ph}):
   rows=[z for z in games if tuple(z['price'])==p and z['phase']==ph and z['opponent']==op['id']]
   bytype.append(dict(phase=ph,price=p,opponent=op['id'],games=len(rows),W=sum(z['payoff']==1 for z in rows),L=sum(z['payoff']==-1 for z in rows),Draw=sum(z['payoff']==0 for z in rows),Unknown=sum(z['payoff'] is None for z in rows),net=sum(z['payoff'] or 0 for z in rows)/len(rows),mean_plies=sum(len(z['trajectory']) for z in rows)/len(rows)))
changes=[]
for p in prices:
 rows=[z for z in pairs if z['p']==base and z['q']==p or z['q']==base and z['p']==p]
 if rows:changes.append(rows[0])
categories=collections.Counter(z['category'] for z in games)
out=dict(status='COMPLETE_ZERO_QUERY_POSTHOC_DIAGNOSIS',root_count=96,training_families=len(trainids),prices=prices,bootstrap_pooled_training_winner_counts=dict(boot),bootstrap_tie_size_counts=dict(ties),leave_one_family_out_winners=dict(loo),training_relative_payoff_matrix_singular_values=singular.tolist(),same_all_training_outcomes=[z for z in pairs if z['outcome_differences']==0],same_all_training_trajectories=[z for z in pairs if z['trajectory_differences']==0],rootchanges_vsunit=changes,categories=dict(categories),by_phase_opponent=bytype,actual_native_go=0,interpretation='Posthoc TRAIN stability/response diagnostic. Bootstrap winners are conditional resamples, not independent replication or actualrandominitial training. Stateactiondifferences alone not gains. Opponent/color coupled byfamily; payoff zero of unresolved finite event is not Draw. NoDEVreselection.')
(O/'result.json').write_text(json.dumps(out,indent=2));(O/'all_price_pairs.json').write_text(json.dumps(pairs,indent=2));print({k:v for k,v in out.items() if k not in ('by_phase_opponent','rootchanges_vsunit','prices')})

