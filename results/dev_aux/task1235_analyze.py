from pathlib import Path
from fractions import Fraction as F
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1235';O.mkdir()
D=json.loads((R/'results/dev_aux/task1232/selection.json').read_bytes());gs=[json.loads(s) for s in (R/'results/dev_aux/task1233/games.jsonl').read_text().splitlines()];rows=[]
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
tasks=[1170,1176,1188,1197,1206,1217,1230,1233];batches=[]
for n in tasks:
 p=R/f'results/dev_aux/task{n}';s=json.loads((p/'result.json').read_bytes());assert s['complete'] and s['error'] is None
 batches.append(dict(task=n,games=s['closed_games'],go=s['actual_go'],producer_seconds=s['seconds']))
perfts=[]
for n in [1169,1175,1187,1196,1216,1229]:
 d=json.loads((R/f'results/dev_aux/task{n}/qualification.json').read_bytes());perfts.append(dict(task=n,count=d['actual_perft_go']))
cost=dict(status='ACTUAL_COMPLETE_PHYSICAL_COUNTS',games=sum(v['games'] for v in batches),game_search_go=sum(v['go'] for v in batches),cold_controls_search_go=72,total_search_go=sum(v['go'] for v in batches)+72,perft_go=sum(v['count'] for v in perfts),game_producer_seconds=sum(v['producer_seconds'] for v in batches),game_batches=batches,perft_batches=perfts,tiny_build_seconds=json.loads((R/'results/dev_aux/task1210/build.json').read_bytes())['seconds'],oracle_requests=0,scope='Allactualclosed/qualified24plygames. CachedH12zeroqueries. No singlehourrun, concurrency normal/noexclusivity/speedup. Analysis/audit/engineering/transport/publicationcostinsessionwall; tokensunmeasured.')
(R/'results/dev_aux/COST_20261014_43.json').write_text(json.dumps(cost,indent=2));print('COST',cost)
