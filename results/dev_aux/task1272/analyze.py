
from pathlib import Path
import json,collections,random,re
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1273';O.mkdir(exist_ok=False)
D=json.loads((R/'results/dev_aux/task1272/plan.json').read_bytes());D['sources']=[D['source']];allrows=[];pred=[];controls=[]
for n in D['sources']:
 path=R/f'results/dev_aux/task{n}/games.jsonl'
 if not path.exists():continue
 summary=json.loads((path.parent/'result.json').read_bytes());assert summary['complete'] and not summary['error']
 gs=[json.loads(s) for s in path.read_text().splitlines()];key=lambda g:(g['root']['seed'],g['root']['variant'],g['color'],g['opponent']);y=lambda g:(g['label']=='W')-(g['label']=='L')
 def canonical(g):
  v=json.loads(json.dumps(g));v.pop('arm');v.pop('game')
  for q in v['queries']:
   q.pop('game');q['metadata']['uci_info']=[re.sub(r'\b(time|nps) \d+','',s) for s in q['metadata']['uci_info']]
  return v
 jj={key(g):g for g in gs if g['arm']=='J' and g['price']==720};ll={key(g):g for g in gs if g['arm']=='L' and g['price']==720};assert set(jj)==set(ll)
 assert all(canonical(g)==canonical(ll[k]) for k,g in jj.items());controls.append(dict(task=n,identical_J720_L720=len(jj)))
 for arm in ['J','L']:
  bb={key(g):g for g in gs if g['arm']==arm and g['price']==720}
  for price in D['candidates_by_arm'][arm]:
   aa={key(g):g for g in gs if g['arm']==arm and g['price']==price};assert set(aa)==set(bb)
   for opp in ['ALL','unit_search','uniform_random']:
    kk=[k for k in bb if opp=='ALL' or k[3]==opp];families=collections.defaultdict(list);comp={}
    for k in kk:families[k[0]].append(F(y(aa[k])-y(bb[k])));comp[k[0]]=bb[k]['root']['composition']
    fd={s:sum(ds)/len(ds) for s,ds in families.items()};groups=[[s for s in fd if comp[s]==c] for c in sorted(set(comp.values()))];rng=random.Random(D['bootstrap_seed']);boot=[]
    for _ in range(D['bootstrap']):
     sample=[fd[rng.choice(group)] for group in groups for _ in group];boot.append(float(sum(sample)/len(sample)))
    boot.sort();ci=[boot[int(.025*(len(boot)-1))],boot[int(.975*(len(boot)-1))]]
    cc=lambda aa:dict(collections.Counter(aa[k]['label'] for k in kk))
    delta=F(sum(y(aa[k])-y(bb[k]) for k in kk),len(kk))
    allrows.append(dict(task=n,arm=arm,price=price,opponent=opp,N=len(kk),families=len(fd),baseline=cc(bb),candidate=cc(aa),baseline_J=str(F(sum(y(bb[k]) for k in kk),len(kk))),candidate_J=str(F(sum(y(aa[k]) for k in kk),len(kk))),paired_delta=str(delta),descriptive_bootstrap95=ci,point_exceeds_epsilon=float(delta)>D['epsilon'],lower_exceeds_epsilon=ci[0]>D['epsilon'],family_mean_deltas={s:str(v) for s,v in fd.items()}))

result=dict(status='PAIRED_MATCHED_POPULATION_CANDIDATE_PRICE_VALIDATION_NO_REFIT',rows=allrows,prediction=pred,controls=controls,scope=D['scope'])
(O/'result.json').write_text(json.dumps(result,indent=2))
for x in allrows:
 if x['opponent']=='ALL':print({k:v for k,v in x.items() if k!='family_mean_deltas'})
print('PREDICTION',pred,'CONTROLS',controls)
