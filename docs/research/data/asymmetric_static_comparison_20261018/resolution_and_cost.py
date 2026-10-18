"""Two frozen-data checks behind the reported W-L null.

1. Censoring bias: does the served-score margin differ between pairs that
   resolved and pairs that hit the 64-ply horizon?  The W-L result is largely
   censored, so if the price margin also predicts resolution, the resolved
   subset is not a neutral view of the treatment.
2. Execution symmetry/cost: recompute the reported query/node totals from the
   frozen `queries.jsonl`/`games.jsonl`, confirm every query completed depth 2
   without fallback, and compare per-pair query/node counts and game lengths
   between the two profiles.

Descriptive on frozen evidence; no new search and no new outcome.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import score_margin as sm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'resolution_and_cost.json'


def games_of(directory):
    return [json.loads(line) for line in (directory / 'games.jsonl').open()]


def status(g):
    return 'resolved' if g['reward'] is not None else 'unknown'


def censoring(directory):
    pairs, _, _ = sm.build_pairs(directory)
    by_slot = {g['slot']: g for g in games_of(directory)}
    groups = defaultdict(list)
    for p in pairs:
        if p['terminal_band']:
            continue
        # build_pairs keys are (rule, family, foe, owner); recover the two slots
        # through games.jsonl instead of re-deriving the pairing.
        groups[(p['rule'], p['family'], p['foe'], p['owner'])].append(p)
    rows = []
    for key, ps in groups.items():
        assert len(ps) == 1, key
        rows.append(ps[0])
    # Reconstruct the label slots, so resolution is read per label.
    labels = defaultdict(dict)
    for g in by_slot.values():
        if g['label'] in sm.LABELS:
            labels[(g['rule'], g['family'], g['foe'],
                    g['candidate_owner'])][g['label']] = g
    out = defaultdict(list)
    by_rule = defaultdict(lambda: defaultdict(list))
    missing = 0
    for p in rows:
        key = (p['rule'], p['family'], p['foe'], p['owner'])
        pair = labels.get(key, {})
        if len(pair) != 2:
            missing += 1
            continue
        su = status(pair['unit'])
        ss = status(pair['rule_static_v2'])
        group = f'unit_{su}__static_{ss}'
        out[group].append(p['diff'])
        by_rule[str(p['rule'])][group].append(p['diff'])
    summary = {}
    for group in ('unit_resolved__static_resolved', 'unit_resolved__static_unknown',
                  'unit_unknown__static_resolved', 'unit_unknown__static_unknown'):
        vals = out.get(group, [])
        summary[group] = dict(
            pairs=len(vals),
            mean_diff=(sum(vals) / len(vals)) if vals else None,
            median_diff=sorted(vals)[len(vals) // 2] if vals else None,
            nonzero=sum(v != 0 for v in vals),
        )
    per_rule = {}
    for rule, groups in sorted(by_rule.items()):
        per_rule[rule] = {
            group: dict(pairs=len(vals), mean_diff=sum(vals) / len(vals))
            for group, vals in sorted(groups.items())}
    return dict(by_resolution=summary, by_rule=per_rule,
                missing_pair_slots=missing)


def cost(directory):
    games = games_of(directory)
    queries = [json.loads(line) for line in (directory / 'queries.jsonl').open()]
    q_by_slot = Counter(q['slot'] for q in queries)
    n_by_slot = Counter()
    for q in queries:
        n_by_slot[q['slot']] += q['nodes']
    bad_depth = [q['slot'] for q in queries if q['completed_depth'] != 2]
    fallbacks = [q['slot'] for q in queries if q['used_fallback']]

    by_key = defaultdict(dict)
    for g in games:
        if g['label'] in sm.LABELS:
            by_key[(g['rule'], g['family'], g['foe'],
                    g['candidate_owner'])][g['label']] = g
    same_queries = same_nodes = pairs = 0
    for key, pair in by_key.items():
        if len(pair) != 2:
            continue
        pairs += 1
        u, s = pair['unit'], pair['rule_static_v2']
        same_queries += u['queries'] == s['queries']
        same_nodes += u['nodes'] == s['nodes']

    # Same-state control: at the candidate's first decision both profiles face
    # a byte-identical state, so a node difference there is a profile effect and
    # not a game-length/position-composition effect.
    actor_of = {g['slot']: g['candidate_owner'] for g in games
                if g['label'] in sm.LABELS}
    first = sm.load_queries(directory, actor_of)
    first_pairs = first_same_nodes = 0
    first_nodes = {'unit': [], 'rule_static_v2': []}
    for key, pair in by_key.items():
        if len(pair) != 2:
            continue
        qu = first.get(pair['unit']['slot'])
        qs = first.get(pair['rule_static_v2']['slot'])
        if qu is None or qs is None:
            continue
        assert qu['before_sha256'] == qs['before_sha256'], key
        first_pairs += 1
        first_same_nodes += qu['nodes'] == qs['nodes']
        first_nodes['unit'].append(qu['nodes'])
        first_nodes['rule_static_v2'].append(qs['nodes'])

    per_label = {}
    for label in sm.LABELS:
        gs = [g for g in games if g['label'] == label]
        per_label[label] = dict(
            games=len(gs),
            games_with_queries_in_log=sum(g['slot'] in q_by_slot for g in gs),
            logged_queries=sum(q_by_slot[g['slot']] for g in gs),
            reported_queries=sum(g['queries'] for g in gs),
            logged_nodes=sum(n_by_slot[g['slot']] for g in gs),
            reported_nodes=sum(g['nodes'] for g in gs),
            nodes_per_logged_query=(
                sum(n_by_slot[g['slot']] for g in gs) /
                max(1, sum(q_by_slot[g['slot']] for g in gs))),
            endings=dict(Counter(g['ending'] for g in gs)),
            total_plies=sum(g['relative_plies'] for g in gs),
            max_plies=max(g['relative_plies'] for g in gs),
        )
    slots_without_queries = [g['slot'] for g in games
                             if g['label'] in sm.LABELS
                             and g['slot'] not in q_by_slot]
    missing_set = set(slots_without_queries)
    return dict(
        logged_queries=len(queries),
        logged_nodes=sum(q['nodes'] for q in queries),
        queries_with_completed_depth_1=len(bad_depth),
        queries_with_fallback=len(fallbacks),
        label_slots_without_queries=len(slots_without_queries),
        label_slots_without_queries_and_zero_reported=sum(
            g['queries'] == 0 for g in games if g['slot'] in missing_set),
        label_pairs=pairs,
        pairs_with_identical_query_count=same_queries,
        pairs_with_identical_node_count=same_nodes,
        first_decision_pairs=first_pairs,
        first_decision_same_nodes=first_same_nodes,
        first_decision_mean_nodes={
            k: (sum(v) / len(v)) if v else None
            for k, v in first_nodes.items()},
        per_label=per_label,
    )


if __name__ == '__main__':
    out = {}
    for name, directory in sm.SETS.items():
        out[name] = dict(censoring=censoring(directory), cost=cost(directory),
                         scope=('Frozen files only. Group means use the '
                                'terminal-band-excluded first-decision served '
                                'score diff. Resolution groups are descriptive '
                                'and outcome-adjacent; not a preregistered '
                                'test and not a new outcome.'))
        c = out[name]['censoring']['by_resolution']
        k = out[name]['cost']
        print(name)
        for group, cell in c.items():
            if cell['pairs']:
                print(f"  {group}: n={cell['pairs']} "
                      f"mean={cell['mean_diff']:+.2f} "
                      f"median={cell['median_diff']:+.2f} "
                      f"nonzero={cell['nonzero']}")
        for rule, groups in out[name]['censoring']['by_rule'].items():
            text = ' | '.join(f"{g.replace('unit_', 'U_').replace('static_', 'S_')}"
                              f"={v['pairs']}@{v['mean_diff']:+.1f}"
                              for g, v in groups.items())
            print(f"  rule {rule}: {text}")
        print(f"  cost: logged {k['logged_queries']} queries / "
              f"{k['logged_nodes']} nodes; depth<2 {k['queries_with_completed_depth_1']}"
              f", fallbacks {k['queries_with_fallback']}, "
              f"label_slots_without_queries {k['label_slots_without_queries']} "
              f"(of which zero reported {k['label_slots_without_queries_and_zero_reported']}); "
              f"identical query counts {k['pairs_with_identical_query_count']}"
              f"/{k['label_pairs']}, identical nodes "
              f"{k['pairs_with_identical_node_count']}/{k['label_pairs']}")
        print(f"  first-decision nodes: same {k['first_decision_same_nodes']}"
              f"/{k['first_decision_pairs']}, mean unit "
              f"{k['first_decision_mean_nodes']['unit']:.1f} vs static "
              f"{k['first_decision_mean_nodes']['rule_static_v2']:.1f}")
        for label, cell in k['per_label'].items():
            print(f"  {label}: games={cell['games']} plies={cell['total_plies']} "
                  f"max={cell['max_plies']} endings={cell['endings']} "
                  f"reported={cell['reported_queries']}q/{cell['reported_nodes']}n "
                  f"logged={cell['logged_queries']}q/{cell['logged_nodes']}n "
                  f"nodes/query={cell['nodes_per_logged_query']:.1f}")
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    print(f"wrote {OUT}")
