"""Internal TRAIN selection fragility only; not independent validation."""
from pathlib import Path
from collections import defaultdict,Counter
import json,random,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2347')
def choose(scores):
 best=max(scores.values())
 return 1. if best<=scores[1.]else min(x for x in(1.5,3.)if scores[x]==best)
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());selection=read('results/dev_aux/task2342/selection.json');games=list(map(json.loads,Path('results/dev_aux/task2340/games.jsonl').read_text().splitlines()));groups=defaultdict(lambda:defaultdict(list))
 for g in games:groups[g['root']][g['ratio']].append(g['reward'])
 if selection['status']!='TRAIN_SELECTION_COMPLETE':
  out=dict(status='INCOMPLETE_TRAIN_NO_STABILITY_ESTIMATE',UNKNOWN=sum(g['reward']is None for g in games),scope='NoUimputation/no pricechoice/freshvalidationclaim')
 else:
  assert len(groups)==8 and all(len(v)==4 and all(x is not None for x in v)for rr in groups.values()for v in rr.values());matrix={family:{price:sum(rr[price])/4 for price in(1.,1.5,3.)}for family,rr in groups.items()};families=sorted(matrix);rng=random.Random(810047);counts=Counter();folds=[]
  for k in range(10000):
   if k%1000==0:stop()
   sample=[families[rng.randrange(8)]for j in range(8)];scores={price:sum(matrix[f][price]for f in sample)/8 for price in(1.,1.5,3.)};counts[choose(scores)]+=1
  for held in families:
   train=[f for f in families if f!=held];scores={price:sum(matrix[f][price]for f in train)/7 for price in(1.,1.5,3.)};price=choose(scores);folds.append(dict(held_family=held,selected_without_family=price,seen_family_delta=matrix[held][price]-matrix[held][1.]))
  assert choose({price:sum(matrix[f][price]for f in families)/8 for price in(1.,1.5,3.)})==selection['selected_price'];out=dict(status='TRAIN_INTERNAL_SELECTION_FRAGILITY_DIAGNOSIS',families=8,bootstrap_resamples=10000,descriptive_selection_counts=dict(counts),leave_one_seen_family_out=folds,mean_LOFO_seen_family_delta=sum(f['seen_family_delta']for f in folds)/8,family_mean_rewards=matrix,scope='ONLYoldexposedTRAINdata/internaldescriptiveresampling; selectionfrequency NOTposteriorprobability, LOFO NOTfreshholdout/generalizationproof. Frozenprices/grid/foes/resources unchanged; no adjustingselectedprice/validationscope bytheseoutcomes. Genuinevalidationonlyprefit2341price-unqueriedorbits, futureexecutionseparate.')
 out['seconds']=time.perf_counter()-t
 with(OUT/'result.json').open('x')as f:json.dump(out,f,indent=2)
 print(json.dumps({k:v for k,v in out.items()if k not in('family_mean_rewards','leave_one_seen_family_out')}))
if __name__=='__main__':run()
