from fractions import Fraction as F
from scripts.compatible_contact import integrate_contact_intervals,discounted_contact_interval


def test_common_discount_lower_certificate_and_interior_extremum():
    for i in range(121):
        g=F(1,3)+F(i,360)
        gap=g-g**3
        assert gap-F(8,27)==(g-F(1,3))*(F(8,9)-g/3-g**2)
        assert F(8,9)-g/3-g**2>=0 and gap>=F(8,27)
    assert F(1,2)-F(1,2)**3>max(F(1,3)-F(1,3)**3,F(2,3)-F(2,3)**3)
    assert F(1,3)-F(2,3)**3==F(1,27) # independent box loses dependence


def test_signed_physical_obstruction_and_shared_parameter_cancellation():
    for g in (F(1,3),F(1,2),F(2,3)):
        rook=(g+g**3)/2;pawn=(g**3-g)/2
        assert pawn<0 and rook+pawn==g**3
        for a,b in ((1,1),(1,-1),(-2,3)):
            assert a*rook+b*pawn==F(a-b,2)*g+F(a+b,2)*g**3
    assert (F(1,2)+F(1,2)**3)/2==F(5,16)
    assert (F(1,2)**3-F(1,2))/2==-F(3,16)


def test_proven_frontier_tail_and_unsupported_mass_are_different():
    g=F(1,2)
    weights={'one':F(1,4),'two':F(1,4),'tail':F(1,4),'unreachable':F(1,4)}
    bounds={'one':(g,g),'two':(g**2,g**2),
            'tail':discounted_contact_interval(g,excluded_through=2),
            'unreachable':discounted_contact_interval(g,excluded_through=0,unreachable=True)}
    assert integrate_contact_intervals(weights,bounds)==(F(3,16),F(7,32))
    bounds['tail']=discounted_contact_interval(g,excluded_through=0)
    assert integrate_contact_intervals(weights,bounds)==(F(3,16),F(5,16))
    # A concrete compatible witness for the unresolved stratum improves lower mass.
    bounds['tail']=discounted_contact_interval(g,excluded_through=2,witness_length=4)
    assert integrate_contact_intervals(weights,bounds)==(F(13,64),F(7,32))


def test_common_unknown_cancels_only_under_explicit_identity():
    for shared in (F(0),F(1,3),F(1)):
        assert (F(2,3)+shared)-(F(1,3)+shared)==F(1,3)
    # Same0..1 marginal boxes alone allow different values, including reversal.
    assert (F(2,3)+0)-(F(1,3)+1)==-F(2,3)
