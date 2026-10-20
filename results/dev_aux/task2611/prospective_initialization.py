"""Generate task2611's prospective uniform-init manifest; no training or selection."""
from pathlib import Path
import hashlib, json, random
R=Path('results/dev_aux')
feas=json.loads((R/'task2611/feasibility.json').read_text(encoding='utf-8'))
train_source=R/'task2606/train.py'
source=train_source.read_text(encoding='utf-8')
needle="initial=[1.]+[rng.uniform(.5,1.5)for _ in range(p['dimension']-1)]"
assert needle in source
seeds=feas['proposed_new_seeds']
rows=[]
for seed in seeds:
 rng=random.Random(seed)
 weights=[1.0]+[rng.uniform(.5,1.5) for _ in range(5)]
 assert weights[0]==1.0 and all(.5<=x<=1.5 for x in weights[1:])
 rows.append({'seed':seed,'initial_weights':weights,'fixed_scale_coordinate':0,'source_rng':'random.Random(seed)','training_started':False})
assert len({tuple(r['initial_weights']) for r in rows})==len(rows)
out={'status':'PROSPECTIVE_MANIFEST_ONLY_NOT_REGISTERED','task':'DEV_AUX2611','dimension':6,'initialization_source_sha256':hashlib.sha256(train_source.read_bytes()).hexdigest(),'feasibility_sha256':hashlib.sha256((R/'task2611/feasibility.json').read_bytes()).hexdigest(),'seeds':rows,'seed_and_weight_selection':'deterministic from predeclared seed 2611; no fitness/outcome/model comparison used','next_session_requirement':'bind this manifest to the fresh session UUID and final registration before any training'}
(R/'task2611/prospective-initialization-manifest.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
