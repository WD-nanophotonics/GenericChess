"""TRAIN-only directional-credit diagnostics; no parameter selection or new labels."""
from pathlib import Path
from collections import defaultdict
import json
OUT=Path('results/dev_aux/task2508')
def run():
 root=Path('results/dev_aux/task2506');p=json.loads((root/'plan.json').read_text());episodes=[json.loads(x)for x in(root/'episodes.jsonl').read_text().splitlines()];queries=[json.loads(x)for x in(root/'decisions.jsonl').read_text().splitlines()];by=defaultdict(list)
 for d in queries:by[(d['seed'],d['quiet'],d['game'])].append(d)
 output=[]
 for a in json.loads((root/'result.json').read_text())['arms']:
  net=[0.]*5;absolute=[0.]*5;terminal_absolute=[0.]*5;boot_absolute=[0.]*5;actual_delta=forecast_delta=nonzero_actual=nonzero_forecast=0;states=[];bad=0
  gg=[e for e in episodes if e['seed']==a['seed']and e['quiet']==a['quiet']]
  for ep in gg:
   ds=[d for d in by[(a['seed'],a['quiet'],ep['game'])]if d['complete']];elig=[0.]*5;episode_delta=[0.]*5
   for i,d in enumerate(ds):
    target=ds[i+1]['prediction']if i+1<len(ds)else ep['outcome']
    if target is None:break
    elig=[p['lambda']*e+g for e,g in zip(elig,d['gradient'])];error=target-d['prediction'];impulse=[error*e for e in elig];isactual=i+1==len(ds);isforecast=not isactual and ds[i+1]['pv_terminal']
    if isactual:actual_delta+=1;nonzero_actual+=error!=0
    if isforecast:forecast_delta+=1;nonzero_forecast+=error!=0
    for j,v in enumerate(impulse):
     net[j]+=v;absolute[j]+=abs(v);episode_delta[j]+=v
     if isactual:terminal_absolute[j]+=abs(v)
     else:boot_absolute[j]+=abs(v)
   for before,after,credit in zip(ep['initial_weights'],ep['weights'],episode_delta):assert abs(after-before-p['eta']*credit)<1e-10
   states.append(dict(game=ep['game'],coherence=[abs(n)/v if v else None for n,v in zip(net,absolute)],net_recommended=net[:],absolute_recommended=absolute[:]))
  output.append(dict(seed=a['seed'],quiet=a['quiet'],net_recommended=net,absolute_recommended=absolute,directional_coherence=[abs(n)/v if v else None for n,v in zip(net,absolute)],actual_terminal_delta_absolute=terminal_absolute,bootstrap_delta_absolute=boot_absolute,actual_terminal_terms=actual_delta,nonzero_actual_terminal_terms=nonzero_actual,predicted_terminal_successor_terms=forecast_delta,nonzero_predicted_terminal_successor_terms=nonzero_forecast,episodes=states))
 data=dict(status='PASS_SAVED_TRAIN_CREDIT_DECOMPOSITION',arms=output,scope='Recommended impulses before eta from existingfixedepisodepredictions/gradients, notfutureTCtraining. Absolute mass is descriptive: eligibility spans time; cancellation doesnotprove noise or a unique optimum. Actualfinalresidual mayzero aftersearchforecast reachedterminalvalue; earlier forecastchanges still train. Heuristic selfbootstraps are NOTactualWDL. No weights/hyperparameters/checkpoints selected, no gamesrerun.')
 (OUT/'credit-diagnostics.json').write_text(json.dumps(data,indent=2));print(json.dumps([dict(seed=a['seed'],quiet=a['quiet'],coherence=a['directional_coherence'],nonzero_actual_terminal_terms=a['nonzero_actual_terminal_terms'],forecast_terms=a['nonzero_predicted_terminal_successor_terms'])for a in output]))
if __name__=='__main__':run()
