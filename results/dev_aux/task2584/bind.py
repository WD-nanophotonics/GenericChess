"""Bind ALL task2583 snapshots (1.25M, 2.5M) plus initial prices; no selection."""
from pathlib import Path
import json,hashlib
from results.dev_aux.task2580.train import initial
D=Path('results/dev_aux/task2583');E=Path('results/dev_aux/task2584')
def label(method,boundary):return f'{method}@{boundary/1e6:g}M|plain'
def run():
 p=json.loads((D/'plan.json').read_text());t=json.loads((D/'result.json').read_text());a={(x['seed'],x['method']):x for x in t['arms']};out=[]
 for seed in p['seeds']:
  out.append(dict(generator_seed=0,seed=seed,method='initial|plain',original_method='initial',boundary=0,initial=initial(seed),weights=initial(seed),snapshot_nodes=0))
  for method in('Fixednu','SelfCandidate'):
   arm=a.get((seed,method))
   if arm is None:continue
   snaps={s['boundary']:s for s in arm['snapshots']}
   for boundary in p['snapshot_nodes']:
    s=snaps.get(boundary)
    if s is None:continue
    out.append(dict(generator_seed=0,seed=seed,method=label(method,boundary),original_method=method,boundary=boundary,initial=initial(seed),weights=s['weights'],snapshot_nodes=s['nodes'],snapshot_lag=boundary-s['nodes'],snapshot_games=s['index'],arm_nodes=arm['nodes'],matched_training_budget=arm['nodes']==p['nodes_per_arm']))
 (E/'result.json').write_text(json.dumps(dict(arms=out,training_source=str(D/'result.json'),training_sha=hashlib.sha256((D/'result.json').read_bytes()).hexdigest()),indent=2));print('bound',len(out))
if __name__=='__main__':run()
