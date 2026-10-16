"""TRAIN-only postfit descriptive selector sensitivity, no selection update."""
from pathlib import Path
from collections import Counter
import json,time,numpy as np
OUT=Path('results/dev_aux/task2277')
def run():
 assert not (OUT/'result.json').exists(); start=time.perf_counter(); folder=Path('results/dev_aux/task2261'); p=json.loads((folder/'plan.json').read_text()); selection=json.loads((folder/'TRAIN-selection.json').read_text()); games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines() if json.loads(x)['phase']=='TRAIN']; assert len(games)==640 and all(g['reward'] is not None for g in games); families=sorted({g['family'] for g in games}); grid=p['grid']; means=np.array([[sum(g['reward'] for g in games if g['family']==f and g['ratio']==r)/4 for r in grid] for f in families]); assert means.shape==(32,5)
 def choose(v,initial):
  current=grid.index(initial); trace=[grid[current]]
  while True:
   better=[i for i in (current-1,current+1) if 0<=i<len(grid) and v[i]>v[current]]
   if not better:break
   current=better[0];trace.append(grid[current])
  allowed=[i for i in range(len(grid)) if v[i]>v[grid.index(initial)]]
  global_index=min(allowed,key=lambda i:(-v[i],i)) if allowed else grid.index(initial)
  return dict(initial=initial,adjacent_selected=grid[current],adjacent_trace=trace,global_selected=grid[global_index])
 assert [choose(means.mean(axis=0),x) for x in p['initial_prices']]==selection['selections']
 rng=np.random.default_rng(20261017782777); boot=means[rng.integers(0,32,size=(10000,32))].mean(axis=1); sensitivity=[]
 for initial in p['initial_prices']:
  selections=[choose(row,initial) for row in boot]; leaveout=[choose(np.delete(means,i,axis=0).mean(axis=0),initial) for i in range(32)]
  sensitivity.append(dict(initial=initial,bootstrap10000_global=dict(Counter(str(x['global_selected']) for x in selections)),bootstrap10000_adjacent=dict(Counter(str(x['adjacent_selected']) for x in selections)),leave_one_family_out_global=dict(Counter(str(x['global_selected']) for x in leaveout)),leave_one_family_out_adjacent=dict(Counter(str(x['adjacent_selected']) for x in leaveout))))
 result=dict(status='PASS_TRAIN_ONLY_DESCRIPTIVE_SELECTOR_SENSITIVITY',TRAIN_games=640,TRAIN_family_blocks=32,DEV_games_read_for_analysis=0,sensitivity=sensitivity,original_selection_unchanged=True,seconds=time.perf_counter()-start,scope='PostfitexposedTRAINfamilyresampling/leaveoneout diagnostic, NOTnewfit/pricechoice/DEVfilter/parameterprobability/calibratedCI. OriginalTRAIN2/DEVprotocol unchanged. Bootstraps dependonfrozenfiniteconditionalmu; point2notuniversalmagnitude. No newplayer/rewardgames/humanprices.')
 with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
