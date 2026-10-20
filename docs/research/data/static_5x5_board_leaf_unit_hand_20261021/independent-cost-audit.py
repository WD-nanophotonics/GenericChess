from __future__ import annotations
import hashlib, json, statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'plan.json').read_text(encoding='utf-8'))
games=[json.loads(line) for line in (HERE/'games.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
paired={}
for game in games:
    root_id=game['game_id'].split('|',1)[0]
    key=(root_id,int(game['candidate_owner']))
    candidate_moves=[move for move in game['moves'] if move['role']=='candidate']
    entry={'candidate_nodes':sum(int(m['nodes']) for m in candidate_moves),'candidate_caller_seconds':sum(float(m['caller_seconds']) for m in candidate_moves),'candidate_queries':len(candidate_moves)}
    paired.setdefault(key,{})[game['candidate']]=entry
assert len(games)==plan['arms']['physical_games']==64
assert len(paired)==32
assert all(set(arms)==set(plan['arms']['candidates']) for arms in paired.values())
rows=[]
for (root_id,owner),arms in sorted(paired.items()):
    unit=arms['unit_leaf__unit_order']; static=arms['static_v2_leaf__unit_order']
    rows.append({'root_id':root_id,'candidate_owner':owner,'unit_nodes':unit['candidate_nodes'],'static_nodes':static['candidate_nodes'],'relative_node_delta':static['candidate_nodes']/unit['candidate_nodes']-1 if unit['candidate_nodes'] else None,'unit_caller_seconds':unit['candidate_caller_seconds'],'static_caller_seconds':static['candidate_caller_seconds'],'caller_delta_seconds':static['candidate_caller_seconds']-unit['candidate_caller_seconds']})
rel=[r['relative_node_delta'] for r in rows if r['relative_node_delta'] is not None]
node_abs=[r['static_nodes']-r['unit_nodes'] for r in rows]
caller=[r['caller_delta_seconds'] for r in rows]
by_owner={str(owner):{'median_relative_node_delta':statistics.median([r['relative_node_delta'] for r in rows if r['candidate_owner']==owner]),'median_caller_delta_seconds':statistics.median([r['caller_delta_seconds'] for r in rows if r['candidate_owner']==owner]),'pairs':sum(r['candidate_owner']==owner for r in rows)} for owner in (0,1)}
result={'schema':'primary-static-board-leaf-paired-cost-audit-v1','plan_sha256':hashlib.sha256((HERE/'plan.json').read_bytes()).hexdigest(),'games_sha256':hashlib.sha256((HERE/'games.jsonl').read_bytes()).hexdigest(),'producer_source_sha256':hashlib.sha256((HERE/'producer-source.json').read_bytes()).hexdigest(),'game_count':len(games),'paired_root_owner_count':len(rows),'candidate_role_only_cost':True,'metric':'Within each identical (fresh root, candidate owner), sum candidate-role nodes/caller seconds by arm; report median of per-pair relative node deltas. Foe work excluded because identical Unit and not candidate treatment.','median_relative_node_delta':statistics.median(rel),'median_absolute_node_delta':statistics.median(node_abs),'median_caller_delta_seconds':statistics.median(caller),'cost_gate_threshold_relative_node_delta':0.10,'cost_gate_pass':statistics.median(rel)<=0.10,'by_owner':by_owner,'pairs':rows}
(HERE/'cost-audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='pairs'},indent=2))
