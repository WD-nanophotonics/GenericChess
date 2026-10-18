"""Post-seal paired decomposition; no queries, generation or training."""
from pathlib import Path
from collections import Counter
import json,sys
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/filter-search-inputs-20261018';S=R/'.local_agent/playability-filter-20261018'
qs={(q['slot'],q['filter'],q['prefix']):q for q in map(json.loads,(D/'queries.jsonl').read_bytes().splitlines())};gs={(g['slot'],g['filter']):g for g in map(json.loads,(S/'generations.jsonl').read_bytes().splitlines())};rows=[]
for prefix in (0,4,16):
 counts=Counter();delta=Counter();statuses=Counter()
 for slot in range(768):
  a,b=gs[slot,False],gs[slot,True]
  same=a['success']and b['success']and a['rules']==b['rules'];kind='same_complete_rule'if same else'replacement_rule'if a['success']and b['success']else'bounded_generation_refusal'
  counts[kind]+=1;x=qs.get((slot,False,prefix));y=qs.get((slot,True,prefix));vx=bool(x and x['gradient_nonzero']);vy=bool(y and y['gradient_nonzero']);delta[kind]+=int(vy)-int(vx)
  statuses[kind+'_off_nonzero']+=vx;statuses[kind+'_on_nonzero']+=vy
  if same:
   # Caller clocks/compilation cost may differ; these scientific fields must not.
   fields=['status','channels','root_state_sha256','gradient_nonzero']
   if x['status']=='USABLE_NATIVE_RETURN':fields+=['chosen_action','decision_line','leaf_phi','gradient','leaf_prediction','score','completed_depth','query_nodes']
   assert all(x[f]==y[f]for f in fields),(slot,prefix)
 rows.append(dict(prefix=prefix,pairs=dict(counts),nonzero_input_delta=dict(delta),counts=dict(statuses),total_nonzero_delta=sum(delta.values())))
result=dict(status='PASS_PAIRED_DECOMPOSITION',rows=rows,scope='All768intendedpairs; unavailablegeneratedinputs countasavailabilityfalse, not measuredzerogradient. All606same-completerulepairs agree onscientificquery/featurefields atallthreeprefixes. Replacementmeasure isselectedrulechange, not samegamecausalbenefit ortraininggain. No new Native query/generation/fitness/train.')
write_json(D/'paired-input-decomposition.json',result);print(json.dumps(result),flush=True)
