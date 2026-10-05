"""Independent jump-intersection proof controls, no engine or goal queries."""
from collections import Counter
from fractions import Fraction as F
from itertools import permutations


def displacement_counts(n):
    steps=[(a,b) for a in (-2,-1,1,2) for b in (-2,-1,1,2)
           if abs(a)+abs(b)==3]
    counts=Counter()
    for dx in range(1-n,n):
        for dy in range(1-n,n):
            if (dx+dy)%2 or (dx,dy)==(0,0):
                continue
            offsets=[v for v in steps if (v[0]-dx,v[1]-dy) in steps]
            for x in range(max(0,-dx),min(n,n-dx)):
                for y in range(max(0,-dy),min(n,n-dy)):
                    counts[sum(0<=x+a<n and 0<=y+b<n for a,b in offsets)]+=1
    return counts


def test_offset_counts_match_coordinate_pair_neighbor_sets():
    def adjacent(s,d):
        return sorted((abs(s[0]-d[0]),abs(s[1]-d[1])))==[1,2]
    for n in (3,4,5,8):
        squares=[(x,y) for x in range(n) for y in range(n)]
        neighbors={s:{q for q in squares if adjacent(s,q)} for s in squares}
        independent=Counter(len(neighbors[s]&neighbors[d])
                            for s,d in permutations(squares,2)
                            if (sum(s)-sum(d))%2==0)
        assert displacement_counts(n)==independent
    assert displacement_counts(8)=={0:904,1:488,2:592}


def test_complete_mass_and_refined_discount_bounds():
    total=249984;direct=20832;two=66472;odd_unknown=106144;even_unknown=56536
    assert direct+two+odd_unknown+even_unknown==total
    assert two==488*61+592*62
    for g in (F(1,100),F(1,2),F(99,100)):
        old=(direct*g+123008*g*g+odd_unknown*g**3)/total
        upper=(direct*g+two*g*g+odd_unknown*g**3+even_unknown*g**4)/total
        lower=(direct*g+two*g*g+odd_unknown*g**61+even_unknown*g**62)/total
        assert 0<lower<upper
        assert old-upper==even_unknown*g*g*(1-g*g)/total>0
    m=lambda t:F(2,(t+1)*(t+2))
    nlo=(direct*m(1)+two*m(2)+odd_unknown*m(61)+even_unknown*m(62))/total
    nhi=(direct*m(1)+two*m(2)+odd_unknown*m(3)+even_unknown*m(4))/total
    blo=(33936*m(1)+85824*m(2))/total;bhi=blo+3008*m(3)/total
    assert nlo<blo<bhi<nhi  # Tightening still does not certify B/N order.
