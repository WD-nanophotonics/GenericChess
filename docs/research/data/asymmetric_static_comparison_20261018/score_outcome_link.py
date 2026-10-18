"""Does the first-decision served-score margin track the paired W-L outcome?

Post-hoc descriptive link between the `score_margin.py` pairing and the frozen
game rewards.  For each (rule, family, foe, owner) pair whose BOTH games ended
in an actual terminal result, compare

    score margin : static served score - unit served score (first decision)
    outcome diff : static reward - unit reward            (in {-2,-1,0,1,2})

and report a tie-averaged Spearman correlation with a family-cluster bootstrap
envelope, plus the sign-concordance table.  This asks whether the served-score
observable is a usable proxy for the finite W-L comparison.  It is NOT a new
outcome, not a preregistered endpoint, and the both-resolved subset excludes
horizon-UNKNOWN games, so it is not a full-cohort statement.
"""
import json
import random
import statistics
from collections import Counter
from pathlib import Path

import score_margin as sm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'score_outcome_link.json'


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(rows):
    if len(rows) < 3:
        return None
    rx = ranks([r['diff'] for r in rows])
    ry = ranks([r['outcome_diff'] for r in rows])
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) *
           sum((b - my) ** 2 for b in ry)) ** 0.5
    return None if den == 0 else num / den


def clustered_spearman(rows, rng, resamples=2000):
    by_rule_family = {}
    for r in rows:
        by_rule_family.setdefault(r['rule'], {}).setdefault(
            r['family'], []).append(r)
    rules = sorted(by_rule_family)
    stats = []
    for _ in range(resamples):
        pooled = []
        for rule in rules:
            clusters = by_rule_family[rule]
            keys = sorted(clusters)
            for _ in keys:
                pooled.extend(clusters[rng.choice(keys)])
        value = spearman(pooled)
        if value is not None:
            stats.append(value)
    stats.sort()
    return [stats[max(0, int(0.025 * len(stats)))],
            stats[min(len(stats) - 1, int(0.975 * len(stats)) - 1)]]


def build(directory):
    pairs, _, _ = sm.build_pairs(directory)
    reward = {}
    for g in map(json.loads, (directory / 'games.jsonl').open()):
        reward[(g['rule'], g['family'], g['label'], g['foe'],
                g['candidate_owner'])] = g['reward']
    rows, dropped = [], Counter()
    for p in pairs:
        if p['terminal_band']:
            dropped['terminal_band'] += 1
            continue
        ru = reward[(p['rule'], p['family'], 'unit', p['foe'], p['owner'])]
        rs = reward[(p['rule'], p['family'], 'rule_static_v2', p['foe'],
                     p['owner'])]
        if ru is None or rs is None:
            dropped['horizon_unknown'] += 1
            continue
        rows.append(dict(rule=p['rule'], family=p['family'], foe=p['foe'],
                         owner=p['owner'], diff=p['diff'],
                         outcome_diff=rs - ru))
    return rows, dropped


def summarize(rows):
    nz = [r for r in rows
          if r['diff'] != 0 and r['outcome_diff'] != 0]
    concordant = sum((r['diff'] > 0) == (r['outcome_diff'] > 0) for r in nz)
    pos = [r['outcome_diff'] for r in rows if r['diff'] > 0]
    neg = [r['outcome_diff'] for r in rows if r['diff'] < 0]
    per_cell = {}
    for foe in sorted({r['foe'] for r in rows}):
        for owner in sorted({r['owner'] for r in rows if r['foe'] == foe}):
            cell = [r for r in rows
                    if r['foe'] == foe and r['owner'] == owner]
            cnz = [r for r in cell
                   if r['diff'] != 0 and r['outcome_diff'] != 0]
            per_cell[f'{foe}:owner{owner}'] = dict(
                pairs=len(cell),
                spearman=spearman(cell),
                nonzero_both=len(cnz),
                concordant=sum((r['diff'] > 0) == (r['outcome_diff'] > 0)
                               for r in cnz),
            )
    return dict(
        pairs=len(rows),
        by_foe={k: v for k, v in sorted(
            Counter(r['foe'] for r in rows).items())},
        outcome_diff_counts={str(k): v for k, v in sorted(
            Counter(r['outcome_diff'] for r in rows).items())},
        spearman=spearman(rows),
        spearman_family_cluster_envelope=clustered_spearman(
            rows, random.Random(20261018)),
        per_foe_owner=per_cell,
        nonzero_both=len(nz),
        concordant=concordant,
        discordant=len(nz) - concordant,
        sign_test_p_two_sided=sm.sign_test(concordant, len(nz) - concordant),
        mean_outcome_diff_if_score_positive=(
            statistics.fmean(pos) if pos else None),
        mean_outcome_diff_if_score_negative=(
            statistics.fmean(neg) if neg else None),
        owner0_foe_duplicate_note=(
            'owner-0 served scores are identical across the uniform and '
            'fixed-random foes, but their game outcomes are different games; '
            'per_foe_owner cells separate the two gaming contexts, the pooled '
            'correlation does not.'),
    )


if __name__ == '__main__':
    out = {}
    for name, directory in sm.SETS.items():
        rows, dropped = build(directory)
        out[name] = dict(summarize(rows), dropped=dict(dropped), scope=(
            'Post-hoc both-resolved pairs only (terminal-band and '
            'horizon-UNKNOWN excluded); tie-averaged Spearman; family-cluster '
            'bootstrap 2.5/97.5 of 2000 resamples; descriptive, not a new '
            'outcome, not a full-cohort or causal claim.'))
        cell = out[name]
        print(f"{name}: n={cell['pairs']} by_foe={cell['by_foe']} "
              f"spearman={cell['spearman']:+.3f} "
              f"env={[round(x, 3) for x in cell['spearman_family_cluster_envelope']]} "
              f"nonzero={cell['nonzero_both']} concordant={cell['concordant']} "
              f"p={cell['sign_test_p_two_sided']:.3g} dropped={cell['dropped']}")
        print(f"  outcome_diff={cell['outcome_diff_counts']} "
              f"mean outcome diff score+ = "
              f"{cell['mean_outcome_diff_if_score_positive']:+.3f}, score- = "
              f"{cell['mean_outcome_diff_if_score_negative']:+.3f}")
        for key, sub in cell['per_foe_owner'].items():
            rho = sub['spearman']
            print(f"  cell {key}: n={sub['pairs']} "
                  f"spearman={rho:+.3f} nonzero={sub['nonzero_both']} "
                  f"concordant={sub['concordant']}")
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    print(f"wrote {OUT}")
