"""Coordinate census cross-checks analytical necessary conditions, not game search."""
from fractions import Fraction as F


def opposite(s, d):
    return (sum(s) - sum(d)) % 2 == 1


def near(s, d):
    return abs(abs(s[0]-d[0])-abs(s[1]-d[1])) == 1


def low(s, d, owner):
    return s[1] <= 5 and d[1] <= 4 if owner == 0 else s[1] >= 3 and d[1] >= 4


def test_displacement_census_against_independent_coordinate_pairs():
    squares = [(x,y) for x in range(9) for y in range(9)]
    far = [(s,d) for s in squares for d in squares if opposite(s,d) and not near(s,d)]
    formula = sum((9-abs(x))*(9-abs(y)) for x in range(-8,9)
                  for y in range(-8,9) if (x+y)%2 and abs(abs(x)-abs(y)) != 1)
    assert len(far) == formula == 1648
    for owner in (0,1):
        near_low = [(s,d) for s in squares for d in squares
                    if opposite(s,d) and near(s,d) and low(s,d,owner)]
        assert len(near_low) == 679
        # Reflection changes ownership, not the classified mass.
        assert all(low((8-s[0],8-s[1]),(8-d[0],8-d[1]),1-owner)
                   for s,d in near_low)


def test_corner_trap_intersections_are_disjoint_and_counted_once():
    squares = [(x,y) for x in range(9) for y in range(9)]
    for owner in (0,1):
        counts = [0,0,0]
        for s in ((0,0),(0,8),(8,0),(8,8)):
            b = (1 if s[0] == 0 else 7, 1 if s[1] == 0 else 7)
            for d in squares:
                if d in (s,b):
                    continue
                aligned = abs(s[0]-d[0]) == abs(s[1]-d[1])
                far = opposite(s,d) and not near(s,d)
                near_low = opposite(s,d) and near(s,d) and low(s,d,owner)
                assert sum((aligned,far,near_low)) <= 1
                for i, member in enumerate((aligned,far,near_low)):
                    counts[i] += member
        assert counts == [28,96,18]
        assert sum(counts) == 142


def test_partial_frontier_mass_and_upper_improvement():
    direct, unreachable = 63120, 316
    ge3 = 1344 + 79*(1648+679) - 142
    ge2 = 511920-direct-unreachable-ge3
    assert (ge2,ge3) == (263449,185035)
    for i in range(1,100):
        g=F(i,100)
        lower=F(direct,511920)*g
        old=(direct*g+448484*g**2)/511920
        new=(direct*g+ge2*g**2+ge3*g**3)/511920
        assert lower < new < old
        assert old-new == F(ge3,511920)*g**2*(1-g)
        rook=(99360*g+409536*g**2+3024*g**3)/511920
        assert rook-new > F(1,1620)*g > 0
