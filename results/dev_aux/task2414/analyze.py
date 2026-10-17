from pathlib import Path
from collections import Counter
import json,time
import numpy as np
from results.dev_aux.task2406.analyze import contrast
OUT=Path('results/dev_aux/task2414')
def run():
 t=time.perf_counter();f=Path('results/dev_aux/task2413');slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};selected=json.loads(Path('results/dev_aux/task2405/selection.json').read_text())['selected'];rng=np.random.default_rng(841414);panels=[];pooled=[]
 for foe in(0,1):
  data={};rows=[]
  for price in([1.5,1.5],selected):
   blocks=[];counts=Counter()
   for family in range(8):
    role_bounds=[]
    for role in(0,1):
     s,=[s for s in slots if s['opponent']==foe and s['root']==family and s['candidate_color']==role and[s['ratio'],s['hand_ratio']]==price];g=games.get(s['slot']);reward=None if g is None else g['reward'];counts['U'if reward is None else g['outcome']]+=1;role_bounds.append((-1,1)if reward is None else(reward,reward))
    blocks.append([sum(x[i]for x in role_bounds)/2 for i in(0,1)])
   data[tuple(price)]=np.array(blocks);rows.append(dict(price=price,counts={k:counts[k]for k in'WLDU'},mean_bounds=data[tuple(price)].mean(axis=0).tolist()))
  panels.append(dict(opponent_R=[.5,4.][foe],rows=rows,gain=contrast(data[tuple(selected)],data[(1.5,1.5)],rng)));pooled.append(data)
 a=(pooled[0][tuple(selected)]+pooled[1][tuple(selected)])/2;b=(pooled[0][(1.5,1.5)]+pooled[1][(1.5,1.5)])/2
 out=dict(status='CLOSED_FIXED_NEW_OPPONENT_TRANSFER',panels=panels,pooled_gain=contrast(a,b,rng),actual_returned=len(games),missing=len(slots)-len(games),actual_game_seconds=sum(g['seconds']for g in games.values()),seconds=time.perf_counter()-t,scope='Baseline/immutableTRAINselected, ALL8samepre-reservedroots/roles and2newopponentpriceswithfixedbudgets. Initialrootsexposed2402, notfreshinitialholdout. Bootstrap8familyclusters, foes/roleswithincluster. U/missingintervals notdraw; no refit/countpadding/oldcapextension. Finite conditionalfullpolicypriceeffect, notuniqueoruniversalvalue.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
