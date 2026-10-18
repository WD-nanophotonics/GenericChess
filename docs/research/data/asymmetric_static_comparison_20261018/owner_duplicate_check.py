import json
from pathlib import Path
D = Path('.local_agent/asymmetric-static-20261018')
games = [json.loads(l) for l in (D/'games.jsonl').open()]
slots = {}; actor = {}
for g in games:
    k = (g['rule'], g['family'], g['foe'], g['candidate_owner'])
    slots.setdefault(k, {})[g['label']] = g['slot']
    actor[g['slot']] = g['candidate_owner']
first = {}
for line in (D/'queries.jsonl').open():
    q = json.loads(line); s = q['slot']
    if s not in actor or q['actor'] != actor[s]:
        continue
    p = first.get(s)
    if p is None or q['relative_ply'] < p['relative_ply']:
        first[s] = q
pairs = {}
for k, v in slots.items():
    if len(v) == 2 and v['unit'] in first and v['rule_static_v2'] in first:
        pairs[k] = (first[v['rule_static_v2']]['score'] - first[v['unit']]['score'],
                    first[v['unit']]['before_sha256'],
                    first[v['rule_static_v2']]['before_sha256'])
u = {(k[0], k[1], k[3]): v for k, v in pairs.items() if k[2] == 'uniform'}
r = {(k[0], k[1], k[3]): v for k, v in pairs.items() if k[2] == 'fixed_random99031_channels'}
common = set(u) & set(r)
print('uniform pairs', len(u), 'random pairs', len(r), 'common', len(common))
print('identical diffs on common', sum(u[k][0] == r[k][0] for k in common))
print('same unit root', sum(u[k][1] == r[k][1] for k in common),
      'same static root', sum(u[k][2] == r[k][2] for k in common))
