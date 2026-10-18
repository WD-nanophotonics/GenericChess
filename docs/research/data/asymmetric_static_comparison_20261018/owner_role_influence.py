"""Leave-one-rule influence audit of the served-score owner cells.

Post-hoc sensitivity check on the SAME frozen pairs used by score_margin.py.
Question: is the pooled negative mean in the free6 owner-1 cell a role-wide
shift, or is it carried by one rule's left tail?  For every reported cell this
prints the per-rule means and the full-vs-leave-one-rule-out summary, reusing
score_margin's tested pairing and family-cluster bootstrap.

No new search or outcome is produced.  The result is descriptive: it does not
turn a post-hoc observable into a preregistered endpoint.
"""
import json
import random
import statistics
from collections import Counter
from pathlib import Path

import score_margin as sm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'owner_role_influence.json'


def stats(rows):
    diffs = [p['diff'] for p in rows]
    pos = sum(d > 0 for d in diffs)
    neg = sum(d < 0 for d in diffs)
    by_rule_family = {}
    for p in rows:
        by_rule_family.setdefault(p['rule'], {}).setdefault(
            p['family'], []).append(p['diff'])
    return dict(
        pairs=len(diffs),
        mean=statistics.fmean(diffs),
        median=statistics.median(diffs),
        positive=pos,
        zero=len(diffs) - pos - neg,
        negative=neg,
        sign_test_p_two_sided=sm.sign_test(pos, neg),
        envelope=sm.bootstrap_envelope(
            by_rule_family, random.Random(20261018)),
    )


def cell(dataset, foe, owner):
    pairs, _, _ = sm.build_pairs(sm.SETS[dataset])
    rows = [p for p in pairs
            if not p['terminal_band'] and p['foe'] == foe
            and p['owner'] == owner]
    rules = sorted({p['rule'] for p in rows})
    per_rule = {}
    for rule in rules:
        rrows = [p for p in rows if p['rule'] == rule]
        s = stats(rrows)
        s['families'] = len({p['family'] for p in rrows})
        per_rule[str(rule)] = s
    leave_one_out = {}
    for rule in rules:
        s = stats([p for p in rows if p['rule'] != rule])
        s['dropped_rule'] = str(rule)
        leave_one_out[str(rule)] = s
    rule_means = [s['mean'] for s in per_rule.values()]
    neg_mass = sum(-s['mean'] * s['pairs'] for s in per_rule.values()
                   if s['mean'] < 0)
    per_rule_neg = {str(r): round(-s['mean'] * s['pairs'], 3)
                    for r, s in per_rule.items() if s['mean'] < 0}
    return dict(
        dataset=dataset,
        foe=foe,
        owner=owner,
        full=stats(rows),
        per_rule=per_rule,
        leave_one_rule_out=leave_one_out,
        rule_mean_median=statistics.median(rule_means),
        rules_positive=sum(m > 0 for m in rule_means),
        rules_negative=sum(m < 0 for m in rule_means),
        negative_mass_by_rule=per_rule_neg,
        largest_negative_mass_share=(
            max(per_rule_neg.values()) / neg_mass if neg_mass else None),
    )


def fmt(s):
    return (f"n={s['pairs']} mean={s['mean']:.2f} med={s['median']:.1f} "
            f"+/0/-={s['positive']}/{s['zero']}/{s['negative']} "
            f"p={s['sign_test_p_two_sided']:.4g} "
            f"env=[{s['envelope'][0]:.2f},{s['envelope'][1]:.2f}]")


CELLS = [
    ('free6_nonmirror_5x5', 'fixed_random99031_channels', 0),
    ('free6_nonmirror_5x5', 'fixed_random99031_channels', 1),
    ('classic4_bilateral_4x4', 'random99031', 0),
    ('classic4_bilateral_4x4', 'random99031', 1),
]

if __name__ == '__main__':
    out = {}
    for dataset, foe, owner in CELLS:
        c = cell(dataset, foe, owner)
        out[f'{dataset}:{foe}:owner{owner}'] = c
        print(f"\n== {dataset} {foe} owner{owner} FULL {fmt(c['full'])}")
        for rule, s in c['per_rule'].items():
            print(f"   rule {rule}: {fmt(s)}")
        for rule, s in c['leave_one_rule_out'].items():
            print(f"   drop {rule}: {fmt(s)}")
        print(f"   rule means: median={c['rule_mean_median']:.2f} "
              f"+rules={c['rules_positive']} -rules={c['rules_negative']} "
              f"largest negative-mass share="
              f"{c['largest_negative_mass_share']:.2%}")

    # Cross-role view: does any rule show an excursion from zero in BOTH
    # candidate roles?  This is the role-replication question at rule level.
    cross = {}
    for dataset in sorted({c[0] for c in CELLS}):
        cells = [v for v in out.values() if v['dataset'] == dataset]
        assert len(cells) == 2, dataset
        by_owner = {v['owner']: v for v in cells}
        cross[dataset] = {}
        for rule in sorted(by_owner[0]['per_rule']):
            row = {}
            for owner in (0, 1):
                s = by_owner[owner]['per_rule'][rule]
                lo, hi = s['envelope']
                row[f'owner{owner}'] = dict(
                    mean=s['mean'], median=s['median'],
                    positive=s['positive'], zero=s['zero'],
                    negative=s['negative'], envelope=[lo, hi],
                    excludes_zero=(lo > 0 or hi < 0))
            row['both_roles_exclude_zero'] = (
                row['owner0']['excludes_zero']
                and row['owner1']['excludes_zero'])
            row['same_mean_sign'] = (
                (row['owner0']['mean'] > 0) == (row['owner1']['mean'] > 0))
            cross[dataset][rule] = row
        n_both = sum(v['both_roles_exclude_zero']
                     for v in cross[dataset].values())
        n_same = sum(v['same_mean_sign'] for v in cross[dataset].values())
        print(f"\n== {dataset}: rules with both-role zero-excluding envelope "
              f"= {n_both}/{len(cross[dataset])}; same mean sign = "
              f"{n_same}/{len(cross[dataset])}")
        for rule, v in cross[dataset].items():
            print(f"   rule {rule}: o0={v['owner0']['mean']:+.2f} "
                  f"o1={v['owner1']['mean']:+.2f} "
                  f"o0x={v['owner0']['excludes_zero']} "
                  f"o1x={v['owner1']['excludes_zero']}")

    # The two owner cells are not a matched pair: check whether the same
    # (rule, family) is queried from the same root/ply in both roles.
    confound = {}
    for dataset in sorted({c[0] for c in CELLS}):
        foe = next(c[1] for c in CELLS if c[0] == dataset)
        pairs, _, _ = sm.build_pairs(sm.SETS[dataset])
        rows = [p for p in pairs
                if not p['terminal_band'] and p['foe'] == foe]
        grouped = {}
        for p in rows:
            grouped.setdefault((p['rule'], p['family']), {})[p['owner']] = p
        both = [v for v in grouped.values() if 0 in v and 1 in v]
        ply_pairs = {}
        for v in both:
            k = f"{v[0]['ply']}->{v[1]['ply']}"
            ply_pairs[k] = ply_pairs.get(k, 0) + 1
        # The game root is a per-(rule, family, label, foe) frozen initial
        # state.  Count how many of those groups paid both candidate owners
        # from the SAME root, to separate "different root" from "same root,
        # different first-decision ply".
        game_groups = {}
        for g in map(json.loads, (sm.SETS[dataset] / 'games.jsonl').open()):
            key = (g['rule'], g['family'], g['label'], g['foe'])
            game_groups.setdefault(key, {})[g['candidate_owner']] = g
        paid_both = [v for v in game_groups.values() if 0 in v and 1 in v]
        confound[dataset] = dict(
            families_with_both_owners=len(both),
            same_first_decision_state_across_owners=sum(
                v[0]['state_sha'] == v[1]['state_sha'] for v in both),
            same_ply_across_owners=sum(
                v[0]['ply'] == v[1]['ply'] for v in both),
            ply_pair_counts=dict(sorted(ply_pairs.items())),
            owner_ply_counts={
                str(owner): dict(sorted(
                    Counter(
                        p['ply'] for p in rows
                        if p['owner'] == owner).items()))
                for owner in (0, 1)},
            both_owner_game_groups=len(paid_both),
            shared_game_root_across_owners=sum(
                v[0]['root_state_sha256'] == v[1]['root_state_sha256']
                for v in paid_both),
        )
        print(f"\n== {dataset} role confound: {confound[dataset]}")

    OUT.write_text(json.dumps(dict(cells=out, cross_role_rules=cross,
                                   role_confound=confound), indent=1) + '\n')
    print(f"\nwrote {OUT}")
