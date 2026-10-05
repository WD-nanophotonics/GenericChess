from fractions import Fraction as F
import pytest
from scripts.shogi_complete_board_intervals import moment


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_zero_first_drop_failure_does_not_bound_later_guard_loss(law):
    virtual=(moment(law,2)+moment(law,4))/2
    guarded=moment(law,2)/2
    assert virtual-guarded==moment(law,4)/2>0
    eta=F(1,2)
    assert virtual-guarded<=eta*moment(law,2)


def test_deadline_mixture_requires_shared_second_moment():
    assert moment('linear_mixture',2)==F(1,6)
    assert moment('linear_mixture',2)>moment('linear_mixture',1)**2
    # A failed minimal length2 route attains eta*m2, falsifying eta*(E gamma)^2.
    eta=F(1,2)
    loss=eta*moment('linear_mixture',2)
    assert loss>eta*moment('linear_mixture',1)**2


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_legal_resampling_can_attain_both_error_signs(law):
    maximum=moment(law,2);masked=maximum/2;delta=F(1,2)
    assert maximum-masked==delta*maximum
    assert F(0)-masked==-delta*maximum
