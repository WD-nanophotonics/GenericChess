"""Independent Pawn geometry: first two actions and blocked promotion support."""
from fractions import Fraction as F
from itertools import permutations
from collections import Counter


def diagonal_capture(s,d):
    return d[1]-s[1]==1 and abs(d[0]-s[0])==1


def queen_capture(s,d,b):
    dx,dy=d[0]-s[0],d[1]-s[1]
    if s==d or not (dx==0 or dy==0 or abs(dx)==abs(dy)):
        return False
    steps=max(abs(dx),abs(dy));ux=(dx>0)-(dx<0);uy=(dy>0)-(dy<0)
    return all((s[0]+k*ux,s[1]+k*uy)!=b for k in range(1,steps+1))


def first_two(s,d,b,n):
    if s[1]==n-1:
        return False
    if diagonal_capture(s,d):
        return True
    q=(s[0],s[1]+1)
    if q not in (d,b):
        if q[1]==n-1:
            knight=sorted((abs(d[0]-q[0]),abs(d[1]-q[1])))==[1,2]
            if knight or queen_capture(q,d,b):
                return True
        elif diagonal_capture(q,d):
            return True
    if s[1]==1 and s[1]+2<n and q not in (d,b):
        q2=(s[0],s[1]+2)
        if q2 not in (d,b) and diagonal_capture(q2,d):
            return True
    return False


def test_eight_board_exact_two_action_partition_and_extra_zeros():
    n=8;squares=[(x,y) for x in range(n) for y in range(n)]
    direct=two=zero=extra=0
    for s,d,b in permutations(squares,3):
        direct+=diagonal_capture(s,d)
        two+=not diagonal_capture(s,d) and first_two(s,d,b,n)
        old_zero=(s[1]==7 or (d[0]==s[0] and d[1]>s[1]))
        new_zero=(not old_zero and b[0]==s[0] and b[1]>s[1]
                  and not (abs(d[0]-s[0])==1 and s[1]<d[1]<=b[1]))
        zero+=old_zero or new_zero;extra+=new_zero
        if old_zero or new_zero:
            assert not first_two(s,d,b,n)
    assert (direct,two,zero,extra)==(6076,16112,56952,11816)


def test_promotion_to_knight_is_not_silently_replaced_by_queen():
    # P(3,6)->(3,7)=N, then captures(5,6); Q cannot make that second move.
    s=(3,6);d=(5,6);b=(0,0);q=(3,7)
    assert not queen_capture(q,d,b) and first_two(s,d,b,8)
    # Old source vacates: promotion-Q may capture backward through it.
    assert first_two((3,6),(3,4),(0,0),8)
    # Initial double cannot jump over the blocker, nor end on the target.
    assert not first_two((3,1),(4,4),(3,2),8)
    assert not first_two((3,1),(3,3),(0,0),8)


def test_rank_stratification_preserves_direct_overlap_and_duration_order():
    total=249984;m=lambda t:F(2,(t+1)*(t+2))
    assert 7*24640==172480 and 7*770==5390 and 7*23870==167090
    pold=(6076*m(1)+167090*m(10))/total
    plo=(6076*m(1)+23870*sum(m(k+3) for k in range(1,8)))/total
    pup=(6076*m(1)+16112*m(2)+170844*m(3))/total
    blo=(33936*m(1)+85824*m(2))/total
    assert pold<plo==F(35,1152)<pup==F(5273,60480)<blo
    assert blo-pup==F(28657,1874880)
    g=F(1,2)
    p=(6076*g+16112*g*g+170844*g**3)/total
    b=(33936*g+85824*g*g)/total
    assert b-p==F(20005,499968)>0
    assert 6076+16112+170844+56952==total


def test_prefix_and_rank_support_overlap_by_independent_world_oracle():
    squares=[(x,y) for x in range(8) for y in range(8)]
    overlaps=Counter()
    for s,d,b in permutations(squares,3):
        if (s[1]<7 and d[0]!=s[0] and b[0]!=s[0]
                and not diagonal_capture(s,d) and first_two(s,d,b,8)):
            overlaps[7-s[1]]+=1
    assert overlaps=={1:6596,2:770,3:770,4:770,5:770,6:1540,7:770}
    assert sum(overlaps.values())==11986<16112
    for g in (F(1,100),F(1,2),F(99,100)):
        new=6076*g+16112*g*g+sum((23870-overlaps[k])*g**(k+3) for k in range(1,8))
        old=6076*g+23870*sum(g**(k+3) for k in range(1,8))
        prefix=6076*g+16112*g*g
        assert new>old and new>prefix
