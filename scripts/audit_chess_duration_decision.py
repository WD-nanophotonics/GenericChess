"""Time sensitivity on corrected histograms and exposed complete child table."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.partial_contact_prior import PartialContactPrior
from scripts.research_record import record_value, write_record
OUT = ROOT/'docs/research/data/chess_duration_decision_20261006.json'
HIST = 'docs/research/data/chess_zero_target_correction_20261005.json'
FOREST = 'docs/research/data/chess_adjudicated_exchange_20261006.json'
SOURCES = ('scripts/audit_chess_duration_decision.py', 'scripts/partial_contact_prior.py',
           'docs/research/CHESS_DURATION_DECISION_PROTOCOL.md', 'scripts/research_record.py', HIST, FOREST)


def main():
    if OUT.exists(): raise FileExistsError('time-sensitivity audit never rerun')
    start = monotonic()
    r = dict(complete=False, arithmetic_terms=0, public_transitions=0, source_queries=0,
             geometry_queries=0, cumulative={}, policies={},
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        hist = json.loads((ROOT/HIST).read_text()); forest = json.loads((ROOT/FOREST).read_text())
        for raw in (hist, forest):
            if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('qualified complete input required')
            for p, digest in raw['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        for mode, row in hist['rows'].items():
            if sum(row['histogram'].values())+row['unreachable'] != 249984: raise ValueError('denominator mismatch')
            r['cumulative'][mode] = {str(n): [sum(v for h, v in row['histogram'].items() if int(h) <= n)]*2 for n in range(1, 9)}
            r['cumulative'][mode]['infinity'] = [249984-row['unreachable']]*2
            r['arithmetic_terms'] += 9
        prior = PartialContactPrior(r['cumulative'], 249984, normalizer='Q')
        r['N_minus_B'] = prior.difference({'N': 1, 'B': -1})
        r['Q_minus_R'] = prior.difference({'Q': 1, 'R': -1})
        r['arithmetic_terms'] += 18
        short = r['cumulative']['N']['2'][0]-r['cumulative']['B']['2'][0]
        late = r['cumulative']['N']['3'][0]-r['cumulative']['B']['3'][0]
        r['two_three_boundary'] = dict(negative_two=short, positive_three=late,
                                       mass_at_three_for_equality=F(-short, late-short))
        masses = {h: {h: F(1)} for h in prior.horizons}
        for law in ('geometric_half', 'linear_mixture'):
            m = (lambda t: F(1, 2**t)) if law == 'geometric_half' else (lambda t: F(2, (t+1)*(t+2)))
            masses[law] = {'0': 1-m(1), **{str(n): m(n)-m(n+1) for n in range(1, 9)}, 'infinity': m(9)}
        r['inventory_vectors'] = {}
        for key, state in forest['children'].items():
            if forest['root_source_goals'][key] is not None: raise ValueError('unexpected root child goal')
            vector = {mode: 0 for mode in 'PNBRQ'}
            for p in state['position']['board']:
                if p and p['current_type_id'] != 'K': vector[p['current_type_id']] += 1 if p['owner'] == 0 else -1
            r['inventory_vectors'][key] = vector
        for name, pmf in masses.items():
            weights = prior.duration(pmf)['normalized']
            scores = {key: sum(F(n)*weights[mode][0] for mode, n in vector.items())/31 for key, vector in r['inventory_vectors'].items()}
            best = max(scores.values()); ties = sorted(key for key, score in scores.items() if score == best)
            r['policies'][name] = dict(selected=ties[0], tie_set=ties, scores=scores,
                                       n_minus_b=weights['N'][0]-weights['B'][0])
            r['arithmetic_terms'] += len(scores)
        if r['arithmetic_terms'] > 256 or monotonic()-start >= 15: raise ValueError('algebra cap')
        r['complete'] = True
        r['not_proved'] = 'new performance, natural population, duration selection or mixed-class goal order'
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps(record_value({k: v for k, v in r.items() if k not in ('source_sha256', 'cumulative', 'inventory_vectors', 'policies')})))
    print(json.dumps(record_value({k: {a: b for a, b in v.items() if a != 'scores'} for k, v in r['policies'].items()})))


if __name__ == '__main__': main()
