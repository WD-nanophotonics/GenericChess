"""Shared-parameter switching and exact certificates, not corner sampling."""
from fractions import Fraction as F
from itertools import product
import pytest
from scripts.shared_min_envelope_certificate import min_envelope_margin_lower,affine_box_min

def value(rows,point):
    return min(row[0]+sum(c*x for c,x in zip(row[1:],point)) for row in rows)

def test_vertex_ties_do_not_certify_minimax_choice():
    a=[(0,0)];b=[(0,1),(1,-1)];box=[(0,1)]
    assert all(value(a,(h,))==value(b,(h,)) for h in (0,1))
    result=min_envelope_margin_lower(a,b,box,[(F(1,2),F(1,2))])
    assert result['lower']==-F(1,2)
    assert value(a,(F(1,2),))-value(b,(F(1,2),))==result['lower']
    assert min_envelope_margin_lower(b,a,box,[(1,),(1,)])['lower']==0

def test_combinations_bound_every_shared_point_and_cancellation():
    first=[(F(1,3),2,-1),(1,-2,3)]
    second=[(0,2,-1),(-1,0,2)]
    box=[(-1,2),(0,3)]
    for proof in ((1,0),(0,1),(F(1,2),F(1,2))):
        bound=min_envelope_margin_lower(first,second,box,[proof,proof])['lower']
        for point in product((-1,F(1,2),2),(0,F(3,2),3)):
            assert bound<=value(first,point)-value(second,point)
    # Both leaves share a large uncertain feature. Difference certificates
    # cancel it exactly; independent per-leaf interval subtraction would not.
    assert min_envelope_margin_lower([(3,100)],[(1,100)],[(0,1)],[(1,)])['lower']==2

@pytest.mark.parametrize('proof',[(F(1,2),),(-1,2),(1,1),(0.5,0.5)])
def test_forged_or_incomplete_distribution_rejected(proof):
    with pytest.raises(ValueError):
        min_envelope_margin_lower([(0,0)],[(0,1),(1,-1)],[(0,1)],[proof])

def test_scope_and_exactness_fail_closed():
    with pytest.raises(ValueError):affine_box_min((0,1),[(2,1)])
    with pytest.raises(ValueError):min_envelope_margin_lower([],[(0,)],[],[])
    with pytest.raises(ValueError):min_envelope_margin_lower([(0,1)],[(0,)],[(0,1)],[(1,)])
    with pytest.raises(ValueError):min_envelope_margin_lower([(0,)],[(0,)],[],[])
