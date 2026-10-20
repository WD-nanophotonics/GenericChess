import json,pathlib,collections
p=pathlib.Path('.local_agent/primary_staged_promo_utility_20261020/capture-order-run-20261021/capture-order-games.jsonl')
rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
g=collections.defaultdict(dict)
for r in rows:g[(r['root_id'],r['candidate_owner'])][r['variant']]=r
out=[]
for (root,owner),v in sorted(g.items()):
    u=v['unit_capture_order']; s=v['static_v2_capture_order']
    um=u['moves']; sm=s['moves']
    first=None; common=0
    for i,(a,b) in enumerate(zip(um,sm)):
        if a['state_before']!=b['state_before']:
            first={'ply':i,'kind':'prior_path_diverged','unit_state':a['state_before'],'static_state':b['state_before']};break
        if a['action']!=b['action']:
            first={'ply':i,'kind':'action_choice_diverged','role':a['role'],'side':a['side'],'unit_action':a['action'],'static_action':b['action'],'unit_source':a['result_source'],'static_source':b['result_source'],'unit_depth':a['completed_depth'],'static_depth':b['completed_depth'],'unit_nodes':a['nodes'],'static_nodes':b['nodes']};break
        common+=1
    if first is None and len(um)!=len(sm):
        first={'ply':min(len(um),len(sm)),'kind':'one_path_ended','unit_moves':len(um),'static_moves':len(sm)}
    outcome=(u['reward'],s['reward'])
    out.append({'root':root,'owner':owner,'common_prefix':common,'first_divergence':first,'unit_reward':u['reward'],'static_reward':s['reward'],'unit_moves':len(um),'static_moves':len(sm)})
stats=collections.Counter((x['first_divergence']['kind'] if x['first_divergence'] else 'identical') for x in out)
roles=collections.Counter((x['first_divergence']['role'] if x['first_divergence'] and x['first_divergence']['kind']=='action_choice_diverged' else 'no_same_state_action_divergence') for x in out)
print(json.dumps({'pairs':len(out),'first_divergence_counts':stats,'divergence_roles':roles,'details':out},separators=(',',':')))
