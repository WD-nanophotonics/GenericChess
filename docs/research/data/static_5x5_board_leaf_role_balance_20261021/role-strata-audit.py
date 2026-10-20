import json, hashlib, statistics
from pathlib import Path
from collections import defaultdict,Counter
p=Path('docs/research/data/static_5x5_board_leaf_role_balance_20261021')
plan=json.loads((p/'plan.json').read_text(encoding='utf-8')); games=[json.loads(x) for x in (p/'games.jsonl').read_text(encoding='utf-8').splitlines() if x]
roots={r['root_id']:r for r in json.loads((p/'root-preflight.json').read_text(encoding='utf-8'))['roots']}
paired={}
for g in games:
 root_id=g['game_id'].split('|',1)[0]; owner=int(g['candidate_owner']); root=roots[root_id]
 first=(owner==int(root['side_to_move']))
 moves=[m for m in g['moves'] if m['role']=='candidate']
 paired.setdefault((root_id,owner),{})[g['candidate']]={'reward':g['reward'],'first_role':first,'owner':owner,'nodes':sum(int(m['nodes']) for m in moves),'caller_seconds':sum(float(m['caller_seconds']) for m in moves)}
assert len(paired)==32 and all(set(v)==set(plan['arms']['candidates']) for v in paired.values())
strata=defaultdict(list); raw=[]; node_delta=[]; rel=[]; time_delta=[]
for (root_id,owner),arms in sorted(paired.items()):
 u=arms['unit_leaf__unit_order']; s=arms['static_v2_leaf__unit_order']; d=None if u['reward'] is None or s['reward'] is None else s['reward']-u['reward']; role='candidate-first' if u['first_role'] else 'candidate-reply'; key=f'owner={owner}|role={role}'
 if d is not None: strata[key].append(d)
 raw.append({'root_id':root_id,'owner':owner,'root_side_to_move':roots[root_id]['side_to_move'],'candidate_role':role,'unit_reward':u['reward'],'static_reward':s['reward'],'delta':d})
 node_delta.append(s['nodes']-u['nodes']); rel.append(s['nodes']/u['nodes']-1 if u['nodes'] else None); time_delta.append(s['caller_seconds']-u['caller_seconds'])
stratum_summary={k:{'cells':len(v),'mean_and_exact_bound':sum(v)/len(v)} for k,v in sorted(strata.items())}
result={'schema':'primary-static-board-role-strata-audit-v1','plan_sha256':hashlib.sha256((p/'plan.json').read_bytes()).hexdigest(),'games_sha256':hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest(),'root_preflight_sha256':hashlib.sha256((p/'root-preflight.json').read_bytes()).hexdigest(),'paired_cells':len(paired),'role_owner_strata':stratum_summary,'owner_by_root_first_role_counts':dict(Counter(f"owner={r['owner']}|role={r['candidate_role']}" for r in raw)),'candidate_cost':{'metric':'paired candidate-role only; foe work excluded','median_relative_node_delta':statistics.median(x for x in rel if x is not None),'median_absolute_node_delta':statistics.median(node_delta),'median_caller_delta_seconds':statistics.median(time_delta),'threshold_relative_node_delta':0.10,'gate_pass':statistics.median(x for x in rel if x is not None)<=0.10},'cells':raw}
(p/'role-strata-audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))
