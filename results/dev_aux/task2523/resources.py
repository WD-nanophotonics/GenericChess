from pathlib import Path
from collections import Counter
import json

def run():
 out=Path('results/dev_aux/task2523');base=Path('results/dev_aux/task2521');p=json.loads((base/'plan.json').read_text());failed=[];endings=Counter()
 for line in(base/'decisions.jsonl').open():
  r=json.loads(line)
  if not r['complete']:
   q={k:r[k]for k in('seed','method','game','ply','nodes','effective_node_limit','effective_wall_limit','global_remaining_before_query','seconds','reason','total_nodes')};q['last_small_node_pool']=r['nodes']==r['effective_node_limit']<p['nodes_per_query']and r['total_nodes']==p['nodes_per_arm'];failed.append(q)
 for line in(base/'episodes.jsonl').open():
  r=json.loads(line)
  if r['outcome']is None:endings[r['ending']]+=1
 record=dict(status='ACTUAL_FAILED_QUERY_AND_CENSOR_CLASSIFICATION',queries=failed,failed_nodes=sum(x['nodes']for x in failed),last_small_node_pool=sum(r['last_small_node_pool']for r in failed),other_failed_queries=sum(not r['last_small_node_pool']for r in failed),unknown_endings=dict(endings),scope='Usesactualeffectivebudgets/receipt reasons, notnominal8192budget orOSfaultguess. Earlierbootstraptermsremain, failedquerytargetsneveradmitted; noimputation/replay/capreset.')
 (out/'training-resource-diagnostics.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
if __name__=='__main__':run()
