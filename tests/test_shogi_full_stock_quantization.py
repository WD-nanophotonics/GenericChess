import hashlib,json
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.shogi_contact_interval_choice import shogi_contact_intervals
from scripts.shogi_static_inventory import quantize,SCALE
ROOT=Path(__file__).resolve().parents[1]

def test_full_stock_separation_and_exact_pair_orders():
    r=json.loads((ROOT/'docs/research/data/shogi_full_stock_quantization_20261006.json').read_text())
    assert r['complete'] and r['ordinary_tokens']==sum(r['stock'].values())==38
    assert r['max_absolute_score']==3800000<r['static_limit']<r['mate_threshold']<r['mate_score']
    assert F(r['leaf_rounding_error'])==F(19,100000)
    assert F(r['pair_rounding_error'])==F(19,50000)
    assert r['public_transitions']==r['source_queries']==r['distance_worlds']==0
    for row in r['rows']:
        means=exact_board_means(row['law']);weights={t:x/means['TR'] for t,x in means.items()}
        assert row['integer_weights']=={t:quantize(x) for t,x in weights.items()}
        assert row['order_preserved'] and len(row['pairs'])==78
        assert all(x['integer_sign']==x['exact_sign'] for x in row['pairs'])
        for a,b in combinations(weights,2):
            assert (weights[a]>weights[b])==(row['integer_weights'][a]>row['integer_weights'][b])
        assert row['integer_weights']['G']==row['integer_weights']['TP']==row['integer_weights']['TL']==row['integer_weights']['TN']==row['integer_weights']['TS']
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_held_enclosure_keeps_original_uncertainty():
    r=json.loads((ROOT/'docs/research/data/shogi_full_stock_quantization_20261006.json').read_text())
    for row in r['rows']:
        intervals=shogi_contact_intervals(row['law'])
        for t,data in row['held_intervals'].items():
            lo,hi=intervals['hand',t];a,b=data['integer_outer']
            assert tuple(map(F,data['exact']))==(lo,hi)
            assert 0<=a<=b<=SCALE and F(a,SCALE)<=lo<=hi<=F(b,SCALE)
            assert 0<=lo-F(a,SCALE)<F(1,SCALE) and 0<=F(b,SCALE)-hi<F(1,SCALE)
            if lo<hi:assert a<b
