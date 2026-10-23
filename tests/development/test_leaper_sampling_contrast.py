"""All binary label completions as an independent transport-bound oracle."""
from fractions import Fraction as F
from itertools import product
import pytest
from scripts.leaper_sampling_contrast import contrast,normalize


def test_shared_unknown_labels_cancel_under_identical_normalized_mu():
    out=contrast(dict(a=None,b=None),dict(a=1,b=3),dict(a=2,b=6))
    assert out['second_minus_first_bounds']==['0','0']
    assert out['total_variation']=='0'and out['unknown_nonzero_coefficients']==0
    assert all(q['queries']==0 for q in out['unit_independent_label_query_bounds'])


def test_bounds_equal_all_completions_for_small_finite_support():
    for la,lb in product(((1,2,3),(3,0,1),(0,0,1)),repeat=2):
        ids=('a','b','c');a=dict(zip(ids,la));b=dict(zip(ids,lb))
        for pattern in ((None,)*3,(True,None,False),(None,False,None)):
            labels=dict(zip(ids,pattern));out=contrast(labels,a,b)
            first,second=normalize(a),normalize(b)
            possible=[]
            for bits in product((False,True),repeat=3):
                if any(y is not None and y!=v for y,v in zip(pattern,bits)):continue
                possible.append(sum((second.get(h,F(0))-first.get(h,F(0)))*v for h,v in zip(ids,bits)))
            assert list(map(F,out['second_minus_first_bounds']))==[min(possible),max(possible)]
            assert max(abs(x)for x in possible)<=F(out['total_variation'])


def test_one_unknown_query_has_known_residual_width():
    out=contrast(dict(a=None,b=True),dict(a=1),dict(b=1))
    assert out['second_minus_first_bounds']==['0','1']
    assert all(q['queries']==1 and F(q['residual_width'])==0 for q in out['unit_independent_label_query_bounds'])


@pytest.mark.parametrize('first,second,labels',[
    (dict(a=-1),dict(a=1),dict(a=None)),
    (dict(a=True),dict(a=1),dict(a=None)),
    (dict(a=0),dict(a=1),dict(a=None)),
    (dict(a=1),dict(b=1),dict(a=None)),
    (dict(a=1),dict(a=1),dict(a=0))])
def test_invalid_law_or_truth_is_not_a_default_zero(first,second,labels):
    with pytest.raises(ValueError):contrast(labels,first,second)
