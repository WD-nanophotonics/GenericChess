"""Read-only representation audit of spent evidence; never fit weights."""
import ast
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.material_interval_choice import material_margin_interval


def oriented_difference(first, second, owner):
    if type(owner) is not int or owner not in (0, 1):
        raise ValueError('owner0/1 required')
    if any(type(n) is not int for n in (*first.values(), *second.values())):
        raise ValueError('integer inventory counts required')
    return {k: n for k in first.keys() | second.keys()
            if (n := (first.get(k, 0)-second.get(k, 0))*(1 if owner == 0 else -1))}


def preference_status(difference, weights, preferred_id, other_id):
    """A pair-score check only, not global optimum or weight learning."""
    if any(k not in weights for k in difference):
        raise ValueError('missing feature weight')
    if any(type(w) is not int and not isinstance(w, F) for w in weights.values()):
        raise ValueError('exact weights required')
    margin = sum((n*weights[k] for k, n in difference.items()), F(0))
    return {'oriented_score_margin': margin, 'strict_score_represented': margin > 0,
            'frozen_tie_selects_preferred': margin == 0 and preferred_id < other_id,
            'pair_selects_preferred': margin > 0 or (margin == 0 and preferred_id < other_id)}


def audit():
    sources = ['docs/research/data/small_selector_diagnostic_20261004.json',
               'docs/research/data/two_victim_direct_intervals_20261004.json']
    spent, pilot = [json.loads((ROOT/p).read_text()) for p in sources]
    for data in (spent, pilot):
        for p, h in data['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != h:
                raise ValueError('spent evidence input drift')
    first = {('board', t): sum(F(r['first_mean']) for r in pilot['roots'] if r['type'] == t)/24
             for t in ('P', 'N', 'B', 'R', 'Q')}
    boxes = {('board', t): tuple(map(F, p['raw_interval'])) for t, p in pilot['component_intervals'].items()}
    rows = []
    for root in spent['rows']:
        owner = int(root['owner_flip']); selection = root['selections_before_labels']
        a, b = selection['ordering']['selected'], selection['unit']['selected']
        evidence = root['selected_goal_evidence']
        va = evidence[a]['conditional_bridge']['interval']; vb = evidence[b]['conditional_bridge']['interval']
        low_a, high_b = (va[0], vb[1]) if owner == 0 else (-va[1], -vb[0])
        if low_a <= high_b:
            continue
        parse = lambda k: {ast.literal_eval(t): n for t, n in root['all_child_features'][k].items()}
        fa, fb = parse(a), parse(b); d = oriented_difference(fa, fb, owner)
        rows.append({'preferred': a, 'other': b, 'owner': owner,
                     'oriented_goal_advantage_lower': low_a-high_b,
                     'difference': {str(t): n for t, n in d.items()},
                     'strict_required_by_actual_tie': a > b,
                     'first_action_ablation': preference_status(d, first, a, b),
                     'H2_box_pair_margin': material_margin_interval(fa, fb, boxes, owner=owner)})
    unique = {tuple(sorted(r['difference'].items())) for r in rows}
    return {'scope': 'exposed development representation audit, no new labels/transitions/fitting',
            'rows': rows, 'raw_witness_count': len(rows), 'distinct_oriented_differences': len(unique),
            'zero_difference_witnesses': sum(not r['difference'] for r in rows),
            'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                              [*sources, 'scripts/audit_exposed_inventory_preferences.py', 'scripts/material_interval_choice.py']}}


if __name__ == '__main__':
    target = ROOT/'docs/research/data/exposed_inventory_preferences_20261004.json'
    if not target.parent.is_dir() or target.exists():
        raise ValueError('preserve completed audit; no rerun')
    result = audit()
    target.write_text(json.dumps(result, indent=2, default=str)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, default=str))
