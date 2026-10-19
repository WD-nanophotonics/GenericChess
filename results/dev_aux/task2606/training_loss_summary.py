"""Descriptive, in-sample training residual-loss summaries for closed task2606 games."""
from collections import defaultdict
from pathlib import Path
import json
D=Path('results/dev_aux/task2606')
plan=json.loads((D/'plan.json').read_text(encoding='utf-8'))
width=plan['nodes_per_arm']/4
bins=defaultdict(lambda:{'loss_sum':0.0,'terms':0,'games':0,'unknown_games':0})
with (D/'games.jsonl').open(encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        g=json.loads(line); method=g['method']; arm=(g['generator_seed'],g['seed'],method)
        idx=min(3,max(0,int(max(0,g['total_nodes']-1)/width)))
        b=bins[(method,idx)]; st=g['stats']; n=st['samples']; loss=st['loss']
        b['games']+=1; b['unknown_games']+=g['outcome'] is None
        if n and loss is not None: b['loss_sum']+=loss*n; b['terms']+=n
out={'task':'DEV_AUX2606','metric':'Mean 1/2 squared TD residual over the learner’s within-training episodes, weighted by observed residual terms; binned by within-arm paid-node fraction. In-sample and trajectory-dependent, descriptive only.','bins':[]}
for method in plan['methods']:
    for idx in range(4):
        b=bins[(method,idx)]
        out['bins'].append({'method':method,'arm_node_fraction':[idx/4,(idx+1)/4],'games':b['games'],'unknown_games':b['unknown_games'],'observed_residual_terms':b['terms'],'mean_half_squared_residual':b['loss_sum']/b['terms'] if b['terms'] else None})
(D/'training-loss-summary.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))