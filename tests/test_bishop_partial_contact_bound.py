from fractions import Fraction as F


def test_diagonal_population_and_trapped_source_mass():
    lines=[*range(1,9),9,*range(8,0,-1)]*2
    aligned=sum(k*(k-1) for k in lines)
    blocked=sum(F(k*(k-1)*(k-2),3) for k in lines)
    assert aligned==816 and blocked==1344
    direct=aligned*79-blocked
    trapped=4*79
    assert direct==63120 and trapped==316
    assert direct+trapped+448484==81*80*79


def test_shared_law_rook_lower_gap_identity_without_point_selection():
    for i in range(1,100):
        g=F(i,100)
        rook=(99360*g+409536*g**2+3024*g**3)/511920
        bishop_upper=(63120*g+448484*g**2)/511920
        certificate=(316*g+g*(1-g)*(35924-3024*g))/511920
        assert rook-bishop_upper==certificate>=g/1620>0
