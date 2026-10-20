import json,pathlib,collections,hashlib
base=pathlib.Path('.local_agent/primary_staged_promo_utility_20261020/capture-order-run-20261021')
rows=[json.loads(x) for x in (base/'capture-order-games.jsonl').read_text().splitlines() if x.strip()]
roots={r['root_id']:r for r in json.loads((base/'roots.json').read_text())}
g=collections.defaultdict(dict)
for r in rows:g[(r['root_id'],r['candidate_owner'])][r['variant']]=r
details=[]
for (root,owner),arms in sorted(g.items()):
 u=arms['unit_capture_order'];s=arms['static_v2_capture_order']
 first=None
 for i,(a,b) in enumerate(zip(u['moves'],s['moves'])):
  if a['state_before']!=b['state_before']:
   first={'kind':'prior_path_diverged','ply':i};break
  if a['action']!=b['action']:
   first={'kind':'same_state_action_diverged','ply':i,'role':a['role'],'depth_unit':a['completed_depth'],'depth_static':b['completed_depth'],'nodes_unit':a['nodes'],'nodes_static':b['nodes']};break
 if first is None and len(u['moves'])!=len(s['moves']):
  first={'kind':'path_length_diverged','unit':len(u['moves']),'static':len(s['moves'])}
 if u['reward'] is None or s['reward'] is None: outcome='unknown'
 elif s['reward']>u['reward']: outcome='static_better'
 elif s['reward']<u['reward']: outcome='unit_better'
 else: outcome='tied'
 details.append({'root_id':root,'seed':roots[root]['seed'],'root_plies':roots[root]['prefix_plies'],'owner':owner,'first':first,'outcome':outcome})
first_counts=collections.Counter(x['first']['kind'] if x['first'] else 'identical_path' for x in details)
candidate= [x for x in details if x['first'] and x['first']['kind']=='same_state_action_diverged' and x['first']['role']=='candidate']
by_seed={}
for seed in sorted({x['seed'] for x in details}):
 sub=[x for x in details if x['seed']==seed]
 by_seed[str(seed)]={'pairs':len(sub),'candidate_choice_diverged':sum(x in candidate for x in sub),'outcomes':dict(collections.Counter(x['outcome'] for x in sub))}
out={'schema':'primary-capture-order-transcript-diff-v1','plan_sha256':hashlib.sha256((base.parent/'capture-order-plan.json').read_bytes()).hexdigest(),'games_sha256':hashlib.sha256((base/'capture-order-games.jsonl').read_bytes()).hexdigest(),'paired_games':len(details),'first_divergence':dict(first_counts),'candidate_choices_differed_at_same_state':len(candidate),'outcomes':dict(collections.Counter(x['outcome'] for x in details)),'diverged_pairs_outcomes':dict(collections.Counter(x['outcome'] for x in candidate)),'by_seed':by_seed,'details':details}
(base/'transcript-diff-summary.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ('paired_games','first_divergence','candidate_choices_differed_at_same_state','outcomes','diverged_pairs_outcomes','by_seed','games_sha256')},separators=(',',':')))
