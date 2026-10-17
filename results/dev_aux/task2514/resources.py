from pathlib import Path
import json
out=Path('results/dev_aux/task2514');failed=[]
for line in Path('results/dev_aux/task2512/decisions.jsonl').open():
 r=json.loads(line)
 if not r['complete']:failed.append({k:r[k]for k in('seed','method','game','ply','nodes','effective_node_limit','effective_wall_limit','global_remaining_before_query','seconds','reason','total_nodes')})
assert len(failed)==8 and all(r['nodes']==r['effective_node_limit']<8192 and r['total_nodes']==1000000 for r in failed)
r=dict(status='ALL8_FAILURES_LAST_SMALL_NODE_REMAINDER',queries=failed,failed_nodes=sum(x['nodes']for x in failed),scope='Actualjournaledeffectivebudgets/receipts establish finalperarmnodepoolremainder, notafull8192nodequeryfailure/OSfault. No failedtargetadmitted/capreset; 3otherH512trainingcensors remainUNKNOWN. No replay/successimputation.');(out/'training-resource-diagnostics.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
