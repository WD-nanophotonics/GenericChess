"""Check the report's quoted numbers against the frozen JSON outputs.

Not a science run: it re-derives nothing and only guards against transcription
drift between `analysis.json` / `describe.json` / `score_margin.json` and the
markdown report that GPT will review.  Every assertion names the report sentence
or table row it protects.

Path portability: this script runs unchanged from either the private working
directory or the published `docs/research/data/...` copy.  The report is found
under the enclosing repository root, not a fixed parent offset.

The five wording checks that read `docs/research/LOCAL_MAINLINE.md` are opt-in
via `--mainline PATH` because that document is PRIMARY-owned mutable research
state, not part of this auxiliary evidence copy.  Without the flag they are
skipped and listed in the output rather than silently reported as passing.
"""
import argparse
import json
import re
import hashlib
from pathlib import Path

D = Path(__file__).resolve().parent
REPO = next(p for p in D.parents if (p / 'docs' / 'research').is_dir())

parser = argparse.ArgumentParser()
parser.add_argument(
    '--report', type=Path, default=None,
    help='report markdown (default: <repo>/docs/research/'
         'ASYMMETRIC_FREE_RULE_STATIC_COMPARISON_20261018.md)')
parser.add_argument(
    '--mainline', type=Path, default=None,
    help='enable the five mainline-wording checks against this file')
ARGS = parser.parse_args()

REPORT = ARGS.report or (REPO / 'docs' / 'research' /
                         'ASYMMETRIC_FREE_RULE_STATIC_COMPARISON_20261018.md')
analysis = json.loads((D / 'analysis.json').read_text())
describe = json.loads((D / 'describe.json').read_text())
margin = json.loads((D / 'score_margin.json').read_text())
text = REPORT.read_text()
flat = re.sub(r'\s+', ' ', text)

checks = []
skipped = []
mainline = (re.sub(r'\s+', ' ', ARGS.mainline.read_text())
            if ARGS.mainline is not None else None)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(got, want, tol):
    assert abs(got - want) <= tol, (got, want)


# 0. Frozen inputs still match the hashes recorded before any outcome.
frozen = json.loads((D / 'producer-source.json').read_text())
for key, name in (('producer_sha256', 'producer.py'),
                  ('plan_sha256', 'plan.json'),
                  ('rules_sha256', 'rules.json'),
                  ('models_sha256', 'models.json'),
                  ('roots_sha256', 'roots.json')):
    assert sha256(D / name) == frozen[key], (name, sha256(D / name), frozen[key])
checks.append('5 frozen inputs still match producer-source.json hashes')

# 0b. Supervisor corrections: bundled-domain wording and paid-node-only cost.
for phrase in (
        'This run is a **bundled sampled-domain change**, not an isolation of '
        'one factor.',
        'board size (4 -> 5), setup (`classic_like` -> `free_random`)',
        'the post-prefix horizon (128 -> 64 plies; both `plan.json`)',
        '**not** the AUX random99031 vector',
        'That establishes **paid-node parity only** at a fixed state.',
        'wall and lifecycle cost neutrality remain unestablished'):
    assert phrase in flat, phrase
assert 'adds no per-query node cost' not in flat
assert 'cost-neutral per query' not in flat
checks.append('report states the bundled domain change and paid-node-only '
              'parity (no per-query/lifecycle neutrality claim)')


def close_reported(literal, want):
    """Allow exactly the rounding implied by the printed literal."""
    literal = literal.strip().lstrip('+')
    decimals = len(literal.split('.')[1]) if '.' in literal else 0
    close(float(literal), want, 0.5 * 10 ** -decimals + 1e-12)


def interval(text_value):
    m = re.fullmatch(r'\[(-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?)\]',
                     text_value.strip())
    assert m, text_value
    return float(m.group(1)), float(m.group(2))


def same_interval(got, want, tol=5e-7):
    assert len(got) == len(want) == 2
    assert all(abs(a - b) <= tol for a, b in zip(got, want)), (got, want)


contrast = {c['foe']: c for c in analysis['contrasts']}

# 1. Pooled W-L table (report "Paired candidate-minus-Unit reward").
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 7 or row[0] not in ('uniform', 'fixed random channels'):
        continue
    foe = 'uniform' if row[0] == 'uniform' else 'fixed_random99031_channels'
    c = contrast[foe]
    same_interval(interval(row[1]), c['bounds'])
    same_interval(interval(row[2]),
                  c['conditional_fixed_rules_family_95_envelope'])
    assert c['counts']['resolved_pairs'] == int(row[3]), (foe, row[3])
    better, worse, equal = (int(x) for x in row[4].split('/'))
    assert (c['counts']['resolved_better'], c['counts']['resolved_worse'],
            c['counts']['resolved_pairs'] - c['counts']['resolved_better']
            - c['counts']['resolved_worse']) == (better, worse, equal), foe
    assert c['counts']['both_unknown'] == int(row[5]), (foe, row[5])
    assert c['counts']['one_unknown'] == int(row[6]), (foe, row[6])
checks.append('pooled W-L table matches both contrasts exactly')

# 2. Per-rule W-L table.
rows = 0
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 3 or not re.fullmatch(r'28100[1-6]', row[0]):
        continue
    rule = int(row[0])
    for cell, foe in ((row[1], 'uniform'),
                      (row[2], 'fixed_random99031_channels')):
        same_interval(interval(cell), contrast[foe]['per_rule'][str(rule)])
    rows += 1
assert rows == 6, rows
checks.append('per-rule W-L table matches 6 rules x 2 foes')

# 3. Prose per-owner W-L intervals.
m = re.search(r'Per owner: uniform owner 0 `(\[[^`]+\])`, owner 1 `(\[[^`]+\])`; '
              r'fixed random owner 0 `(\[[^`]+\])`, owner 1 `(\[[^`]+\])`', flat)
assert m, 'per-owner prose not found'
for cell, foe, owner in ((m.group(1), 'uniform', '0'),
                         (m.group(2), 'uniform', '1'),
                         (m.group(3), 'fixed_random99031_channels', '0'),
                         (m.group(4), 'fixed_random99031_channels', '1')):
    same_interval(interval(cell), contrast[foe]['per_owner'][owner])
checks.append('prose per-owner W-L intervals match analysis.json')

# 4. Execution/cost bullets.
for pattern, want in (
        (r'(\d+)/\d+ physical games returned', describe['physical_games']),
        (r'([\d,]+) queries;', analysis['query_counts']['queries']),
        (r'([\d,]+) nodes;', analysis['query_counts']['nodes']),
        (r'(\d+) physical terminals', describe['physical_endings']
         ['ACTUAL_TERMINAL']),
        (r'(\d+) horizon UNKNOWN', describe['physical_endings']
         ['HORIZON_UNKNOWN'])):
    m = re.search(pattern, flat)
    assert m, pattern
    assert int(m.group(1).replace(',', '')) == want, (pattern, m.group(1))
logical_endings = describe['endings']
assert re.search(r'logical totals to (\d+) terminals and (\d+) UNKNOWN',
                 flat).groups() == (
    str(logical_endings['ACTUAL_TERMINAL']),
    str(logical_endings['HORIZON_UNKNOWN']))
assert describe['logical_cells'] == 1536
assert describe['known_rewards'] == (1536 - logical_endings['HORIZON_UNKNOWN'])
producer_seconds = json.loads((D / 'result.json').read_text())['seconds']
close(float(re.search(r'Producer wall time ([\d.]+) s', flat).group(1)),
      producer_seconds, 5e-4)
close(float(re.search(r'kernel time ([\d.]+) s', flat).group(1)),
      analysis['kernel_seconds'], 5e-4)
close(float(re.search(r'caller time\s*([\d.]+) s', flat).group(1)),
      analysis['caller_seconds'], 5e-4)
close(float(re.search(r'max single query\s*([\d.]+) s', flat).group(1)),
      analysis['max_caller_seconds'], 5e-5)
assert re.search(r'0 fallbacks', flat)
checks.append('execution bullets match analyze/describe/result JSON')

# 5. Same-state coverage and owner-0 duplication claims.
assert sum(b['same_state_pairs'] for b in margin.values()) == 570 + 342
assert all(b['same_state_pairs'] == b['pairs'] for b in margin.values())
assert all(b['same_root_pairs'] == b['pairs'] for b in margin.values())
assert all(b['same_ply_pairs'] == b['pairs'] for b in margin.values())
dup = (D / 'owner_duplicate_check.log').read_text()
assert 'uniform pairs 192 random pairs 378 common 192' in dup
assert 'identical diffs on common 192' in dup
assert 'same unit root 192 same static root 192' in dup
checks.append('570+342 same-state pairs and 192/192 owner-0 duplicate verified')

# 6. Secondary served-score role table.
datasets = {'free6 non-mirror': 'free6_nonmirror_5x5',
            'classic4 bilateral': 'classic4_bilateral_4x4'}
role_rows = 0
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 9 or row[0] not in datasets:
        continue
    block = margin[datasets[row[0]]]
    foe = ('fixed_random99031_channels' if row[0] == 'free6 non-mirror'
           else 'random99031')
    cell = block['per_foe'][foe]['per_owner'][row[1].split()[0]]
    assert int(row[2].split()[0]) == cell['pairs'] == int(
        row[2].split('(')[1].rstrip(')')), row[2]
    close_reported(row[3], cell['mean'])
    close_reported(row[4], cell['median'])
    assert tuple(int(x) for x in row[5].split('/')) == (
        cell['positive'], cell['zero'], cell['negative']), row[5]
    close_reported(row[6], cell['sign_test_p_two_sided'])
    assert tuple(int(x) for x in row[7].split('/')) == (
        cell['changed_action'], cell['pairs']), row[7]
    for literal, want in zip(row[8].strip('[]').split(','),
                             cell['family_cluster_envelope']):
        close_reported(literal, want)
    role_rows += 1
assert role_rows == 4, role_rows
checks.append('served-score role table matches score_margin.json')

# 7. Identity is the pre-decision state, not the action.
#    The JSON-derived pair counts are always checked; only the wording in
#    PRIMARY's mainline memo needs --mainline.
changed = {name: block['pairs'] - block['same_action_pairs']
           for name, block in margin.items()}
assert changed == {'free6_nonmirror_5x5': 305,
                   'classic4_bilateral_4x4': 99}, changed
if mainline is not None:
    assert '570/570free,342/342classic same root+pre-query hash+ply' in mainline
    assert '305/570free,99/342classic' in mainline
    checks.append('mainline states state-identity vs action-change correctly')
else:
    skipped.append('mainline states state-identity vs action-change correctly')

# 8. Leave-one-rule influence audit (post-hoc, same frozen pairs).
influence = json.loads((D / 'owner_role_influence.json').read_text())
cells = influence['cells']
labels = {'free6 non-mirror': ('free6_nonmirror_5x5',
                               'fixed_random99031_channels'),
          'classic4 bilateral': ('classic4_bilateral_4x4', 'random99031')}
rows = 0
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 5 or row[0] not in labels or row[1] not in ('0', '1'):
        continue
    ds, foe = labels[row[0]]
    c = cells[f'{ds}:{foe}:owner{row[1]}']
    full = c['full']
    assert row[2] == (f"{full['mean']:+.2f} "
                      f"[{full['envelope'][0]:.2f}, "
                      f"{full['envelope'][1]:.2f}]"), row[2]
    pos = sum(v['mean'] > 0 for v in c['per_rule'].values())
    neg = sum(v['mean'] < 0 for v in c['per_rule'].values())
    assert row[3] == f'{pos}+/{neg}-', row[3]
    loo = [v['mean'] for v in c['leave_one_rule_out'].values()]
    assert row[4] == f'[{min(loo):.2f}, {max(loo):.2f}]', row[4]
    rows += 1
assert rows == 4, rows

o1 = cells['free6_nonmirror_5x5:fixed_random99031_channels:owner1']
r6 = o1['per_rule']['281006']
assert (f"rule 281006 alone has mean {r6['mean']:+.2f} (envelope "
        f"`[{r6['envelope'][0]:.2f}, {r6['envelope'][1]:.2f}]`)") in flat
drop6 = o1['leave_one_rule_out']['281006']
assert (f"changes the pooled cell to {drop6['mean']:+.2f} "
        f"`[{drop6['envelope'][0]:.2f}, {drop6['envelope'][1]:.2f}]` "
        f"({drop6['pairs']} pairs, {drop6['positive']}/{drop6['zero']}/"
        f"{drop6['negative']}, sign p 0.0018)") in flat
close(drop6['sign_test_p_two_sided'], 0.0018, 5e-5)

c0 = cells['classic4_bilateral_4x4:random99031:owner0']
c1 = cells['classic4_bilateral_4x4:random99031:owner1']
assert f"rule 271002 ({c0['per_rule']['271002']['mean']:+.2f})" in flat
d02 = c0['leave_one_rule_out']['271002']
assert f"dropping it gives {d02['mean']:+.2f}" in flat
assert f"rule 271001 ({c1['per_rule']['271001']['mean']:+.2f})" in flat
d11 = c1['leave_one_rule_out']['271001']
assert f"dropping it gives {d11['mean']:+.2f}" in flat

cross = influence['cross_role_rules']
n_free = sum(v['both_roles_exclude_zero']
             for v in cross['free6_nonmirror_5x5'].values())
n_classic = sum(v['both_roles_exclude_zero']
                for v in cross['classic4_bilateral_4x4'].values())
same_free = sum(v['same_mean_sign']
                for v in cross['free6_nonmirror_5x5'].values())
same_classic = sum(v['same_mean_sign']
                   for v in cross['classic4_bilateral_4x4'].values())
assert (n_free, n_classic, same_free, same_classic) == (0, 0, 3, 1)
assert '**0/6** free rules and **0/4** classic rules' in flat
assert '3/6 free and 1/4 classic rules' in flat
if mainline is not None:
    assert 'rule281006 only (drop it: +41.58/152,env[6.91,76.46])' in mainline
    assert 'in BOTH owner cells (0/6,0/4); mean signs agree3/6,1/4' in mainline
else:
    skipped.append('mainline leave-one-rule driver and cross-role clauses')

conf = influence['role_confound']
assert conf['free6_nonmirror_5x5'] == dict(
    families_with_both_owners=182, same_first_decision_state_across_owners=0,
    same_ply_across_owners=0, ply_pair_counts={'0->1': 182},
    owner_ply_counts={'0': {'0': 185}, '1': {'1': 182}},
    both_owner_game_groups=576, shared_game_root_across_owners=576)
assert conf['classic4_bilateral_4x4'] == dict(
    families_with_both_owners=92, same_first_decision_state_across_owners=0,
    same_ply_across_owners=0, ply_pair_counts={'0->1': 92},
    owner_ply_counts={'0': {'0': 96}, '1': {'1': 92}},
    both_owner_game_groups=3456, shared_game_root_across_owners=3456)
assert ('every scorable owner-0 pair is at relative ply 0 and every owner-1 '
        'pair at ply 1. The game root itself is shared (576/576 free and '
        '3456/3456 classic both-owner game groups start from the same '
        '`root_state_sha256`), but the candidate\'s first-decision state is '
        'not: 0/182 free and 0/92 classic `(rule, family)` cells have the same '
        'first-decision state in both owners.') in flat
if mainline is not None:
    assert ('every owner0 pair is ply0, every owner1 pair ply1; game roots ARE '
            'shared (576/576free,3456/3456classic both-owner groups) but'
            '0/182free+0/92classic share the first-decision state') in mainline
assert 'Not a candidate-role comparison' in text
checks.append('leave-one-rule audit table, drivers and cross-role counts match '
              'owner_role_influence.json; owner/ply/root confound verified')

# 9. Post-hoc served-score / outcome link (both-resolved subset only).
link = json.loads((D / 'score_outcome_link.json').read_text())
foes = {'free6 non-mirror': ('free6_nonmirror_5x5',
                             'fixed_random99031_channels'),
        'classic4 bilateral': ('classic4_bilateral_4x4', 'random99031')}
rows = 0
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 8 or row[0] not in foes:
        continue
    cell = link[foes[row[0]][0]]
    assert int(row[1]) == cell['pairs'], row[1]
    close_reported(row[2], cell['spearman'])
    for literal, want in zip(row[3].strip('[]').split(','),
                             cell['spearman_family_cluster_envelope']):
        close_reported(literal, want)
    assert int(row[4]) == cell['nonzero_both'], row[4]
    assert tuple(int(x) for x in row[5].split('/')) == (
        cell['concordant'], cell['discordant']), row[5]
    close_reported(row[6], cell['sign_test_p_two_sided'])
    counts = cell['outcome_diff_counts']
    assert tuple(int(x) for x in row[7].split('/')) == tuple(
        counts[str(k)] for k in (-2, -1, 0, 1, 2)), row[7]
    rows += 1
assert rows == 2, rows

rows = 0
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 4 or row[0] not in foes:
        continue
    ds, foe = foes[row[0]]
    cells = link[ds]['per_foe_owner']
    for literal, key in zip(row[1:], (f'uniform:owner0', f'{foe}:owner0',
                                      f'{foe}:owner1')):
        m = re.fullmatch(r'([+-]\d+\.\d+) \((\d+)\)', literal)
        assert m, (row[0], literal)
        close_reported(m.group(1), cells[key]['spearman'])
        assert int(m.group(2)) == cells[key]['pairs'], (key, literal)
    rows += 1
assert rows == 2, rows
assert ('no cell exceeds |rho| = 0.22' in flat
        and '99/166 and 157/255 both-resolved pairs have identical outcomes'
        in flat)
has_mainline = mainline is not None
if has_mainline:
    assert ('166free/' in mainline and '255classic pairs' in mainline
            and 'NO positive support for the served margin as a W-L proxy'
            in mainline)
else:
    skipped.append('mainline score-proxy limitation clause')
link_check = ('served-score/outcome link tables and scope match '
              'score_outcome_link.json')
checks.append(link_check + ('; mainline carries the limitation'
                            if has_mainline
                            else ' (mainline wording check skipped)'))

# 10. Censoring and execution-cost controls.
rc = json.loads((D / 'resolution_and_cost.json').read_text())
groups = {'both resolved': 'unit_resolved__static_resolved',
          'unit resolved, static unknown': 'unit_resolved__static_unknown',
          'unit unknown, static resolved': 'unit_unknown__static_resolved',
          'both unknown': 'unit_unknown__static_unknown'}
rows = 0
for line in text.splitlines():
    row = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(row) != 3 or row[0] not in foes or row[1] not in groups:
        continue
    cell = rc[foes[row[0]][0]]['censoring']['by_resolution'][groups[row[1]]]
    m = re.fullmatch(r'(\d+) / ([+-]\d+\.\d+)', row[2])
    assert m, row[2]
    assert int(m.group(1)) == cell['pairs'], row[2]
    close_reported(m.group(2), cell['mean_diff'])
    rows += 1
assert rows == 8, rows

free = rc['free6_nonmirror_5x5']
classic = rc['classic4_bilateral_4x4']
assert free['cost']['logged_queries'] == analysis['query_counts']['queries']
assert free['cost']['logged_nodes'] == analysis['query_counts']['nodes']
assert free['cost']['queries_with_completed_depth_1'] == 0
assert free['cost']['queries_with_fallback'] == 0
assert free['cost']['label_slots_without_queries'] == 0
assert classic['cost']['label_slots_without_queries'] == 49
assert classic['cost'][
    'label_slots_without_queries_and_zero_reported'] == 49
for block in (free, classic):
    k = block['cost']
    assert k['first_decision_same_nodes'] == k['first_decision_pairs'], k
    assert (k['first_decision_mean_nodes']['unit'] ==
            k['first_decision_mean_nodes']['rule_static_v2'])
    for label in ('unit', 'rule_static_v2'):
        c = k['per_label'][label]
        assert c['logged_queries'] == c['reported_queries']
        assert c['logged_nodes'] == c['reported_nodes']
assert (f"identical node counts in {free['cost']['first_decision_pairs']}/"
        f"{free['cost']['first_decision_pairs']} free and "
        f"{classic['cost']['first_decision_pairs']}/"
        f"{classic['cost']['first_decision_pairs']} classic pairs") in flat
close_reported(
    re.search(r'free: ([\d.]+) unit vs ([\d.]+) static', flat).group(1),
    free['cost']['per_label']['unit']['nodes_per_logged_query'])
close_reported(
    re.search(r'free: ([\d.]+) unit vs ([\d.]+) static', flat).group(2),
    free['cost']['per_label']['rule_static_v2']['nodes_per_logged_query'])
assert 'reverses on 281004' in flat
has_mainline = mainline is not None
if has_mainline:
    assert ('raw logs recompute 59650q/20334363n exactly' in mainline
            and 'informative-censoring NOT established' in mainline)
else:
    skipped.append('mainline cost and censoring clauses')
by_rule = free['censoring']['by_rule']
rev = by_rule['281004']
assert (f"281004 (+{rev['unit_resolved__static_resolved']['mean_diff']:.1f} "
        f"both resolved vs +{rev['unit_unknown__static_resolved']['mean_diff']:.1f} "
        "static-resolved/unit-unknown)") in flat
nonmono = by_rule['281003']
assert (f"281003 ({nonmono['unit_resolved__static_resolved']['mean_diff']:.1f}, "
        f"+{nonmono['unit_resolved__static_unknown']['mean_diff']:.1f}, "
        f"+{nonmono['unit_unknown__static_resolved']['mean_diff']:.1f}, "
        f"+{nonmono['unit_unknown__static_unknown']['mean_diff']:.1f})") in flat
cost_check = ('censoring/cost tables, recomputed totals, same-state node '
              'parity and per-rule reversal/non-monotone prose match '
              'resolution_and_cost.json')
checks.append(cost_check + ('; mainline line matches'
                            if has_mainline
                            else ' (mainline wording check skipped)'))

# 11. Detectable-shift (MDE) section and its independent arithmetic path.
mde = json.loads((D / 'mde_power.json').read_text())
xchk = json.loads((D / 'paired_mean_crosscheck.json').read_text())
assert mde['status'] == 'PASS' and all(mde['checks'].values())
assert xchk['status'] == 'PASS'
free_mde = mde['free6_nonmirror_5x5']
classic_mde = mde['classic4_bilateral_4x4']
for key, block in (('free6_nonmirror_5x5', free_mde),
                   ('classic4_bilateral_4x4', classic_mde)):
    x = xchk[key]
    assert x['pairs'] == x['claimed_pairs'] == block['pairs'], key
    assert x['mean'] == x['claimed_mean'] == block['mean_u'], key
    assert x['rule_cluster_se'] == block['rule_cluster_se'], key
    assert (x['sign_flip_p'] == x['claimed_sign_flip_p']
            == block['rule_sign_flip_p_two_sided']), key
    assert x['duplicate_keys'] == 0 and x['matched_rows'] == block['pairs'], key
assert free_mde['rule_clusters'] == 6 and classic_mde['rule_clusters'] == 4
assert free_mde['rule_sign_flip_assignments'] == 64
assert classic_mde['rule_sign_flip_assignments'] == 16

free_sentence = (
    f"free6: n={free_mde['pairs']}, mean {free_mde['mean_u']:+.3f} reward "
    f"units per pair (about {free_mde['mean_u'] * 50:+.1f} wins per 100 "
    f"resolved pairs), rule-cluster SE {free_mde['rule_cluster_se']:.3f}, "
    f"t({free_mde['rule_clusters'] - 1}) 95% interval "
    f"`[{free_mde['ci95_rule_cluster_t'][0]:.3f}, "
    f"{free_mde['ci95_rule_cluster_t'][1]:+.3f}]`, 80%-power MDE "
    f"{free_mde['mde80_rule_cluster_t']:.3f} units (about "
    f"{free_mde['mde80_rule_cluster_wins_per_100_pairs']:.1f} wins/100).")
classic_sentence = (
    f"classic4: n={classic_mde['pairs']}, "
    f"mean {classic_mde['mean_u']:+.3f}, "
    f"SE {classic_mde['rule_cluster_se']:.3f}, "
    f"t({classic_mde['rule_clusters'] - 1}) interval "
    f"`[{classic_mde['ci95_rule_cluster_t'][0]:.3f}, "
    f"{classic_mde['ci95_rule_cluster_t'][1]:+.3f}]`, MDE "
    f"{classic_mde['mde80_rule_cluster_t']:.3f} units (about "
    f"{classic_mde['mde80_rule_cluster_wins_per_100_pairs']:.1f} wins/100).")
assert free_sentence in flat, free_sentence
assert classic_sentence in flat, classic_sentence
assert (f"The naive iid SEs ({free_mde['iid_se']:.3f}/"
        f"{classic_mde['iid_se']:.3f})") in flat
assert (f"Between-rule SD of per-rule means is "
        f"{free_mde['between_rule_sd']:.3f} (free) and "
        f"{classic_mde['between_rule_sd']:.3f} (classic)") in flat
assert (f"roughly {free_mde['rules_needed_for_common_shift']['0.10']} (free) / "
        f"{classic_mde['rules_needed_for_common_shift']['0.10']} (classic) "
        "independent rules at 80% power, and 0.20 units about "
        f"{free_mde['rules_needed_for_common_shift']['0.20']} / "
        f"{classic_mde['rules_needed_for_common_shift']['0.20']}") in flat
assert (f"p={free_mde['rule_sign_flip_p_two_sided']:.4f} "
        f"({free_mde['rule_sign_flip_assignments']} assignments, free) and "
        f"p={classic_mde['rule_sign_flip_p_two_sided']:.3f} "
        f"({classic_mde['rule_sign_flip_assignments']} assignments, classic)"
        ) in flat
assert (f"`[{free_mde['leave_one_rule_out_range'][0]:.3f}, "
        f"{free_mde['leave_one_rule_out_range'][1]:.3f}]` / "
        f"`[{classic_mde['leave_one_rule_out_range'][0]:.3f}, "
        f"{classic_mde['leave_one_rule_out_range'][1]:.3f}]`") in flat
assert ('more families on the same six rules would reduce only the '
        'within-rule sampling part of `sigma_rule` and would leave the '
        'rule-level df at 5 (3 for classic4). The rule counts quoted above are '
        'a **descriptive, conditional forecast** from the selected '
        'both-resolved games, the estimated rule-level variance and an '
        'exchangeable-rule, common-shift assumption. They are not a universal '
        'prerequisite, not a mandate to launch tens or hundreds of rules, and '
        'not a planned experiment.') in flat
has_mainline = mainline is not None
if has_mainline:
    assert ('DESCRIPTIVE conditional' in mainline
            and 'or a mandate to launch tens/hundreds of rules' in mainline)
else:
    skipped.append('mainline MDE-forecast consequence clauses')
for command in ('mde_power.py', 'paired_mean_crosscheck.py',
                'report_consistency_check.py'):
    assert (f'.venv/Scripts/python.exe '
            f'.local_agent/asymmetric-static-20261018/{command}') in text
mde_check = ('MDE section numbers, sign-flip/LOO values, independent pair '
             'cross-check and reproduction commands match mde_power.json / '
             'paired_mean_crosscheck.json')
checks.append(mde_check + ('; mainline consequence matches'
                           if has_mainline
                           else ' (mainline wording check skipped)'))

# 12. Determinism rerun and the t-quantile verification limitation.
for digest in ('83C262ED699A092A143E608BC6EB6BBC5FA232E99CA6398AFE7DA8C1ACCCD08F',
               'DF0E6BCB19B62587F5306DF51278AE6FADB837A7DB296A7A5FB40B695C782D47'):
    assert digest in flat, digest
assert sha256(D / 'mde_power.json').upper() == (
    '83C262ED699A092A143E608BC6EB6BBC5FA232E99CA6398AFE7DA8C1ACCCD08F')
assert sha256(D / 'paired_mean_crosscheck.json').upper() == (
    'DF0E6BCB19B62587F5306DF51278AE6FADB837A7DB296A7A5FB40B695C782D47')
assert '1.959964 + 0.841621 = 2.801585' in flat
assert 'scipy is not installed in this venv' in flat
assert 'not independently verified here' in flat
assert ('within-rule sampling share at 0.0385/0.1106 (35%) for free6 and '
        '0.0157/0.1354 (12%) for classic4, leaving implied between-rule '
        'variance 0.072/0.120') in flat
vlog = (D / 'variance-decomposition.log').read_text()
assert ('sigma2=0.1106 within_sampling=0.0385 implied_between=0.0721'
        in vlog)
assert ('sigma2=0.1354 within_sampling=0.0157 implied_between=0.1197'
        in vlog)
detlog = (D / 'determinism-check.log').read_text()
assert 'mde_exit=0 crosscheck_exit=0' in detlog
assert detlog.count(' True ') == 2, detlog
qlog = (D / 'quantile-check.log').read_text()
assert 'ModuleNotFoundError' in qlog and '2.801585' in qlog
checks.append('determinism rerun hashes and normal-power constant match the '
              'logged outputs; t-quantile check limitation recorded')

# 13. Every analysis file named in backticks exists beside this script.
referenced = set(re.findall(
    r'`([A-Za-z0-9_.-]+\.(?:py|jsonl|json|log))`', text))
missing = []
gzipped = []
for name in sorted(referenced):
    if (D / name).exists():
        continue
    if name.endswith('.jsonl') and (D / (name + '.gz')).exists():
        # Raw logs are published gzipped; the decompressed bytes are hashed in
        # README and reproduce the private originals exactly.
        gzipped.append(name)
        continue
    missing.append(name)
assert not missing, missing
assert len(referenced) >= 30, len(referenced)
checks.append(f'all {len(referenced)} referenced analysis files exist '
              f'({len(gzipped)} raw jsonl present as .gz)')

print(json.dumps(dict(
    checks=checks,
    mainline_checks=('skipped (--mainline omitted)'
                     if ARGS.mainline is None else 'PASS'),
    skipped_mainline_assertions=skipped,
    status='PASS'), indent=1))
