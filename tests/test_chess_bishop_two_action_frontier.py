"""Independent diagonal geometry controls; no engine paths or source labels."""
from fractions import Fraction as F
from itertools import permutations


def frontier(n):
    one = two = none = count = pairs = 0
    width = lambda *o: max(0, n - max(o) + min(o))
    for dx in range(1-n, n):
        for dy in range(1-n, n):
            if (dx+dy)%2 or abs(dx)==abs(dy):
                continue
            a,b=(dx+dy)//2,(dx-dy)//2
            c1=width(0,dx,a)*width(0,dy,a)
            c2=width(0,dx,b)*width(0,dy,-b)
            c12=width(0,dx,a,b)*width(0,dy,a,-b)
            single=c1+c2-2*c12
            population=(n-abs(dx))*(n-abs(dy))
            one+=single;two+=c12;none+=population-single-c12;pairs+=population
            count+=single*(n*n-2-(max(abs(dx),abs(dy))-1))+c12*(n*n-2)
    return pairs,one,two,none,count


def diagonal(s,d,b):
    dx,dy=d[0]-s[0],d[1]-s[1]
    if s==d or abs(dx)!=abs(dy):
        return False
    ux=(dx>0)-(dx<0);uy=(dy>0)-(dy<0)
    return all((s[0]+i*ux,s[1]+i*uy)!=b for i in range(1,abs(dx)+1))


def test_rectangle_counts_against_independent_pair_intersections():
    for n in (3,4,5,6,8):
        squares=[(x,y) for x in range(n) for y in range(n)]
        bins=[0,0,0]
        for s,d in permutations(squares,2):
            if (sum(s)-sum(d))%2 or abs(s[0]-d[0])==abs(s[1]-d[1]):
                continue
            intersections=[q for q in squares if q not in (s,d)
                           and abs(q[0]-s[0])==abs(q[1]-s[1])
                           and abs(q[0]-d[0])==abs(q[1]-d[1])]
            assert len(intersections)<=2
            bins[len(intersections)]+=1
        pairs,one,two,none,_=frontier(n)
        assert bins==[none,one,two] and sum(bins)==pairs
    assert frontier(8)==(1424,640,784,0,85824)


def test_small_board_triples_against_explicit_two_ray_existence():
    for n in (3,4,5):
        squares=[(x,y) for x in range(n) for y in range(n)]
        exact_two=0
        for s,d,b in permutations(squares,3):
            if diagonal(s,d,b):
                continue
            exact_two+=any(q not in (s,d,b) and diagonal(s,q,b)
                           and diagonal(q,d,b) for q in squares)
        assert exact_two==frontier(n)[-1]


def test_refined_full_mass_discount_and_mixture_bounds():
    total=249984;direct=33936;two=85824;zero=127216;unknown=3008
    assert direct+two+zero+unknown==total
    squares=[(x,y) for x in range(8) for y in range(8)]
    corners={(0,0):(1,1),(0,7):(1,6),(7,0):(6,1),(7,7):(6,6)}
    traps={(s,d,b) for s,b in corners.items() for d in squares
           if d not in (s,b) and (sum(s)-sum(d))%2==0}
    traps|={(s,d,b) for d,b in corners.items() for s in squares
            if s not in (d,b) and (sum(s)-sum(d))%2==0}
    assert len(traps)==240
    assert all(not diagonal(s,d,b) and not any(
        q not in (s,d,b) and diagonal(s,q,b) and diagonal(q,d,b)
        for q in squares) for s,d,b in traps)
    for g in (F(1,100),F(1,2),F(99,100)):
        lo=(direct*g+two*g*g)/total;hi=lo+unknown*g**3/total
        old=(direct*g+(two+unknown)*g*g)/total
        assert 0<lo<hi and old-hi==unknown*g*g*(1-g)/total
    m=lambda t:F(2,(t+1)*(t+2))
    lo=(direct*m(1)+two*m(2))/total;hi=lo+unknown*m(3)/total
    nlo=(20832*m(1)+106144*m(61)+123008*m(62))/total
    nhi=(20832*m(1)+123008*m(2)+106144*m(3))/total
    plo=(6076*m(1)+167090*m(10))/total
    phi=(6076*m(1)+198772*m(2))/total
    assert nlo<lo<hi<nhi and plo<lo<hi<phi
