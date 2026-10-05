"""Exact aggregate/pointwise normalization identities, no new duration fitting."""
from fractions import Fraction as F
import pytest
from scripts.native_chess_contact_intervals import native_contact_intervals


def q(g):
    return (87696*g+162048*g*g+240*g**3)/249984


def r(g):
    return (53760*g+194432*g*g+1792*g**3)/249984


def test_tilted_measure_identity_and_noncommutation():
    values=(F(1,4),F(3,4))
    qs=[q(g) for g in values]; vs=[r(g)/q(g) for g in values]
    aggregate=sum(r(g) for g in values)/sum(qs)
    pointwise=sum(vs)/2
    mean_q=sum(qs)/2
    covariance=sum(a*b for a,b in zip(qs,vs))/2-mean_q*pointwise
    assert qs[1]>qs[0] and vs[1]>vs[0]
    assert aggregate-pointwise==covariance/mean_q>0
    threshold=(aggregate+pointwise)/2
    assert pointwise < threshold < aggregate
    assert aggregate==sum(a*b/sum(qs) for a,b in zip(qs,vs))


def test_zero_atom_boundary_keeps_aggregate_defined():
    assert q(F(0))==r(F(0))==0
    with pytest.raises(ZeroDivisionError):
        r(F(0))/q(F(0))
    aggregate=(r(F(0))+r(F(1,2)))/(q(F(0))+q(F(1,2)))
    assert aggregate==r(F(1,2))/q(F(1,2))


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_interface_divides_exact_aggregate_not_pointwise(law):
    moment=(lambda t:F(1,2)**t) if law=='geometric_half' else (lambda t:F(2,(t+1)*(t+2)))
    mean_q=(87696*moment(1)+162048*moment(2)+240*moment(3))/249984
    mean_r=(53760*moment(1)+194432*moment(2)+1792*moment(3))/249984
    bounds=native_contact_intervals(law)
    assert bounds['board','R']==(mean_r/mean_q,)*2
    assert bounds['board','Q']==(F(1),F(1))
