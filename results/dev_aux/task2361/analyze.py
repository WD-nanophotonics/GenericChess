"""Descriptive family contrasts and internal TRAIN fragility, no price changes."""
from pathlib import Path
from collections import defaultdict,Counter
import json,random,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2361')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();selection=json.loads(Path('results/dev_aux/task2357/selection.json').read_text());games=json.loads(Path('results/dev_aux/task2358/matrix-games.json').read_text());grid=[.5,1.,1.5,2.,3.]
 if selection['status']!='TRAIN_SELECTION_COMPLETE':result=dict(status='INCOMPLETE_NO_FAMILY_ESTIMATE',matrix_returned=len(games),selected_price=None,scope='No unbalancedpartialmean/Uimputation')
 else:
  mat=defaultdict(lambda:defaultdict(list))
  for g in games:mat[g['root']][g['ratio']].append(g['reward'])
  families=sorted(mat);assert len(families)==8 and all(len(mat[f][p])==4 for f in families for p in grid);means={f:{p:sum(mat[f][p])/4 for p in grid}for f in families};deltas={p:[means[f][p]-means[f][1.]for f in families]for p in grid};rng=random.Random(820061);counts=Counter();bootstrap={p:[]for p in grid}
  def choose(scores):
   best=max(scores.values());return 1. if best<=scores[1.]else min(p for p in grid if scores[p]==best)
  for k in range(10000):
   if k%1000==0:stop()
   draw=[families[rng.randrange(8)]for j in range(8)];scores={p:sum(means[f][p]for f in draw)/8 for p in grid};counts[choose(scores)]+=1
   for p in grid:bootstrap[p].append(sum(means[f][p]-means[f][1.]for f in draw)/8)
  intervals={str(p):[sorted(bootstrap[p])[250],sorted(bootstrap[p])[9749]]for p in grid};folds=[]
  for held in families:
   rest=[f for f in families if f!=held];scores={p:sum(means[f][p]for f in rest)/len(rest)for p in grid};winner=choose(scores);folds.append(dict(held_seen_family=held,selected_without_family=winner,held_seen_family_gain=means[held][winner]-means[held][1.]))
  result=dict(status='TRAIN_INTERNAL_FAMILY_CONTRASTS',selected_price=selection['selected_price'],family_mean_rewards=means,mean_gains={str(p):sum(deltas[p])/8 for p in grid},positive_families={str(p):sum(d>0 for d in deltas[p])for p in grid},negative_families={str(p):sum(d<0 for d in deltas[p])for p in grid},descriptive_family_intervals=intervals,descriptive_selected_counts=dict(counts),leave_one_seen_family_out=folds,LOFO_selected_counts=dict(Counter(r['selected_without_family']for r in folds)),scope='ONLY8seenTRAINfamilyblocks, reuse65explicit; internalbootstrap NOTposterior/freshvalidation/generalization evidence; LOFO ofalreadyseenTRAINfamilies isfragilitydiagnostic notunseenholdout. AddedDotadvice beforemainTRAINclosure; frozenoriginalselector unchanged. FrozenTRAINselector unchanged, no price/root/cap adaptation from this diagnostic.')
 result['seconds']=time.perf_counter()-t
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='family_mean_rewards'}))
if __name__=='__main__':run()
