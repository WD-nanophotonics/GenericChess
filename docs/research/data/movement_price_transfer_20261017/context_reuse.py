"""Exact full-state/quantized-profile repetition, with actual output differences retained."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,time,os
R=Path.cwd();sys.path.insert(0,str(R));D=R/'.local_agent/movement-transfer-20261017'
from tools.local_agent.common import write_json
start=time.perf_counter();plan=json.loads((D/'plan.json').read_bytes());models={r['checkpoint_id']:r['checkpoint']for r in json.loads((D/'models.json').read_bytes())['rows']};signatures={}
for cid,cp in models.items():
 obj={k:cp[k]for k in ['ruleset_fingerprint','material_scale']};obj.update(board={t:round(w*256)for t,w in cp['board_weights'].items()},hand={t:round(w*256)for t,w in cp['hand_weights'].items()},dynamic=None,q0=True,TT=0,root_window=False)
 signatures[cid]=hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
seen={};total=Counter();duplicate=Counter();diffcounts=Counter();first_differences=[]
fields=['score','returned_action','decision_line','completed_depth','selective_depth','nodes','qnodes','used_fallback','cause']
for line in (D/'queries.jsonl').open(encoding='utf-8'):
 q=json.loads(line);key=(q['before_sha256'],signatures[q['checkpoint_id']],q['requested_depth'],q['requested_nodes'],q['requested_seconds'])
 total['queries']+=1;total['nodes']+=q['nodes'];total['kernel_seconds']+=q['kernel_seconds'];total['caller_seconds']+=q['caller_seconds']
 digests=tuple(hashlib.sha256(json.dumps(q[k],sort_keys=True,separators=(',',':')).encode()).digest()for k in fields)
 if total['queries']%1024==0:assert time.perf_counter()-start<60,'FROZEN_ANALYSIS_CAP'
 if key not in seen:seen[key]=(digests,q['slot'],q['relative_ply']);continue
 duplicate['queries']+=1;duplicate['nodes']+=q['nodes'];duplicate['kernel_seconds']+=q['kernel_seconds'];duplicate['caller_seconds']+=q['caller_seconds'];duplicate['root_queries'if q['relative_ply']==0 else 'later_queries']+=1
 previous=seen[key];changed=[k for k,a,b in zip(fields,previous[0],digests)if a!=b]
 if changed:
  for k in changed:diffcounts[k]+=1
  if len(first_differences)<32:first_differences.append(dict(key=key,prior_ref=[previous[1],previous[2]],current_ref=[q['slot'],q['relative_ply']],changed_fields=changed))
assert total['queries']==json.loads((D/'result.json').read_bytes())['queries']
for n in ['rollout','advisor','slack']:
 f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R)))/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('user_paused')and not f.get('stopped')
write_json(D/'context-reuse.json',dict(status='COMPLETE_FULL_CONTEXT_REPEAT_AND_OUTPUT_AUDIT',total=dict(total),unique_full_contexts=len(seen),duplicate=dict(duplicate),duplicate_fractions={k:duplicate[k]/total[k]if total[k]else 0 for k in ['queries','nodes','kernel_seconds','caller_seconds']},changed_output_counts=dict(diffcounts),first_differences=first_differences,seconds=time.perf_counter()-start,scope='Current COMPLETE Core-state/history digest plus rulefingerprint/actualquantizedboard+handmaps/scale/exactrequestedbudget/q0/TT0/rootwindowFalse, no physical-position quotient or cross-rule aliases. This doesNOTencode hidden persistent search heuristics or assert metadata equivalence. Recorded duplicate work is NOT aspeedup forecast or evidence for a new cache: key construction/lookup/invalidation costs and fair-resource semantics unpaid. No new queries/games/fit or cap extension.'))
print('CONTEXT_REUSE',total['queries'],len(seen),dict(duplicate),dict(diffcounts))
