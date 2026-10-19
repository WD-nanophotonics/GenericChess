"""Bind ALL task2587 snapshots (Cold/Warm @0/25k/50k/100k) for EVAL; no selection."""
from pathlib import Path
import json,hashlib
D=Path('results/dev_aux/task2587')
def run():
 p=json.loads((D/'generic'/'plan.json').read_text());t=json.loads((D/'generic'/'result.json').read_text());out=[]
 for a in t['arms']:
  gs,seed=a['generator_seed'],a['seed'];x='Warm'if a['method']=='FixedWarm'else'Cold';snaps={s['boundary']:s for s in a['snapshots']}
  if x=='Warm':assert a['initial']==p['initial_weights'][f'{gs}/{seed}']
  out.append(dict(generator_seed=gs,seed=seed,method=f'{x}@0',original_method=a['method'],initial=a['initial'],weights=a['initial'],snapshot_nodes=0))
  for b in p['snapshot_nodes']:
   if b in snaps:out.append(dict(generator_seed=gs,seed=seed,method=f'{x}@{b//1000}k',original_method=a['method'],initial=a['initial'],weights=snaps[b]['weights'],snapshot_nodes=snaps[b]['nodes'],snapshot_lag=b-snaps[b]['nodes'],arm_nodes=a['nodes']))
 (D/'eval'/'result.json').write_text(json.dumps(dict(arms=out,training_source=str(D/'generic'/'result.json'),training_sha=hashlib.sha256((D/'generic'/'result.json').read_bytes()).hexdigest()),indent=2));print('bound',len(out))
if __name__=='__main__':run()
