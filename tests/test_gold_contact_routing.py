"""Independent coordinate properties of constructive routes, no engine calls."""
from fractions import Fraction as F
from itertools import permutations
import pytest
from scripts.gold_contact_routing import gold_route,gold_reachability_lower
from scripts.gold_two_frontier import gold_partial_interval,gold_two_counts
from scripts.shogi_direct_mode_bounds import GOLD,TOTAL


@pytest.mark.parametrize('n',[3,4,5,9])
def test_complete_one_blocker_worlds_have_gold_routes_without_bfs(n):
    longest=0
    for s,d,b in permutations(range(n*n),3):
        route=gold_route(s,d,b,n)
        assert route[0]==s and route[-1]==d and b not in route
        assert len(route)==len(set(route))
        for a,z in zip(route,route[1:]):
            assert 0<=z<n*n
            dx,dy=z%n-a%n,z//n-a//n
            assert (dx,dy) in GOLD and (-dx,-dy) in GOLD
        bound=max(2*(n-1),n+1)
        longest=max(longest,len(route)-1)
        assert len(route)-1<=bound
    assert longest==max(2*(n-1),n+1)


def test_reachability_improves_full_mass_lower_without_changing_upper():
    c=gold_two_counts()
    for law,m16 in (('geometric_half',F(1,2)**16),('linear_mixture',F(2,17*18))):
        oldlo,oldhi=gold_partial_interval(law)
        newlo=gold_reachability_lower(law)
        assert newlo-oldlo==F(c['remaining'],TOTAL)*m16>0
        assert newlo<oldhi
