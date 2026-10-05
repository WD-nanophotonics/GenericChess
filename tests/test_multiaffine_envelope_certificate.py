"""Shared box interpolation, switching envelopes and frozen joint proof."""
import hashlib,json
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import pytest
from scripts.multiaffine_envelope_certificate import cube_min,min_envelope_lower
ROOT=Path(__file__).resolve().parents[1]

def evaluate(row,point):
    result=F(0)
    for mask,coefficient in enumerate(row):
        term=F(coefficient)
        for k,x in enumerate(point):
            if mask&(1<<k):term*=x
        result+=term
    return result

def test_multiaffine_vertex_minimum_includes_cross_terms():
    row=(1,-2,3,4,-5,6,-7,8)
    bound=cube_min(row)
    assert bound==min(evaluate(row,p) for p in product((0,1),repeat=3))
    for point in product((0,F(1,3),1),repeat=3):assert bound<=evaluate(row,point)

def test_min_envelope_corners_remain_insufficient():
    zero=(0,)*8;first=(0,1,0,0,0,0,0,0);second=(1,-1,0,0,0,0,0,0)
    assert all(min(evaluate(first,p),evaluate(second,p))==0 for p in product((0,1),repeat=3))
    result=min_envelope_lower([zero],[first,second],[(F(1,2),F(1,2))])
    assert result['lower']==-F(1,2)
    assert min(evaluate(first,(F(1,2),0,0)),evaluate(second,(F(1,2),0,0)))==F(1,2)

def test_complete_saved_joint_certificate_has_no_new_game_events():
    raw=json.loads((ROOT/'docs/research/data/shared_law_hand_20261006.json').read_text())
    assert raw['complete'] and raw['source_hashes_unchanged']
    assert raw['leaf_rows']==43 and raw['pair_terms']==190<=4096
    assert raw['pair_vertex_evaluations']==1952<=4096 and raw['seconds']<15
    assert raw['runtime_pushes']==raw['public_transitions']==raw['source_queries']==0
    rows={key:[tuple(map(F,row)) for row in value] for key,value in raw['rows'].items()}
    candidate=rows[raw['candidate']];denominator=tuple(map(F,raw['denominator']))
    assert denominator[0]>0 and sum(denominator)>0
    for comparison in raw['comparisons']:
        baseline=rows[comparison['baseline']];proof=tuple(map(F,comparison['proof']))
        verified=min_envelope_lower(candidate,baseline,[proof]*len(candidate))
        assert verified['lower']==F(comparison['lower'])>0
        assert F(comparison['normalized_lower'])==verified['lower']/max(denominator[0],sum(denominator))
        # Independent interior checks illustrate the bound; the proof above,
        # not sampling these points, covers the continuous cube.
        for point in ((0,0,0),(1,1,1),(F(1,2),F(1,3),F(2,3))):
            margin=min(evaluate(a,point) for a in candidate)-min(evaluate(b,point) for b in baseline)
            assert margin>=verified['lower']
    assert F(raw['diagnostic_SC_crossover'])==F(394978775728128,396804798952153)
    for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

@pytest.mark.parametrize('row',[(0,)*7,(True,)+(0,)*7,(0.5,)+(0,)*7])
def test_inexact_and_wrong_dimension_fail_closed(row):
    with pytest.raises(ValueError):cube_min(row)

def test_bad_convex_proof_is_not_an_admitted_certificate():
    for proof in ((0,),(2,),(-1,),(True,)):
        with pytest.raises(ValueError):min_envelope_lower([(0,)*8],[(0,)*8],[proof])
