"""Independent intermediate-pair/blocker controls and exact duration margins."""
from collections import Counter
from fractions import Fraction as F
from itertools import permutations
import pytest
from scripts.knight_contact_frontier import three_action_counts


def adjacent(s,d):
    return sorted((abs(s[0]-d[0]),abs(s[1]-d[1])))==[1,2]


def test_offset_routes_match_independent_coordinate_pair_intersections():
    for n in (3,4,5,8):
        squares=[(x,y) for x in range(n) for y in range(n)]
        neighbors={s:{q for q in squares if adjacent(s,q)} for s in squares}
        counts=Counter()
        for s,d in permutations(squares,2):
            if (sum(s)-sum(d))%2!=1 or adjacent(s,d):
                continue
            routes=[{u,v} for u in neighbors[s] for v in neighbors[d]
                    if adjacent(u,v)]
            counts['none' if not routes else str(len(set.intersection(*routes)))]+=1
        assert dict(counts)==three_action_counts(n)['pair_intersections']
    result=three_action_counts()
    assert result['pair_intersections']=={'0':1344,'1':96,'2':96,'none':176}
    assert result['exact_N3']==94944 and result['odd_unknown_ge5']==11200
    assert result['route_count']==7136 and result['offset_sequence_tests']==13376


def test_small_board_blocker_worlds_have_exact_three_step_count():
    for n in (3,4):
        squares=[(x,y) for x in range(n) for y in range(n)]
        neighbors={s:{q for q in squares if adjacent(s,q)} for s in squares}
        total=0
        for s,d,b in permutations(squares,3):
            if (sum(s)-sum(d))%2!=1 or adjacent(s,d):
                continue
            total+=any(adjacent(u,v) for u in neighbors[s]-{b}
                       for v in neighbors[d]-{b})
        assert total==three_action_counts(n)['exact_N3']


def test_full_mass_and_predeclared_duration_ranking_certificate():
    total=249984
    assert 20832+66472+94944+11200+56536==total
    m=lambda t:F(2,(t+1)*(t+2))
    nlo=(20832*m(1)+66472*m(2)+94944*m(3))/total
    nhi=(20832*m(1)+66472*m(2)+94944*m(3)+11200*m(5)+56536*m(4))/total
    bhi=(33936*m(1)+85824*m(2)+3008*m(3))/total
    r=(53760*m(1)+194432*m(2)+1792*m(3))/total
    assert nlo-bhi==F(6001,937440)>0 and r>nhi>nlo
    g=F(1,2)
    n=(20832*g+66472*g*g+94944*g**3)/total
    b=(33936*g+85824*g*g+3008*g**3)/total
    assert n-b==F(17,41664)>0
    # No uniform-discount order is inferred from these two hypotheses.
    g=F(1,100)
    blo=(33936*g+85824*g*g)/total
    nu=(20832*g+66472*g*g+94944*g**3+11200*g**5+56536*g**4)/total
    assert blo>nu


@pytest.mark.parametrize('n',[True,2,9,8.0])
def test_count_boundary_does_not_expand_to_unbounded_jobs(n):
    with pytest.raises(ValueError):
        three_action_counts(n)
