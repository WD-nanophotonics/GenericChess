"""How large a W-L shift could the frozen paired design have detected?

Post-hoc design statement on the already-frozen pairs only (no new games, no
new outcomes). For every (rule, family, foe, owner) pair whose two games both
terminated, u = reward_static - reward_unit is in {-2,-1,0,1,2}. The script
reports the mean paired contrast, its iid standard error, a rule-cluster
robust standard error (G=6 rules) and a rule x foe cluster-robust error
(G=12), each translated to the two-sided 5% / 80%-power minimum detectable
effect MDE = 2.802*SE in reward units per pair and in wins per 100 resolved
pairs. It also reports the between-rule SD of per-rule means and the number of
independent rules needed to detect a common shift delta.

Assumptions and limits: rules are treated as exchangeable clusters and the
effect as a common additive shift; sigma_rule is estimated from six rules and
is itself uncertain. The UNKNOWN (horizon) cells are excluded here because the
primary worst-case contrast is a bounded-inference interval, not an SE
quantity. This is a power statement conditioned on observed variance, not an
equivalence result, not a population claim and not a new endpoint.
"""
import json
import math
import statistics
from collections import Counter
from itertools import product
from pathlib import Path

import score_margin as sm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'mde_power.json'
Z_POWER = 1.959964 + 0.841621  # two-sided 5%, 80% power
# t quantiles for the small cluster counts used here: (t.975, t.80) by df.
# df 3 = 4 classic rules, 5 = 6 free rules, 7 = 4x2 classic rule-foe cells,
# 11 = 6x2 free rule-foe cells. Anything else falls back to the normal.
T_CRIT = {
    3: (3.182446, 0.978472),
    5: (2.570582, 0.919544),
    7: (2.364624, 0.896030),
    11: (2.200985, 0.875933),
}


def paired_rows(directory):
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
                         owner=p['owner'], u=rs - ru))
    return rows, dropped


def iid_se(values):
    return statistics.stdev(values) / math.sqrt(len(values))


def cluster_se(rows, key):
    """Cluster-robust SE of the mean u with the usual G/(G-1) correction."""
    n = len(rows)
    mean = statistics.fmean(r['u'] for r in rows)
    clusters = {}
    for r in rows:
        clusters.setdefault(key(r), []).append(r['u'])
    g = len(clusters)
    total = sum((sum(v) - n_g * mean) ** 2
                for v in clusters.values() for n_g in [len(v)])
    return math.sqrt(g / (g - 1) * total) / n, g


def summarize(rows, dropped):
    values = [r['u'] for r in rows]
    mean = statistics.fmean(values)
    se_iid = iid_se(values)
    se_rule, g_rule = cluster_se(rows, lambda r: r['rule'])
    se_rule_foe, g_rule_foe = cluster_se(rows, lambda r: (r['rule'], r['foe']))
    t_lo_5, t_pw_5 = T_CRIT.get(g_rule - 1, (1.959964, 0.841621))
    t_lo_11, t_pw_11 = T_CRIT.get(g_rule_foe - 1, (1.959964, 0.841621))
    per_rule = {}
    for rule in sorted({r['rule'] for r in rows}):
        cell = [r['u'] for r in rows if r['rule'] == rule]
        per_rule[str(rule)] = dict(pairs=len(cell),
                                   mean=statistics.fmean(cell),
                                   wins_minus_losses=sum(cell))
    rule_means = [v['mean'] for v in per_rule.values()]
    sigma_rule = statistics.stdev(rule_means)
    # Exact rule-level sign-flip test of the sharp null "no effect in any rule":
    # flip each rule's whole contribution; 2**G assignments, two-sided.
    by_rule = {}
    for r in rows:
        by_rule.setdefault(r['rule'], []).append(r['u'])
    n_total = len(rows)
    contributions = [(len(v), statistics.fmean(v)) for v in by_rule.values()]
    observed = mean
    hits = 0
    assigns = 0
    for signs in product((1, -1), repeat=len(contributions)):
        assigns += 1
        stat = sum(s * n_g * m for s, (n_g, m) in zip(signs, contributions))
        hits += abs(stat / n_total) >= abs(observed) - 1e-12
    loo = {}
    for rule in by_rule:
        rest = [r['u'] for r in rows if r['rule'] != rule]
        loo[str(rule)] = statistics.fmean(rest)
    required = {}
    for delta in (0.05, 0.10, 0.20):
        required[f'{delta:.2f}'] = math.ceil((Z_POWER * sigma_rule / delta) ** 2)
    return dict(
        pairs=len(rows),
        dropped=dict(dropped),
        mean_u=mean,
        iid_se=se_iid,
        rule_cluster_se=se_rule,
        rule_clusters=g_rule,
        rule_foe_cluster_se=se_rule_foe,
        rule_foe_clusters=g_rule_foe,
        mde80_iid=Z_POWER * se_iid,
        mde80_rule_cluster=Z_POWER * se_rule,
        mde80_rule_foe_cluster=Z_POWER * se_rule_foe,
        mde80_rule_cluster_t=(t_lo_5 + t_pw_5) * se_rule,
        mde80_rule_foe_cluster_t=(t_lo_11 + t_pw_11) * se_rule_foe,
        mde80_rule_cluster_wins_per_100_pairs=50 * (t_lo_5 + t_pw_5) * se_rule,
        ci95_halfwidth_rule_cluster=1.959964 * se_rule,
        ci95_halfwidth_rule_cluster_t=t_lo_5 * se_rule,
        ci95_rule_cluster_t=[mean - t_lo_5 * se_rule, mean + t_lo_5 * se_rule],
        per_rule=per_rule,
        between_rule_sd=sigma_rule,
        rule_sign_flip_p_two_sided=hits / assigns,
        rule_sign_flip_assignments=assigns,
        leave_one_rule_out_range=[min(loo.values()), max(loo.values())],
        leave_one_rule_out=loo,
        rules_needed_for_common_shift=required,
        u_counts={str(k): v for k, v in sorted(Counter(values).items())},
    )


if __name__ == '__main__':
    out = {}
    for name, directory in sm.SETS.items():
        rows, dropped = paired_rows(directory)
        out[name] = summarize(rows, dropped)
        out[name]['scope'] = (
            'Post-hoc both-resolved pairs only; UNKNOWN and terminal-band pairs '
            'excluded; rule-exchanged clustering; MDE=2.802*SE; no new games '
            'or outcomes; not equivalence and not a population claim.')
        cell = out[name]
        print(f"{name}: n={cell['pairs']} mean_u={cell['mean_u']:+.4f} "
              f"iid_se={cell['iid_se']:.4f} rule_se={cell['rule_cluster_se']:.4f} "
              f"ruleXfoe_se={cell['rule_foe_cluster_se']:.4f}")
        print(f"  MDE80 reward units: iid={cell['mde80_iid']:.3f} "
              f"rule-cluster={cell['mde80_rule_cluster']:.3f} "
              f"rule-cluster(t5)={cell['mde80_rule_cluster_t']:.3f} "
              f"({cell['mde80_rule_cluster_wins_per_100_pairs']:.1f} wins/100 "
              f"pairs) ruleXfoe={cell['mde80_rule_foe_cluster']:.3f}; "
              f"CI95(t5)={[round(x, 3) for x in cell['ci95_rule_cluster_t']]}")
        print(f"  between-rule SD={cell['between_rule_sd']:.3f}; rules needed "
              f"delta .05/.10/.20 -> "
              f"{list(cell['rules_needed_for_common_shift'].values())}")
        print(f"  rule sign-flip p={cell['rule_sign_flip_p_two_sided']:.4f} "
              f"({cell['rule_sign_flip_assignments']} assignments); LOO means "
              f"{[round(x, 3) for x in cell['leave_one_rule_out_range']]}")
        print(f"  u_counts={cell['u_counts']} dropped={cell['dropped']}")
        for rule, sub in cell['per_rule'].items():
            print(f"    rule {rule}: n={sub['pairs']} "
                  f"mean={sub['mean']:+.4f} sum={sub['wins_minus_losses']:+d}")

    checks = {
        'free_pairs_166': out['free6_nonmirror_5x5']['pairs'] == 166,
        'classic_pairs_255': out['classic4_bilateral_4x4']['pairs'] == 255,
        'six_free_rule_clusters': (
            out['free6_nonmirror_5x5']['rule_clusters'] == 6),
        'twelve_rule_foe_clusters': (
            out['free6_nonmirror_5x5']['rule_foe_clusters'] == 12),
        'mde_positive': all(out[n]['mde80_rule_cluster'] > 0 for n in out),
        'mde_at_least_observed_mean': all(
            out[n]['mde80_rule_cluster'] >= abs(out[n]['mean_u'])
            for n in out),
        'rule_cluster_t_ci_reported': all(
            len(out[n]['ci95_rule_cluster_t']) == 2 for n in out),
        'sign_flip_p_in_unit_interval': all(
            0 < out[n]['rule_sign_flip_p_two_sided'] <= 1 for n in out),
    }
    out['checks'] = checks
    out['status'] = 'PASS' if all(checks.values()) else 'FAIL'
    failed = sorted(k for k, v in checks.items() if not v)
    if failed:
        raise SystemExit('mde_power FAILED: ' + ', '.join(failed))
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    print(f"status={out['status']} wrote {OUT}")
