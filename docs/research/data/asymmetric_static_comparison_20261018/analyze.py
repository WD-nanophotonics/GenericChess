"""Coupled actual-outcome analysis for the asymmetric/free-rule comparator."""
from pathlib import Path
from collections import defaultdict, Counter
import json, sys, random, time

R = Path.cwd()
sys.path.insert(0, str(R))
from tools.local_agent.common import write_json

D = R / '.local_agent/asymmetric-static-20261018'
START = time.perf_counter()
PLAN = json.loads((D / 'plan.json').read_bytes())
DONE = json.loads((D / 'result.json').read_bytes())
SLOTS = json.loads((D / 'slots.json').read_bytes())['slots']
ROOTS = json.loads((D / 'roots.json').read_bytes())
RULES = DONE['rules']
physical = {}
for line in (D / 'games.jsonl').read_bytes().splitlines():
    g = json.loads(line)
    physical[g['slot']] = g
logical = {}
for slot, (gs, f, label, owner, foe) in enumerate(SLOTS):
    g = physical.get(slot, dict(slot=slot, rule=gs, family=f, label=label,
                                candidate_owner=owner, foe=foe, reward=None,
                                record=None, ending='UNSTARTED_UNKNOWN',
                                queries=0, nodes=0))
    logical[gs, f, label, owner, foe] = g
    if label == 'unit' and foe == 'uniform':
        logical[gs, f, label, 1, foe] = dict(
            g, candidate_owner=1,
            reward=None if g['reward'] is None else -g['reward'],
            logical_role_copy_only=True)


def outcome(g):
    r = g['reward']
    return 'U' if r is None else ('W' if r == 1 else 'L' if r == -1 else 'D')


def bounds(pairs):
    """Exact finite interval for mean(reward_left - reward_right), UNKNOWN=[-1,1]."""
    lo = hi = 0.0
    for left, right in pairs:
        if left['reward'] is None:
            l0, l1 = -1.0, 1.0
        else:
            l0 = l1 = float(left['reward'])
        if right['reward'] is None:
            r0, r1 = -1.0, 1.0
        else:
            r0 = r1 = float(right['reward'])
        lo += l0 - r1
        hi += l1 - r0
    n = len(pairs)
    return [lo / n, hi / n]


profiles = []
for foe in PLAN['foes']:
    for label in PLAN['profiles']:
        rows = [g for (gs, f, t, o, v), g in logical.items()
                if t == label and v == foe]
        profiles.append(dict(
            foe=foe, label=label, cells=len(rows),
            outcomes=dict(Counter(outcome(r) for r in rows)),
            physical_slots=len({r['slot'] for r in rows})))

contrasts = []
for foe in PLAN['foes']:
    pairs_all = []
    groups = defaultdict(list)
    per_owner = defaultdict(list)
    counts = Counter()
    # Distinct families only: iterating logical keys directly repeats every
    # (rule, family) once per profile/owner/foe key and would inflate pair counts
    # 8x and over-weight duplicated families in the bootstrap.
    fams = {gs: sorted({f for (g, f, *_rest) in logical if g == gs})
            for gs in RULES}
    for gs in RULES:
        for family in fams[gs]:
            for owner in (0, 1):
                a = logical[gs, family, 'rule_static_v2', owner, foe]
                b = logical[gs, family, 'unit', owner, foe]
                pairs_all.append((a, b))
                groups[gs, family].append((a, b))
                per_owner[owner].append((a, b))
                known = a['reward'] is not None and b['reward'] is not None
                counts['resolved_pairs'] += known
                counts['resolved_better'] += known and a['reward'] > b['reward']
                counts['resolved_worse'] += known and a['reward'] < b['reward']
                counts['both_unknown'] += (a['reward'] is None and b['reward'] is None)
                counts['one_unknown'] += ((a['reward'] is None) != (b['reward'] is None))
                if a['record'] is not None and b['record'] is not None:
                    counts['same_full_records'] += a['record'] == b['record']
    group_bounds = {k: bounds(v) for k, v in groups.items()}
    rng = random.Random(2026101819)
    boot = []
    for _ in range(2000):
        sel = [group_bounds[gs, rng.choice(fams[gs])] for gs in RULES
               for _ in fams[gs]]
        boot.append([sum(z[j] for z in sel) / len(sel) for j in (0, 1)])
    low = sorted(x[0] for x in boot)
    high = sorted(x[1] for x in boot)
    contrasts.append(dict(
        foe=foe, name='static-unit', pairs=len(pairs_all),
        families_per_rule={str(gs): len(fams[gs]) for gs in RULES},
        bounds=bounds(pairs_all),
        per_rule={str(gs): bounds([p for p in pairs_all if p[0]['rule'] == gs])
                  for gs in RULES},
        per_owner={str(o): bounds(v) for o, v in per_owner.items()},
        conditional_fixed_rules_family_95_envelope=[low[49], high[1949]],
        counts=dict(counts),
        scope='UNKNOWN reward kept [-1,+1]; six fixed generated rules; family-group '
              'resampling conditional on those rules; not population confidence.'))

qcounts = Counter()
kernel = caller = maximum = 0.
depths = Counter()
for line in (D / 'queries.jsonl').open():
    q = json.loads(line)
    qcounts['queries'] += 1
    qcounts['fallbacks'] += q['used_fallback']
    qcounts['nodes'] += q['nodes']
    depths[q['completed_depth']] += 1
    kernel += q['kernel_seconds']
    caller += q['caller_seconds']
    maximum = max(maximum, q['caller_seconds'])

result = dict(
    status='COMPLETE_FROZEN_SERVED_CANDIDATE_ANALYSIS' if DONE['status'] == 'COMPLETE'
    else 'PARTIAL_FROZEN_ALLSLOTS_RETAINED',
    planned_physical=DONE['planned_physical'],
    returned_physical=len(physical),
    logical_cells=len(logical),
    rules=RULES,
    profiles=profiles,
    contrasts=contrasts,
    query_counts=dict(qcounts),
    depths=dict(depths),
    kernel_seconds=kernel,
    caller_seconds=caller,
    max_caller_seconds=maximum,
    root_attempts=len(ROOTS['attempts']),
    root_terminal_attempts=sum(a['terminal'] for a in ROOTS['attempts']),
    generation_failures=DONE['generation_failures'],
    seconds=time.perf_counter() - START,
    scope='New served-candidate diagnostic on six freshly generated free_random/'
          'asymmetric rules. No fit, learner, AUX checkpoint, AUX state or default '
          'change. UNKNOWN/missing retained; caps not extended.')
write_json(D / 'analysis.json', result)
print(json.dumps({k: v for k, v in result.items()
                  if k not in ('profiles', 'contrasts')}))
print(json.dumps(contrasts, indent=2))
