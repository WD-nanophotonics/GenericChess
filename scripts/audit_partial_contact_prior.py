"""Saved-CDF constructor and shared-parameter consumer, no new game labels."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic, perf_counter
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.partial_contact_prior import PartialContactPrior
from scripts.research_record import record_value, write_record
OUT = ROOT/'docs/research/data/partial_contact_prior_20261006.json'
RAW = 'docs/research/data/diagnostic_duration_order_20261006.json'
SOURCES = ('scripts/audit_partial_contact_prior.py', 'scripts/partial_contact_prior.py',
           'docs/research/PARTIAL_CONTACT_PRIOR_PROTOCOL.md', 'scripts/research_record.py', RAW,
           'docs/research/data/horse_zero_obstruction_20261006.json')


def endpoint_masses(law):
    m = (lambda t: F(1, 2**t)) if law == 'geometric_half' else (lambda t: F(2, (t+1)*(t+2)))
    return {'0': 1-m(1), **{str(n): m(n)-m(n+1) for n in range(1, 18)}, 'infinity': m(18)}


def main():
    if OUT.exists(): raise FileExistsError('frozen prior algebra never rerun')
    start = monotonic()
    r = dict(complete=False, public_transitions=0, geometry_queries=0, source_queries=0,
             arithmetic_terms=0, benchmark_constructor_calls=500, benchmark_comparison_calls=500,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw = json.loads((ROOT/RAW).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('qualified record required')
        for p, digest in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        construction = perf_counter(); prior = PartialContactPrior(raw['cumulative'], raw['total'])
        r['cdf_validation_seconds'] = perf_counter()-construction
        r['endpoints'] = {law: prior.duration(endpoint_masses(law)) for law in ('geometric_half', 'linear_mixture')}
        r['differences'] = {}
        cases = {'R_minus_H': {'R': 1, 'H': -1}, 'H_minus_S': {'H': 1, 'S': -1},
                 'C_minus_S': {'C': 1, 'S': -1}, 'C_minus_E': {'C': 1, 'E': -1},
                 'common_H_R_minus_C': {'R': 1, 'C': -1}, 'two_C_minus_S': {'C': 2, 'S': -1},
                 'H_minus_C_E': {'H': 1, 'C': -1, 'E': -1}, 'H_minus_C_S': {'H': 1, 'C': -1, 'S': -1}}
        for name, delta in cases.items():
            r['differences'][name] = prior.difference(delta)
            r['arithmetic_terms'] += len(prior.horizons)
        r['atom_controls'] = {h: prior.duration({h: F(1)}) for h in prior.horizons}
        # The same common H occurs in both portfolios; difference removes it.
        l = r['endpoints']['geometric_half']['normalized']
        naive = (l['H'][0]+l['R'][0])-(l['H'][1]+l['C'][1])
        r['shared_H_control'] = dict(naive_independent_box_lower=naive,
                                    universal_shared_difference=r['differences']['common_H_R_minus_C']['lower'])
        t = perf_counter()
        for _ in range(500): prior.duration(endpoint_masses('geometric_half'))
        r['constructor500_seconds'] = perf_counter()-t
        t = perf_counter()
        for _ in range(500): prior.difference({'H': 1, 'C': -1, 'S': -1})
        r['comparison500_seconds'] = perf_counter()-t
        r['benchmark_horizon_terms_per_kind'] = 500*len(prior.horizons)
        r['total_import_and_validation_seconds'] = monotonic()-start
        if r['arithmetic_terms'] > 2000 or r['benchmark_horizon_terms_per_kind'] > 20000 or monotonic()-start >= 15:
            raise ValueError('algebra/benchmark budget exceeded')
        r['complete'] = True
        r['scope'] = 'uniform virtual-world CDF; common independent duration; exact five-mode and partial-H interval only'
        r['not_proved'] = 'full H, physical inventory, held-mode, official goal, duration selection or strategic strength'
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps(record_value({k: v for k, v in r.items() if k not in ('source_sha256', 'atom_controls', 'endpoints', 'differences')})))
    print(json.dumps(record_value({k: {a: b for a, b in v.items() if a != 'horizon_bounds'} for k, v in r.get('differences', {}).items()})))


if __name__ == '__main__': main()
