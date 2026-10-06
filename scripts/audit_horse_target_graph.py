"""Independent second moment and target-leg counterexample, not full census."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.horse_target_graph import reverse_distances, forward_oracle, second_mass
from scripts.research_record import write_record, record_value
OUT = ROOT/'docs/research/data/horse_target_graph_20261006.json'
SOURCES = ('scripts/audit_horse_target_graph.py', 'scripts/horse_target_graph.py',
 'docs/research/HORSE_TARGET_GRAPH_PROTOCOL.md', 'scripts/research_record.py',
 'docs/research/data/diagnostic_native_contact_mirrored_20261005.json',
 'docs/research/data/diagnostic_moment_bounds_20261006.json')


def main():
    if OUT.exists(): raise FileExistsError('closed graph/motif qualification never rerun')
    started = monotonic(); r = dict(complete=False, forward_nodes=0, motifs=0,
        public_transitions=0, compiled_queries=0, source_queries=0, rows=[], controls=[],
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save(): r['seconds'] = monotonic()-started; write_record(OUT, r)
    def check():
        if monotonic()-started >= 15: raise TimeoutError('15sec graph/motif family')
    def popped():
        check(); r['forward_nodes'] += 1
        if r['forward_nodes'] > 5000: raise ValueError('5000 forward-node cap')
    def motif():
        check(); r['motifs'] += 1
        if r['motifs'] > 5000: raise ValueError('5000 motif cap')
    save()
    try:
        for width, height in ((3, 3), (4, 2)):
            area = width*height; hist = Counter(); worlds = 0
            for target in range(area):
                for blocker in range(area):
                    if target == blocker: continue
                    distances = reverse_distances(target, blocker, width, height)
                    for source, value in distances.items():
                        independent = forward_oracle(source, target, blocker, width, height, popped)
                        if independent != value: raise ValueError('independent directed distance mismatch')
                        hist[value] += 1; worlds += 1
            formula = second_mass(width, height)
            if hist[1] != formula['direct'] or hist[2] != formula['second']:
                raise ValueError('independent complete small-world prefix mismatch')
            r['rows'].append(dict(width=width, height=height, worlds=worlds, histogram=dict(sorted(hist.items())), formula=formula)); save()
        for source, target, blocker in ((0, 9, 1), (8, 17, 7), (0, 1, 9)):
            check(); exact = reverse_distances(target, blocker, 9, 10)[source]
            naive = reverse_distances(target, blocker, 9, 10, ignore_target_leg=True)[source]
            independent = forward_oracle(source, target, blocker, 9, 10, popped)
            if exact != 0 or independent != exact or naive <= 0:
                raise ValueError('predeclared trapped Horse control not reproduced')
            r['controls'].append(dict(source=source, target=target, blocker=blocker, exact=exact, target_free=naive)); save()
        prefix = second_mass(9, 10, motif); r['full_analytic_prefix'] = prefix
        census = json.loads((ROOT/SOURCES[-2]).read_text()); moments = json.loads((ROOT/SOURCES[-1]).read_text())
        for old in (census, moments):
            if not old['complete'] or not old['source_hashes_unchanged']: raise ValueError('qualified old record required')
            for p, pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != pin: raise ValueError('old source drift')
        horse = next(row for row in census['rows'] if row['profile']['current'] == 'H')
        if horse['histogram']['1'] != prefix['direct'] or horse['histogram']['2'] != prefix['second']:
            raise ValueError('frozen full Horse prefix mismatch')
        r['saved_horse_unreachable'] = horse['unreachable']
        r['slab_zero_metadata'] = []
        for control in r['controls']:
            slab = next(row for row in census['completed_target_slabs'] if row['target'] == control['target'])
            hrow = next(row for row in slab['rows'] if row['profile']['current'] == 'H')
            zero = hrow['counts'].get('0', 0)
            r['slab_zero_metadata'].append(dict(target=control['target'], zero=zero, consistent_with_one_trap=zero >= 1,
                scope='slab count only, no compiled ordered-world attribution'))
        total = 704880; r['moments'] = []
        for row in moments['rows']:
            law = row['law']; m = (lambda t: F(1, 2**t)) if law == 'geometric_half' else (lambda t: F(2, (t+1)*(t+2)))
            lower = (prefix['direct']*m(1)+prefix['second']*m(2))/total
            upper = lower+(total-prefix['direct']-prefix['second'])*m(3)/total
            old_lo, old_hi = map(F, row['horse_interval'])
            if not old_lo <= lower <= upper <= old_hi: raise ValueError('refined prefix interval not nested')
            means = {mode: F(value) for mode, value in row['exact_means'].items()}
            r['moments'].append(dict(law=law, horse_interval=(lower, upper), normalized_interval=(lower/means['R'], upper/means['R']),
                above={mode: lower > value for mode, value in means.items()}, below={mode: upper < value for mode, value in means.items()}))
        r['complete'] = len(r['rows']) == 2 and len(r['controls']) == 3
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == pin for p, pin in r['source_sha256'].items())
    save(); print(json.dumps(record_value({k: v for k, v in r.items() if k not in ('source_sha256', 'rows')})))


if __name__ == '__main__': main()
