from fractions import Fraction as F
import hashlib,json
from pathlib import Path
from scripts.search_price_ray import affine_line_certificate
ROOT=Path(__file__).resolve().parents[1]


def test_fixed_common_offset_and_negative_projection_are_allowed():
    r=affine_line_certificate([(3,4),(2,4),(0,4)],[(2,7),(5,1)])
    assert r['full_choice_invariant'] and r['projection_signs']==[-1,-1]
    assert r['leaf_parameters']==[F(0),F(1),F(3)]


def test_zero_or_changing_projection_is_not_certified():
    rows=[(0,0),(1,-1)]
    assert not affine_line_certificate(rows,[(2,1),(1,1)])['full_choice_invariant']
    assert not affine_line_certificate(rows,[(2,1),(1,2)])['full_choice_invariant']
    assert affine_line_certificate(rows,[(2,1),(3,1)])['full_choice_invariant']


def test_noncollinear_does_not_mean_sensitive_and_constant_is_certified():
    r=affine_line_certificate([(1,1),(1,0),(0,1)],[(2,1),(1,2)])
    assert not r['affine_line'] and not r['full_choice_invariant']
    assert 'still unproved' in r['reason']
    assert affine_line_certificate([(3,2),(3,2)],[(0,0),(7,1)])['constant']


def test_saved_full_trees_and_immutable_pins():
    r=json.loads((ROOT/'docs/research/data/search_price_ray_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged']
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['states']==51 and r['feature_entries']==255 and r['game_transitions']==r['compiled_queries']==0
    for row in r['rows'].values():
        c=row['certificate'];assert c['full_choice_invariant'] and c['affine_line']
        assert len(set(c['projection_signs']))==1
        assert len({tuple(x) for x in row['full_ties'].values()})==1
