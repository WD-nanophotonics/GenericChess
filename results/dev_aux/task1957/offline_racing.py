"""TRAIN-only offline arm-racing development; no new games or selected price."""
from pathlib import Path
from collections import Counter
import json,random,hashlib,time
O=Path('results/dev_aux/task1957')
def run():
 start=time.perf_counter();source=Path('results/dev_aux/task1939/games.jsonl');rows=[json.loads(x) for x in source.read_text().splitlines()];train=[g for g in rows if g['phase']=='TRAIN'];assert len(train)==416;grid=sorted({g['ratio'] for g in train});assert len(grid)==13
 vals={(f,r):sum(g['finite_event_score'] for g in train if g['family']==f and g['ratio']==r) for f in range(16) for r in grid};cost={(f,r):sum(g['seconds'] for g in train if g['family']==f and g['ratio']==r) for f in range(16) for r in grid};full={r:sum(vals[f,r] for f in range(16)) for r in grid};opt={r for r in grid if full[r]==max(full.values())};rng=random.Random(20261016641957);reports=[]
 for repeat in range(10000):
  fs=list(range(16));rng.shuffle(fs);alive=grid[:];paid=set();stages=[]
  for end,keep in [(4,7),(8,4),(12,2),(16,1)]:
   paid.update((f,r) for f in fs[:end] for r in alive);scores={r:sum(vals[f,r] for f in fs[:end]) for r in alive};alive=sorted(alive,key=lambda r:(-scores[r],r))[:keep];stages.append(alive[:])
  selected=alive[0];uniform=min(grid,key=lambda r:(-sum(vals[f,r] for f in fs[:8]),r));assert len(paid)==104
  reports.append(dict(racing=selected,uniform=uniform,racing_regret=max(full.values())-full[selected],uniform_regret=max(full.values())-full[uniform],racing_paid_seconds=sum(cost[k] for k in paid),uniform_paid_seconds=sum(cost[f,r] for f in fs[:8] for r in grid)))
 def summary(method):
  regrets=sorted(r[method+'_regret'] for r in reports);secs=sorted(r[method+'_paid_seconds'] for r in reports);return dict(offline_selections=dict(Counter(r[method] for r in reports)),full_TRAIN_optimum_hit_fraction=sum(r[method] in opt for r in reports)/len(reports),mean_full_TRAIN_net_regret=sum(regrets)/len(regrets),median_full_TRAIN_net_regret=regrets[5000],regret_p95=regrets[9499],paid_case_seconds_median=secs[5000],paid_case_seconds_p5_p95=[secs[500],secs[9499]],physical_new_games=0,game_equivalents=208)
 out=dict(status='TRAIN_ONLY_OFFLINE_COST_FEASIBILITY',source_sha=hashlib.sha256(source.read_bytes()).hexdigest(),source_training_cases=416,full_TRAIN_scores=full,full_TRAIN_optimal_set=sorted(opt),permutations=10000,paired_racing=summary('racing'),equal_game_uniform_subset=summary('uniform'),full_TRAIN_paid_seconds=sum(cost.values()),source_papers=['https://proceedings.mlr.press/v28/karnin13.html','https://www.remi-coulom.fr/CLOP/'],seconds=time.perf_counter()-start,scope='UsesonlyALL16TRAINfamilies/13pricecells from1939; noDEV/CONFIRM/humanlabels, no newchosenprice or performanceclaim. 10000permutations reuseonepaidtable, NOTindependenttrainingreplicates. Fourpairedcumulative4/8/12/16family roundsretain7/4/2/1arms, numericprice ties. This is a heuristicinspiredbySequentialHalving, NOTits exactallocation/theorem: sharedpairedroles/families, withoutreplacement/finitetable/possibleties violate independentarm-sample/uniqueoptimum assumptions. Compareequal208gameequivalents uniform8families/all13arms. Paidcase-time sums omitfreshengine/qualification/transportoverhead andloadchanges, NOTactualsavings. Full416gamesalreadyspent; anyadoptionrequiresfreshprospectiveprotocolandvalidation.')
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':run()
