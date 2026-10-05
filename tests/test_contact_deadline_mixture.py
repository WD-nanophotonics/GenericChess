"""Exact deadline moments/interval arithmetic, not a new deployment observation."""
from fractions import Fraction as F


def moment(t):
    return F(2,(t+1)*(t+2))


def test_deadline_tail_mass_and_mean_telescoping():
    for cutoff in (1,2,10,100):
        pmf=sum(F(4,(h+1)*(h+2)*(h+3)) for h in range(cutoff))
        assert pmf+moment(cutoff)==1
        prefix=sum(moment(t) for t in range(1,cutoff+1))
        assert prefix==1-F(2,cutoff+2)
    assert moment(1)==F(1,3) and moment(2)==F(1,6)
    assert 1/moment(1)==3  # E[H | H>=1], not2 from the fixed-gamma alternative.
    # Uniform-gamma has survival1/(t+1): its harmonic mean diverges, unlike
    # this density2(1-gamma) model. Equal finite means don't imply equal tails.
    assert moment(2)!=F(1,2)**2


def test_held_next_moment_is_not_product_of_parameter_means():
    assert moment(2)!=moment(1)**2
    for t in (1,2,3,16,61):
        assert moment(t+1)/moment(t)==F(t+1,t+3)
    assert moment(2)/moment(1)==F(1,2)
    assert moment(4)/moment(3)==F(2,3)


def test_native_chess_frontiers_integrate_full_mass_without_midpoint_choice():
    total=249984;m=moment
    r=(53760*m(1)+194432*m(2)+1792*m(3))/total
    q=(87696*m(1)+162048*m(2)+240*m(3))/total
    b=(33936*m(1)/total,(33936*m(1)+88832*m(2))/total)
    n=((20832*m(1)+106144*m(61)+123008*m(62))/total,
       (20832*m(1)+123008*m(2)+106144*m(3))/total)
    p=((6076*m(1)+167090*m(10))/total,(6076*m(1)+198772*m(2))/total)
    assert q>r>max(b[1],n[1],p[1])>0
    assert b[0]<n[1] and n[0]<b[1]
    assert b[0]<p[1] and p[0]<b[1]
    assert q-r==(33936*(m(1)-m(2))+1552*(m(2)-m(3)))/total
