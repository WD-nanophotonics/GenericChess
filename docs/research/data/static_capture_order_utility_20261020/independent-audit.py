import json,pathlib,hashlib,statistics,collections
b=pathlib.Path('.local_agent/primary_staged_promo_utility_20261020')
r=b/'capture-order-run-20261021'
plan=json.loads((b/'capture-order-plan.json').read_text())
rows=[json.loads(x) for x in (r/'capture-order-games.jsonl').read_text().splitlines() if x]
assert len(rows)==64
assert all(x['action_invalid_count']==0 and x['full_history_replay_equal'] for x in rows)
groups=collections.defaultdict(dict)
roots={x['root_id']:x for x in json.loads((r/'roots.json').read_text())}
for x in rows:
    groups[(x['root_id'],x['candidate_owner'])][x['variant']]=x
assert len(groups)==32
assert all(set(x)==set(plan['arms']['candidate_arms']) for x in groups.values())
assert all(v['unit_capture_order']['root_state_sha256']==v['static_v2_capture_order']['root_state_sha256'] for v in groups.values())
pairs=[]
for (rid,owner),v in groups.items():
    u=v['unit_capture_order']; s=v['static_v2_capture_order']
    lo=(-1 if s['reward'] is None else s['reward'])-(1 if u['reward'] is None else u['reward'])
    hi=(1 if s['reward'] is None else s['reward'])-(-1 if u['reward'] is None else u['reward'])
    pairs.append((owner,roots[rid]['prefix_plies'],lo,hi,
      sum(m['nodes'] for m in s['moves'] if m['role']=='candidate'),
      sum(m['nodes'] for m in u['moves'] if m['role']=='candidate')))
summary={}
for label,subset in [('all',pairs),('owner0',[x for x in pairs if x[0]==0]),
    ('owner1',[x for x in pairs if x[0]==1]),('ply3',[x for x in pairs if x[1]==3]),
    ('ply4',[x for x in pairs if x[1]==4])]:
    summary[label]={'n':len(subset),'lower':sum(x[2] for x in subset)/len(subset),
      'upper':sum(x[3] for x in subset)/len(subset),
      'candidate_nodes_static':sum(x[4] for x in subset),
      'candidate_nodes_unit':sum(x[5] for x in subset),
      'median_frac_reduction':statistics.median([(x[5]-x[4])/max(x[5],1) for x in subset])}
print(json.dumps({'games':len(rows),'paired':len(pairs),
 'terminals':sum(x['terminal_reason']=='ACTUAL_TERMINAL' for x in rows),
 'unknown':sum(x['reward'] is None for x in rows),
 'type_calls':sum(x['type_value_calls'] for x in rows),
 'capture_calls_by_arm':{arm:sum(x['capture_order_calls'] for x in rows if x['variant']==arm) for arm in plan['arms']['candidate_arms']},
 'summary':summary,
 'game_sha':hashlib.sha256((r/'capture-order-games.jsonl').read_bytes()).hexdigest()},separators=(',',':'))
)