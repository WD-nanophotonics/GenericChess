"""Descriptive termination/censoring and resolved-pair summary (no new games).

The Unit-vs-uniform owner-0 game is physically reused as the owner-1 logical
cell with ``reward -> -reward`` (same convention as analyze.py); the unmaterialized
owner-1 slot must be reconstructed here rather than read from games.jsonl.
"""
from pathlib import Path
from collections import Counter, defaultdict
import json

D = Path('.local_agent/asymmetric-static-20261018')
rows = [json.loads(l) for l in (D / 'games.jsonl').read_text().splitlines()]
SLOTS = json.loads((D / 'slots.json').read_bytes())['slots']
logical = {}
for slot, (rule, family, label, owner, foe) in enumerate(SLOTS):
    g = next((r for r in rows if r['slot'] == slot), None)
    if g is None:
        g = dict(slot=slot, rule=rule, family=family, label=label,
                 candidate_owner=owner, foe=foe, reward=None, record=None,
                 ending='UNSTARTED_UNKNOWN', queries=0, nodes=0)
    logical[rule, family, label, owner, foe] = g
    if label == 'unit' and foe == 'uniform':
        logical[rule, family, label, 1, foe] = dict(
            g, candidate_owner=1,
            reward=None if g['reward'] is None else -g['reward'],
            logical_role_copy_only=True)
LOGICAL = list(logical.values())
by = defaultdict(list)
for r in LOGICAL:
    by[r['rule'], r['label'], r['foe'], r['candidate_owner']].append(r)

per_rule = {}
for r in LOGICAL:
    per_rule.setdefault(r['rule'], Counter())
    per_rule[r['rule']]['games'] += 1
    per_rule[r['rule']]['terminal'] += r['ending'] == 'ACTUAL_TERMINAL'
    per_rule[r['rule']]['unknown'] += r['reward'] is None
    per_rule[r['rule']]['plies'] += r['queries']

resolved = Counter()
for rule in sorted(per_rule):
    for foe in ('uniform', 'fixed_random99031_channels'):
        for owner in (0, 1):
            for fam in sorted({f for (r, f, t, o, v) in logical
                               if r == rule and t == 'unit' and v == foe and o == owner}):
                x = logical[rule, fam, 'rule_static_v2', owner, foe]
                y = logical[rule, fam, 'unit', owner, foe]
                key = f'{rule}|{foe}|owner{owner}'
                if x['reward'] is None or y['reward'] is None:
                    resolved[key, 'unresolved'] += 1
                    continue
                resolved[key, 'resolved'] += 1
                resolved[key, 'better'] += x['reward'] > y['reward']
                resolved[key, 'worse'] += x['reward'] < y['reward']
                resolved[key, 'equal'] += x['reward'] == y['reward']

out = dict(
    physical_games=len(rows),
    logical_cells=len(LOGICAL),
    known_rewards=sum(r['reward'] is not None for r in LOGICAL),
    logical_reused_owner1_unit_uniform=sum(
        1 for r in LOGICAL if r.get('logical_role_copy_only')),
    endings=dict(Counter(r['ending'] for r in LOGICAL)),
    physical_endings=dict(Counter(r['ending'] for r in rows)),
    per_rule={str(k): dict(v, mean_plies=v['plies'] / v['games'])
              for k, v in per_rule.items()},
    terminal_by_label_foe={str(k): [sum(g['ending'] == 'ACTUAL_TERMINAL' for g in v), len(v)]
                           for k, v in by.items()},
    resolved_pairs={str(k): v for k, v in resolved.items()},
    scope='Descriptive only; censoring at the frozen 64-ply horizon is not a draw.')
(D / 'describe.json').write_text(json.dumps(out, indent=1, sort_keys=True))
print(json.dumps(out, indent=1, sort_keys=True))
