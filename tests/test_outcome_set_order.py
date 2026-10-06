import itertools
import pytest
from scripts.outcome_set_order import set_order


def test_quantifiers_and_correlated_losses():
    a={'x':(1,1)};b={'a':(1,0),'b':(0,1)}
    assert set_order(a,b)['weak_order_proved']
    assert not set_order(b,a)['weak_order_proved']
    # An unattainable coordinate minimum falsely claims a reverse certificate.
    assert set_order({'fake':(0,0)},b)['unmatched'] == ['fake']


def test_linear_sufficiency_is_not_necessity_and_never_strict_by_default():
    a={'x':(1,1)};b={'a':(2,0),'b':(0,2)}
    assert not set_order(a,b)['weak_order_proved']
    for w in itertools.product(range(5),repeat=2):
        assert min(sum(wi*vi for wi,vi in zip(w,x)) for x in a.values()) >= min(sum(wi*vi for wi,vi in zip(w,y)) for y in b.values())
    assert not set_order(a,a)['strict_improvement_proved']


def test_finite_cube_relation_equivalent_to_all_isotone_boolean_utilities():
    vectors=tuple(itertools.product((0,1),repeat=2))
    sets=[{str(i):v for i,v in enumerate(vectors) if mask>>i&1} for mask in range(1,16)]
    utilities=[]
    for values in itertools.product((0,1),repeat=4):
        if all(not all(a<=b for a,b in zip(x,y)) or values[i]<=values[j]
               for i,x in enumerate(vectors) for j,y in enumerate(vectors)):
            utilities.append(dict(zip(vectors,values)))
    for a,b in itertools.product(sets,repeat=2):
        oracle=all(min(u[x] for x in a.values()) >= min(u[y] for y in b.values()) for u in utilities)
        assert set_order(a,b)['weak_order_proved'] == oracle


@pytest.mark.parametrize('a,b',[({}, {'x':(0,)}),({'x':()}, {'y':()}),({'x':(True,)},{'y':(1,)}),({'x':(1,2)},{'y':(1,)})])
def test_invalid_or_missing_outcomes_fail(a,b):
    with pytest.raises(ValueError):set_order(a,b)
