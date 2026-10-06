"""Analyze saved mixed-class outcomes, preserve every real branch."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.typed_exchange_order import typed_set_order
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/typed_exchange_order_20261006.json'
RAW = 'docs/research/data/chess_adjudicated_exchange_20261006.json'
SOURCES = ('scripts/audit_typed_exchange_order.py', 'scripts/typed_exchange_order.py',
           'docs/research/TYPED_EXCHANGE_ORDER_PROTOCOL.md', 'scripts/research_record.py', RAW)


def main():
    if OUT.exists(): raise FileExistsError('typed comparison never rerun')
    start = monotonic()
    r = dict(complete=False, comparisons={}, endpoint_pair_checks=0, public_transitions=0,
             source_queries=0, source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw = json.loads((ROOT/RAW).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('qualified complete forest required')
        for p, digest in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        for law in ('geometric_half', 'linear_mixture'):
            for base in ('unit', 'zero'):
                for kind in ('canonical', 'all_ties'):
                    x = {p: raw['leaves'][p] for p in raw['outcomes'][law][kind]['paths']}
                    y = {p: raw['leaves'][p] for p in raw['outcomes'][base][kind]['paths']}
                    forward = typed_set_order(x, y); reverse = typed_set_order(y, x)
                    r['endpoint_pair_checks'] += forward['endpoint_pair_checks']+reverse['endpoint_pair_checks']
                    r['comparisons'][law+'/'+base+'/'+kind] = dict(forward=forward, reverse=reverse,
                        weak_result_explained_by_tie_policy_subset=forward['weak_order_proved'] and forward['candidate_paths_subset_of_baseline'])
                    if r['endpoint_pair_checks'] > 512 or monotonic()-start >= 15: raise ValueError('comparison budget exceeded')
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'comparisons')}))
    print(json.dumps({k: dict(forward=v['forward']['weak_order_proved'], reverse=v['reverse']['weak_order_proved'], tie_subset=v['weak_result_explained_by_tie_policy_subset']) for k, v in r['comparisons'].items()}))


if __name__ == '__main__': main()
