"""Bind task2591 lambda=1 100k endpoints as Lam1@100k (initial carried for audit); no selection."""
from pathlib import Path
import json,hashlib
D=Path('results/dev_aux/task2591')
def run():
 t=json.loads((D/'generic'/'result.json').read_text());out=[]
 for a in t['arms']:
  s={x['boundary']:x for x in a['snapshots']}[100000]
  out.append(dict(generator_seed=a['generator_seed'],seed=a['seed'],method='Lam1@100k',initial=a['initial'],weights=s['weights'],snapshot_nodes=s['nodes']))
 (D/'eval'/'result.json').write_text(json.dumps(dict(arms=out,training_source=str(D/'generic'/'result.json'),training_sha=hashlib.sha256((D/'generic'/'result.json').read_bytes()).hexdigest()),indent=2));print('bound',len(out))
if __name__=='__main__':run()
