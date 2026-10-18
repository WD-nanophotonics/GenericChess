"""Second arithmetic path for the both-resolved paired means and rule SE.

It takes the same pair key set as mde_power.py from score_margin.build_pairs,
but re-reads the raw game rewards and recomputes mean(u), the rule-cluster SE
and the exact rule sign-flip p with separate code. This catches reward-sign,
pairing-key and arithmetic drift between the two scripts; because the key set
is shared, it is NOT an independent rerun of the producer or of score_margin.
"""
import json
import math
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

import score_margin as sm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'paired_mean_crosscheck.json'


def rewards(directory):
    out = defaultdict(dict)
    for g in map(json.loads, (directory / 'games.jsonl').open()):
        if g['label'] in ('unit', 'rule_static_v2'):
            out[(g['rule'], g['family'], g['foe'],
                 g['candidate_owner'])][g['label']] = g['reward']
    return out


result = {}
for name, directory in sm.SETS.items():
    pairs, _, _ = sm.build_pairs(directory)
    used = {(p['rule'], p['family'], p['foe'], p['owner']) for p in pairs
            if not p['terminal_band']}
    raw = rewards(directory)
    rows, assert_rows = [], 0
    for key in sorted(used):
        labels = raw.get(key, {})
        if len(labels) != 2:
            raise SystemExit(f'{name}: key {key} lacks both labels')
        ru, rs = labels['unit'], labels['rule_static_v2']
        if ru is None or rs is None:
            continue
        rows.append((key[0], rs - ru))
        assert_rows += 1
    n = len(rows)
    mean = sum(u for _, u in rows) / n
    by_rule = defaultdict(list)
    for rule, u in rows:
        by_rule[rule].append(u)
    total = sum((sum(v) - len(v) * mean) ** 2 for v in by_rule.values())
    g = len(by_rule)
    se = math.sqrt(g / (g - 1) * total) / n
    hits = assigns = 0
    contrib = [(len(v), sum(v) / len(v)) for v in by_rule.values()]
    for signs in product((1, -1), repeat=g):
        assigns += 1
        stat = sum(s * ng * m for s, (ng, m) in zip(signs, contrib)) / n
        hits += abs(stat) >= abs(mean) - 1e-12
    prior = json.loads((ROOT / 'mde_power.json').read_text())[name]
    result[name] = dict(
        pairs=n, claimed_pairs=prior['pairs'],
        mean=mean, claimed_mean=prior['mean_u'],
        rule_cluster_se=se, claimed_se=prior['rule_cluster_se'],
        sign_flip_p=hits / assigns,
        claimed_sign_flip_p=prior['rule_sign_flip_p_two_sided'],
        rule_clusters=g, duplicate_keys=len(used) - len(set(used)),
        matched_rows=assert_rows,
    )
    cell = result[name]
    if cell['pairs'] != prior['pairs']:
        raise SystemExit(f'{name}: pair count {n} != {prior["pairs"]}')
    if abs(mean - prior['mean_u']) > 1e-12:
        raise SystemExit(f'{name}: mean {mean} != {prior["mean_u"]}')
    if abs(se - prior['rule_cluster_se']) > 1e-9:
        raise SystemExit(f'{name}: SE {se} != {prior["rule_cluster_se"]}')
    if abs(cell['sign_flip_p'] - prior['rule_sign_flip_p_two_sided']) > 1e-12:
        raise SystemExit(f'{name}: sign-flip p mismatch')
    print(f"{name}: n={n} mean={mean:+.6f} rule_se={se:.6f} "
          f"sign_flip_p={cell['sign_flip_p']:.4f} matched raw rewards")

result['status'] = 'PASS'
OUT.write_text(json.dumps(result, indent=1) + '\n')
print(f"status=PASS wrote {OUT}")
