"""Independent geometry/mass arithmetic, not compiled drop/game validation."""
from fractions import Fraction as F


def test_all_four_corner_promotion_routes_avoid_the_declared_blocker():
    cases=[((0,0),(1,1),(7,6),(1,0)),((8,0),(7,1),(1,6),(7,0)),
           ((0,8),(1,7),(0,7),(1,8)),((8,8),(7,7),(8,7),(7,8))]
    for d,b,q,r in cases:
        dx=r[0]-q[0];dy=r[1]-q[1]
        assert abs(dx)==abs(dy)>0 and q[1]>=6
        sx=1 if dx>0 else -1;sy=1 if dy>0 else -1
        path=[(q[0]+k*sx,q[1]+k*sy) for k in range(1,abs(dx)+1)]
        assert b not in path and d not in path and path[-1]==r
        assert abs(r[0]-d[0])+abs(r[1]-d[1])==1


def test_exception_mass_preserves_nominal_source_population():
    total=81*80*79;exceptions=4*79
    assert F(exceptions,total)==F(1,1620)
    for g in (F(1,3),F(1,2),F(2,3)):
        bishop=F(1619,1620)*g**2+F(1,1620)*g**3
        assert g**2-bishop==g**2*(1-g)/1620>0
