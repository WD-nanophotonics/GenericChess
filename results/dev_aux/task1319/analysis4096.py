from pathlib import Path
from fractions import Fraction as F
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1323';O.mkdir()
D=json.loads((R/'results/dev_aux/task1314/selection.json').read_bytes());gs=[json.loads(s) for s in (R/'results/dev_aux/task1320/games.jsonl').read_text().splitlines()];rows=[]
key=lambda g:(g['root']['seed'],g['root']['variant'],g['color'],g['opponent']);y=lambda g:F((g['label']=='W')-(g['label']=='L'))
for selection in D['rows']:
 arm=selection['arm'];price=selection['global_train_selected'];w=F(selection['search_weight']);baseline={key(g):g for g in gs if g['arm']==arm and g['price']==720};candidate={key(g):g for g in gs if g['arm']==arm and g['price']==price};assert set(baseline)==set(candidate)
 fd={};seeds=sorted(set(k[0] for k in baseline));both={}
 for opp in ['unit_search','uniform_random']:
  kk=[k for k in baseline if k[3]==opp];both[opp]=dict(N=len(kk),baseline=dict(collections.Counter(baseline[k]['label'] for k in kk)),candidate=dict(collections.Counter(candidate[k]['label'] for k in kk)),delta=str(sum(y(candidate[k])-y(baseline[k]) for k in kk)/len(kk)))
 for s in seeds:
  m={}
  for opp in ['unit_search','uniform_random']:
   kk=[k for k in baseline if k[0]==s and k[3]==opp];m[opp]=sum(y(candidate[k])-y(baseline[k]) for k in kk)/len(kk)
  fd[s]=w*m['unit_search']+(1-w)*m['uniform_random']
 mean=sum(fd.values())/len(seeds);rng=random.Random(2026309500);boot=[]
 for _ in range(5000):boot.append(float(sum(fd[rng.choice(seeds)] for _ in seeds)/len(seeds)))
 boot.sort();ci=[boot[124],boot[4874]];rows.append(dict(arm=arm,search_weight=str(w),train_only_price=price,families=len(seeds),paired_dev_gain=str(mean),descriptive_bootstrap95=ci,opponent_rows=both,family_deltas={s:str(v) for s,v in fd.items()},no_refit=True))
(O/'result.json').write_text(json.dumps(dict(status='TRAIN_ONLY_DIRECT_POLICY_PRICE_DEVELOPMENT',rows=rows,scope='w1/2primary,w0/1pretrainexploratory; independentdevsameμ,no refit/familyextension/humanfit',new_go=0),indent=2));print([{k:v for k,v in x.items() if k not in ['family_deltas','opponent_rows']} for x in rows])
