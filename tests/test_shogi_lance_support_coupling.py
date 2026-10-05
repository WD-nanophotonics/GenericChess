"""Independent ray/support census and correlated-gap controls, no game labels."""
from fractions import Fraction as F
from itertools import permutations
from scripts.shogi_pawn_promotion_support import classify_pawn_world
from scripts.shogi_direct_mode_bounds import TOTAL,partial_raw_interval


def lance_case(s,d,b,owner):
    if owner==1:s,d,b=80-s,80-d,80-b
    x,r=s%9,s//9
    if r==8:return 'zero'
    if d%9==x and d//9>r:
        segment={y*9+x for y in range(r+1,d//9)}
        if b not in segment:return 'direct'
    # Test the actual ray to earliest promotion square, not Pawn classification.
    z=max(r+1,6)
    ray={y*9+x for y in range(r+1,z+1)}
    return 'zero' if b in ray else 'promotion'


def test_complete_native_support_equal_but_direct_mass_different():
    for owner in (0,1):
        zero=direct=extra=0
        for s,d,b in permutations(range(81),3):
            l=lance_case(s,d,b,owner);p,t=classify_pawn_world(s,d,b,owner)
            assert (l=='zero')==(p=='zero')
            zero+=l=='zero';direct+=l=='direct'
            extra+=l=='direct' and (p,t)!=('prefix',1)
        assert (zero,direct,extra)==(72918,24840,19152)


def test_lance_duration_bounds_and_gap_retained_without_independent_box_order():
    for law,m in (('geometric_half',lambda t:F(1,2)**t),
                  ('linear_mixture',lambda t:F(2,(t+1)*(t+2)))):
        lo=(24840*m(1)+414162*m(17))/TOTAL
        hi=(24840*m(1)+414162*m(2))/TOTAL
        oldlo,oldhi=partial_raw_interval('L',law)
        assert oldlo<lo<hi<oldhi
        gap=F(19152,TOTAL)*(m(1)-m(2))
        assert gap==(F(133,14220) if law=='geometric_half' else F(133,21330))
