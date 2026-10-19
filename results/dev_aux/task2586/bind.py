"""Bind ALL task2586 Fixed snapshots + OldRulesMean for EVAL (no selection)."""
from pathlib import Path
import json,hashlib
D=Path('results/dev_aux/task2586');OLD=Path('results/dev_aux/task2565/generic/result.json')
def run():
 p=json.loads((D/'generic'/'plan.json').read_text());t=json.loads((D/'generic'/'result.json').read_text());old=json.loads(OLD.read_text());out=[]
 means={}
 for seed in p['initial_seeds']:
  ws=[a['weights']for a in old['arms']if a['method']=='Fixed'and a['seed']==seed];assert len(ws)==4
  means[seed]=[sum(c)/4 for c in zip(*ws)]
 for a in t['arms']:
  gs,seed=a['generator_seed'],a['seed'];snaps={s['boundary']:s for s in a['snapshots']}
  out.append(dict(generator_seed=gs,seed=seed,method='Fixed',initial=a['initial'],weights=a['weights'],arm_nodes=a['nodes'],note='carrier for initial treatment'))
  for b in p['snapshot_nodes']:
   if b in snaps:out.append(dict(generator_seed=gs,seed=seed,method=f'Fixed@{b//1000}k',initial=a['initial'],weights=snaps[b]['weights'],snapshot_nodes=snaps[b]['nodes'],snapshot_lag=b-snaps[b]['nodes'],arm_nodes=a['nodes']))
  out.append(dict(generator_seed=gs,seed=seed,method='OldRulesMean',initial=a['initial'],weights=means[seed],source=str(OLD),source_sha=hashlib.sha256(OLD.read_bytes()).hexdigest()))
 (D/'eval').mkdir(exist_ok=True);(D/'eval'/'result.json').write_text(json.dumps(dict(arms=out,training_source=str(D/'generic'/'result.json'),training_sha=hashlib.sha256((D/'generic'/'result.json').read_bytes()).hexdigest()),indent=2));print('bound',len(out))
if __name__=='__main__':run()
