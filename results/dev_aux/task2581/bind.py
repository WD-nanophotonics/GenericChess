from pathlib import Path
import json,hashlib
from results.dev_aux.task2580.train import initial
D=Path('results/dev_aux/task2580');E=Path('results/dev_aux/task2581')
def run():
 p=json.loads((D/'plan.json').read_text());t=json.loads((D/'result.json').read_text());a={(x['seed'],x['method']):x for x in t['arms']};out=[]
 for seed in p['seeds']:
  for method in('initial','TD_early','TD_mixed'):
   if method!='initial'and(seed,method)not in a:continue
   arm=a.get((seed,method));out.append(dict(generator_seed=0,seed=seed,method=method+'|plain',original_method=method,initial=initial(seed),weights=initial(seed)if arm is None else arm['weights'],actual_training_nodes=0 if arm is None else arm['nodes'],matched_training_budget=arm is None or arm['nodes']==p['nodes_per_arm']))
 (E/'result.json').write_text(json.dumps(dict(arms=out,training_source=str(D/'result.json'),training_sha=hashlib.sha256((D/'result.json').read_bytes()).hexdigest()),indent=2));print('bound',len(out))
if __name__=='__main__':run()
