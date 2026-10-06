"""Different bounded algorithm on saved outcomes, never a repeated sample."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.typed_exchange_compression import compressed_order
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/typed_exchange_compression_20261006.json'
RAW = 'docs/research/data/chess_adjudicated_exchange_20261006.json'
OLD = 'docs/research/data/typed_exchange_order_20261006.json'
SOURCES = ('scripts/audit_typed_exchange_compression.py', 'scripts/typed_exchange_compression.py',
           'scripts/typed_exchange_order.py', 'docs/research/TYPED_EXCHANGE_COMPRESSION_PROTOCOL.md',
           'scripts/research_record.py', RAW, OLD)


def main():
    if OUT.exists(): raise FileExistsError('compressed analysis never rerun')
    start = monotonic(); budget = dict(remaining=512, checks=0)
    r = dict(complete=False, comparisons={}, public_transitions=0, source_queries=0,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw = json.loads((ROOT/RAW).read_text()); old = json.loads((ROOT/OLD).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('complete forest required')
        if old['complete'] or old['endpoint_pair_checks'] != 816 or not old['source_hashes_unchanged']:
            raise ValueError('preserved naive budget fault required')
        for original in (raw, old):
            for p, digest in original['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        for law in ('geometric_half', 'linear_mixture'):
            for base in ('unit', 'zero'):
                for kind in ('canonical', 'all_ties'):
                    if monotonic()-start >= 15: raise TimeoutError('whole15sec cap')
                    x = {p: raw['leaves'][p] for p in raw['outcomes'][law][kind]['paths']}
                    y = {p: raw['leaves'][p] for p in raw['outcomes'][base][kind]['paths']}
                    forward = compressed_order(x, y, budget); reverse = compressed_order(y, x, budget)
                    r['comparisons'][law+'/'+base+'/'+kind] = dict(forward=forward, reverse=reverse)
                    if not forward['complete'] or not reverse['complete']: raise ValueError('compression comparison cap')
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['budget'] = budget; r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'comparisons')}))
    print(json.dumps({k: dict(forward=v['forward']['weak_order_proved'], reverse=v['reverse']['weak_order_proved'], tie_subset=v['forward']['candidate_paths_subset_of_baseline']) for k, v in r['comparisons'].items()}))


if __name__ == '__main__': main()
