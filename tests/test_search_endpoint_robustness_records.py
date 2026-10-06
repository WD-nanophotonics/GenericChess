import hashlib,json
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_endpoint_agreement_and_interior_disagreement_are_exact():
    r=json.loads((ROOT/'docs/research/data/search_endpoint_robustness_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged']
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['terms']==45 and r['transitions']==r['labels']==0
    g,l,m=(r['rows'][x] for x in ('geometric_half','linear_mixture','midpoint'))
    assert g['full_ties']==l['full_ties']==['B'] and m['full_ties']==['A']
    assert F(m['scores']['A'])==-329 and F(m['scores']['B'])==-10260
    assert [F(x) for x in m['weights']]==[(F(a)+F(b))/2 for a,b in zip(g['weights'],l['weights'])]


def test_derived_exact_tie_boundaries_and_active_leaf_change():
    lo,hi,kink=F(7293,34448),F(27859,34540),F(17576,34494)
    def a(t):return -abs(-17576+34494*t)
    def b(t):return -10283+46*t
    assert 0<lo<F(1,2)<kink<hi<1
    assert a(lo)==b(lo) and a(hi)==b(hi)
    assert a(F(1,2))>b(F(1,2)) and a(0)<b(0) and a(1)<b(1)
