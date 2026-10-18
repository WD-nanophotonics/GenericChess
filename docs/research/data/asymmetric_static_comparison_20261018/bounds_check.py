"""Independent recomputation of the reported W-L bounds and pair counts.

Deliberately does NOT import analyze.py: it re-pairs the frozen slots, uses
exact Fraction interval arithmetic, and compares against analysis.json.  It
cannot detect a shared design error, but it does catch a pairing/arithmetic bug
in the reported analysis.
"""
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

D = Path(__file__).resolve().parent
slots = json.loads((D / 'slots.json').read_text())['slots']
games = {}
for line in (D / 'games.jsonl').open():
    g = json.loads(line)
    games[g['slot']] = g

logical = {}
for slot, (rule, family, label, owner, foe) in enumerate(slots):
    g = games.get(slot)
    if g is None:
        g = dict(slot=slot, rule=rule, family=family, label=label,
                 candidate_owner=owner, foe=foe, reward=None,
                 ending='UNSTARTED_UNKNOWN')
    logical[rule, family, label, owner, foe] = g
    if label == 'unit' and foe == 'uniform':
        logical[rule, family, label, 1, foe] = dict(
            g, candidate_owner=1,
            reward=None if g['reward'] is None else -g['reward'])


def interval(pairs):
    lo = hi = Fraction(0)
    for a, b in pairs:
        a0, a1 = ((Fraction(-1), Fraction(1)) if a['reward'] is None
                  else (Fraction(a['reward']),) * 2)
        b0, b1 = ((Fraction(-1), Fraction(1)) if b['reward'] is None
                  else (Fraction(b['reward']),) * 2)
        lo += a0 - b1
        hi += a1 - b0
    return [float(lo / len(pairs)), float(hi / len(pairs))]


rules = sorted({s[0] for s in slots})
families = defaultdict(set)
for rule, family, *_ in slots:
    families[rule].add(family)

recomputed = {}
for foe in ('uniform', 'fixed_random99031_channels'):
    pooled, per_rule, per_owner = [], defaultdict(list), defaultdict(list)
    counts = Counter()
    for rule in rules:
        for family in sorted(families[rule]):
            for owner in (0, 1):
                a = logical[rule, family, 'rule_static_v2', owner, foe]
                b = logical[rule, family, 'unit', owner, foe]
                pooled.append((a, b))
                per_rule[rule].append((a, b))
                per_owner[owner].append((a, b))
                known = a['reward'] is not None and b['reward'] is not None
                counts['resolved_pairs'] += known
                counts['resolved_better'] += known and a['reward'] > b['reward']
                counts['resolved_worse'] += known and a['reward'] < b['reward']
                counts['both_unknown'] += (a['reward'] is None
                                           and b['reward'] is None)
                counts['one_unknown'] += ((a['reward'] is None)
                                          != (b['reward'] is None))
    recomputed[foe] = dict(
        pairs=len(pooled), bounds=interval(pooled), counts=dict(counts),
        per_rule={rule: interval(v) for rule, v in per_rule.items()},
        per_owner={str(o): interval(v) for o, v in per_owner.items()})

analysis = json.loads((D / 'analysis.json').read_text())
zero_crossing = 0
for block in analysis['contrasts']:
    mine = recomputed[block['foe']]
    assert mine['pairs'] == block['pairs'], (block['foe'], mine['pairs'])
    assert mine['bounds'] == block['bounds'], (block['foe'], mine['bounds'],
                                                block['bounds'])
    for key, value in mine['counts'].items():
        assert value == block['counts'][key], (block['foe'], key, value,
                                               block['counts'][key])
    assert {str(k): v for k, v in mine['per_rule'].items()} == block['per_rule'], \
        block['foe']
    assert mine['per_owner'] == block['per_owner'], block['foe']
    assert mine['pairs'] == 384, mine['pairs']
    for cell in ([block['bounds']] + list(block['per_rule'].values())
                 + list(block['per_owner'].values())):
        assert cell[0] <= 0 <= cell[1], (block['foe'], cell)
        zero_crossing += 1
assert all(len(families[r]) == 32 for r in rules)

print(json.dumps(dict(
    status='PASS',
    pairs={f: v['pairs'] for f, v in recomputed.items()},
    resolved={f: v['counts']['resolved_pairs'] for f, v in recomputed.items()},
    zero_crossing_intervals=zero_crossing,
    note='unsigned W-L bounds/counts recomputed with Fractions and equal to '
         'analysis.json for both foes; every pooled, per-rule and per-owner '
         'interval contains zero'), indent=1))
