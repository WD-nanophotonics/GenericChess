"""Finite coefficient hull from qualified CDF, not fitted duration values."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.partial_contact_prior import PartialContactPrior
from scripts.duration_coefficient_hull import exact_vertices, affine_rank, realize_vertex_weights, universal_static_choice
from scripts.research_record import record_value, write_record
OUT = ROOT/'docs/research/data/duration_coefficient_hull_20261006.json'
RAW = 'docs/research/data/chess_duration_decision_20261006.json'
SOURCES = ('scripts/audit_duration_coefficient_hull.py', 'scripts/duration_coefficient_hull.py',
           'scripts/partial_contact_prior.py', 'docs/research/DURATION_COEFFICIENT_HULL_PROTOCOL.md',
           'scripts/research_record.py', RAW)


def main():
    if OUT.exists(): raise FileExistsError('finite hull audit never rerun')
    start = monotonic()
    r = dict(complete=False, public_transitions=0, source_queries=0, geometry_queries=0,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw = json.loads((ROOT/RAW).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('qualified input required')
        for p, digest in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        prior = PartialContactPrior(raw['cumulative'], 249984, normalizer='Q')
        r['vertices'] = exact_vertices(prior); r['rank'] = affine_rank(r['vertices'])
        w = {'1': F(1, 3), '3': F(2, 3)}; pmf = realize_vertex_weights(prior, w)
        coefficients = prior.duration(pmf)['normalized']
        expected = {m: sum(x*r['vertices'][h][m] for h, x in w.items()) for m in prior.cdf}
        if any(coefficients[m] != (v, v) for m, v in expected.items()): raise ValueError('inverse duration map failed')
        r['realization'] = dict(vertex_weights=w, duration_masses=pmf, coefficients=expected)
        r['static_choice'] = universal_static_choice(r['vertices'], raw['inventory_vectors'])
        r['action_vertex_terms'] = len(r['vertices'])*len(raw['inventory_vectors'])
        if r['action_vertex_terms'] > 256 or monotonic()-start >= 15: raise ValueError('finite algebra cap')
        r['complete'] = True
        r['not_proved'] = 'preferred duration, new independent performance, uncertain-H attainable hull or production pruning'
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps(record_value({k: v for k, v in r.items() if k not in ('source_sha256', 'vertices', 'static_choice')})))
    print(json.dumps(record_value({k: v for k, v in r.get('static_choice', {}).items() if k != 'vertex_policies'})))


if __name__ == '__main__': main()
