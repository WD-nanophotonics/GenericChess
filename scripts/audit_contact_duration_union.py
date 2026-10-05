"""Frozen bounded arithmetic census, not legal states or goal measurements."""
import hashlib
from itertools import product
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.material_interval_choice import material_margin_interval
from scripts.native_chess_contact_intervals import native_contact_intervals

OUT = ROOT/'docs/research/data/contact_duration_union_20261005.json'
SOURCES = ('scripts/audit_contact_duration_union.py', 'scripts/contact_duration_union.py',
           'scripts/material_interval_choice.py', 'scripts/native_chess_contact_intervals.py',
           'docs/research/CONTACT_DURATION_UNION_DESIGN.md')


def digest(p):
    return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()


if __name__ == '__main__':
    if OUT.exists():
        raise FileExistsError('frozen census: do not rerun')
    start = monotonic()
    report = dict(complete=False, comparisons=0, category_counts={}, witnesses={},
                  source_sha256={p: digest(p) for p in SOURCES}, public_transitions=0, goal_queries=0)
    boxes = {m: native_contact_intervals(m) for m in ('geometric_half', 'linear_mixture', 'both')}
    try:
        for difference in product(range(-2, 3), repeat=5):
            if not any(difference):
                continue
            if monotonic()-start >= 15:
                raise TimeoutError('15sec arithmetic cap')
            first = {('board', t): max(n, 0) for t, n in zip(('Q','R','N','B','P'), difference)}
            second = {('board', t): max(-n, 0) for t, n in zip(('Q','R','N','B','P'), difference)}
            margins = {m: material_margin_interval(first, second, box, owner=0) for m, box in boxes.items()}
            choices = {m: ('A' if lo >= 0 else 'B' if hi < 0 else None) for m, (lo, hi) in margins.items()}
            a, b = choices['geometric_half'], choices['linear_mixture']
            if a is None or b is None:
                category = 'within_model_uncertainty'
            elif a != b:
                category = 'duration_disagreement'
            elif choices['both'] is None:
                category = 'stable_union_hull_uncertain'
            else:
                category = 'stable_union_hull_stable'
            report['comparisons'] += 1
            report['category_counts'][category] = report['category_counts'].get(category, 0)+1
            report['witnesses'].setdefault(category, dict(difference=difference, choices=choices,
                margins={m: [str(v) for v in pair] for m, pair in margins.items()}))
        report['complete'] = report['comparisons'] == 3124
    except Exception as e:
        report['error'] = f'{type(e).__name__}: {e}'
    report['seconds'] = monotonic()-start
    report['source_hashes_unchanged'] = all(digest(p) == h for p, h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report))
