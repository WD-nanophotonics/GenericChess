"""Secondary same-state served-score comparison on frozen evidence.

For every (rule, family, foe, candidate owner) both label slots start from the
same frozen prefix.  The candidate's FIRST decision therefore occurs in an
identical state under both labels, and the served depth-2 score difference is a
paired ordering-price effect with no horizon censoring.  Reported for the six
new free_random/non-mirror rules and for the four bilateral classic_like rules of
the closed mature-static run so the SAME metric is comparable across the two
mechanism classes.

This is a post-hoc observable choice on already-frozen outcomes; it is not a
preregistered endpoint and not a W-L claim.

The candidate's first-decision served score depends only on its own profile and
the root state, so at owner 0 the `uniform` and `fixed_random99031_channels`
fields measure the same cell; `owner_duplicate_check.py` confirms 192/192
identical roots and diffs.  Results are therefore broken down by candidate
owner, the only non-duplicated split.  That split is NOT a matched role
comparison: every scorable owner-0 pair is at relative ply 0 and every owner-1
pair at ply 1, so no (rule, family) shares the candidate's first-decision state
across owners (0/182 free, 0/92 classic).  The game root is shared: 576/576 free
and 3456/3456 classic both-owner game groups start from the same
`root_state_sha256`, so the owner cells differ in decision state and ply from a
common root, not in the initial position.  `owner_role_influence.py` records
this confound.
"""
import json, random, statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETS = {
    'free6_nonmirror_5x5': ROOT,
    'classic4_bilateral_4x4': ROOT.parent / 'mature-static-20261017',
}
LABELS = ('unit', 'rule_static_v2')
TERMINAL_BAND = 1_000_000


def load_queries(directory, wanted):
    first = {}
    for line in (directory / 'queries.jsonl').open():
        q = json.loads(line)
        slot = q['slot']
        if slot not in wanted or q['actor'] != wanted[slot]:
            continue
        prev = first.get(slot)
        if prev is None or q['relative_ply'] < prev['relative_ply']:
            first[slot] = q
    return first


def sign_test(pos, neg):
    """Two-sided exact binomial p under p=0.5, zeros excluded."""
    n = pos + neg
    if n == 0:
        return None
    # exact two-sided by doubling the smaller tail
    from math import comb, fsum
    k = min(pos, neg)
    tail = fsum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def bootstrap_envelope(by_rule_family, rng, resamples=2000):
    """Family-cluster bootstrap within each rule, then pool across rules.

    Two pairs from the same (rule, family) share a root position, so they are
    not independent draws.  Resampling individual pairs would understate the
    envelope.  Here each rule resamples its DISTINCT families with replacement
    (same count as observed), keeps every scorable pair of each sampled family,
    and the per-resample statistic is the mean over all pooled pairs.
    """
    rules = sorted(by_rule_family)
    stats = []
    for _ in range(resamples):
        pooled = []
        for rule in rules:
            clusters = by_rule_family[rule]
            keys = sorted(clusters)
            for _ in keys:
                pooled.extend(clusters[rng.choice(keys)])
        if pooled:
            stats.append(statistics.fmean(pooled))
    stats.sort()
    return [stats[max(0, int(0.025 * len(stats)))],
            stats[min(len(stats) - 1, int(0.975 * len(stats)) - 1)]]


def summarize(rows, note):
    diffs = [p['diff'] for p in rows]
    pos = sum(d > 0 for d in diffs)
    neg = sum(d < 0 for d in diffs)
    by_rule_family = defaultdict(lambda: defaultdict(list))
    by_rule = defaultdict(list)
    for p in rows:
        by_rule[p['rule']].append(p['diff'])
        by_rule_family[p['rule']][p['family']].append(p['diff'])
    rng = random.Random(20261018)
    return dict(
        pairs=len(rows),
        mean=statistics.fmean(diffs),
        median=statistics.median(diffs),
        min=min(diffs), max=max(diffs),
        positive=pos, zero=len(diffs) - pos - neg, negative=neg,
        sign_test_p_two_sided=sign_test(pos, neg),
        sign_test_note=('exact two-sided binomial, zeros dropped; '
                        'uncorrected post-hoc test, four cells reported'),
        changed_action=sum(not p['same_action'] for p in rows),
        families={str(rule): len(v) for rule, v in by_rule_family.items()},
        family_cluster_envelope=bootstrap_envelope(by_rule_family, rng),
        envelope_note=note,
        rules=dict(sorted(
            (str(rule), dict(
                pairs=len(v),
                mean=statistics.fmean(v),
                positive=sum(d > 0 for d in v),
                negative=sum(d < 0 for d in v),
                families=len(by_rule_family[rule]),
            )) for rule, v in by_rule.items())),
    )


def build_pairs(directory):
    games = [json.loads(line) for line in (directory / 'games.jsonl').open()]
    slots = defaultdict(dict)
    actor_of = {}
    root_of = {}
    for g in games:
        if g['label'] not in LABELS:
            continue
        key = (g['rule'], g['family'], g['foe'], g['candidate_owner'])
        slots[key][g['label']] = g['slot']
        actor_of[g['slot']] = g['candidate_owner']
        root_of[g['slot']] = g['root_state_sha256']
    first = load_queries(directory, actor_of)

    pairs = []
    missing = Counter()
    no_decision = Counter()
    for key, labels in sorted(slots.items()):
        if len(labels) != 2:
            missing[tuple(sorted(LABELS)) if not labels else
                    tuple(l for l in LABELS if l not in labels)] += 1
            continue
        su, ss = labels['unit'], labels['rule_static_v2']
        if su not in first or ss not in first:
            no_decision[tuple(sorted((su in first, ss in first)))] += 1
            continue
        qu, qs = first[su], first[ss]
        pairs.append(dict(
            rule=key[0], family=key[1], foe=key[2], owner=key[3],
            ply=qu['relative_ply'], ply_static=qs['relative_ply'],
            same_state=qu['before_sha256'] == qs['before_sha256'],
            same_root=root_of[su] == root_of[ss],
            state_sha=qu['before_sha256'][:16],
            score_unit=qu['score'], score_static=qs['score'],
            diff=qs['score'] - qu['score'],
            same_action=qu['returned_action'] == qs['returned_action'],
            terminal_band=abs(qu['score']) >= TERMINAL_BAND
                          or abs(qs['score']) >= TERMINAL_BAND,
        ))
    return pairs, missing, no_decision


def analyse(name, directory):
    pairs, missing, no_decision = build_pairs(directory)

    scorable = [p for p in pairs if not p['terminal_band']]
    out = dict(
        dataset=name,
        pairs=len(pairs),
        reused_or_missing_pairs={str(k): v for k, v in missing.items()},
        pairs_without_candidate_decision={str(k): v for k, v in no_decision.items()},
        same_state_pairs=sum(p['same_state'] for p in pairs),
        same_root_pairs=sum(p['same_root'] for p in pairs),
        same_ply_pairs=sum(p['ply'] == p['ply_static'] for p in pairs),
        same_action_pairs=sum(p['same_action'] for p in pairs),
        terminal_band_pairs=len(pairs) - len(scorable),
        plies={str(k): v for k, v in Counter(p['ply'] for p in pairs).items()},
        per_foe={}, per_rule_foe={}, scope=(
            'Same frozen prefix state, candidate first decision only. Served '
            'Native depth-2 actor-perspective score in native units; terminal '
            'band pairs excluded from means and counted. Post-hoc secondary '
            'observable, not W-L and not a preregistered endpoint. Coverage is '
            'limited to cells where the candidate profile actually moved first: '
            'the Unit-vs-uniform owner-0 game is the only paid uniform cell, so '
            'the uniform foe cells contain owner-0 candidate pairs only, while '
            'both-owner cells exist for the fixed-random foes. The served '
            'first-decision score is foe-independent, so the owner-0 cells are '
            'identical across foes; only the owner split adds information. '
            'However the owner split is confounded with ply and decision '
            'state: every scorable owner-0 pair is at relative ply 0 and every '
            'owner-1 pair at ply 1, and no (rule, family) shares the '
            "candidate's first-decision state across owners (0/182 free, 0/92 "
            'classic), although 576/576 free and 3456/3456 classic both-owner '
            'game groups start from the same frozen game root. The role cells '
            'are therefore not a matched replication.'),
    )

    note = ('2.5/97.5 percentile of 2000 resamples; distinct families resampled '
            'with replacement within each rule, all scorable pairs of a sampled '
            'family kept.')
    for foe in sorted({p['foe'] for p in scorable}):
        rows = [p for p in scorable if p['foe'] == foe]
        cell = summarize(rows, note)
        cell['per_owner'] = {}
        for owner in (0, 1):
            orows = [p for p in rows if p['owner'] == owner]
            if orows:
                cell['per_owner'][str(owner)] = summarize(orows, note)
        cell['balanced_owner0'] = summarize(
            [p for p in rows if p['owner'] == 0], note)
        out['per_foe'][foe] = cell
    return out


if __name__ == '__main__':
    result = {name: analyse(name, directory) for name, directory in SETS.items()}
    (ROOT / 'score_margin.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({n: {k: v for k, v in d.items()
                          if k in ('pairs', 'same_state_pairs', 'same_ply_pairs',
                                   'same_action_pairs', 'terminal_band_pairs',
                                   'per_foe')} for n, d in result.items()},
                     indent=1))
