"""Independent small-grid path/count controls; no compiled game transitions."""
from collections import Counter,deque
from itertools import permutations
from fractions import Fraction as F


def counts(w,h):
    assert w>=2 and h>=2
    a=w*h;aligned=a*(w+h-2)
    third=F(a*((w-1)*(w-2)+(h-1)*(h-2)),3)
    assert third.denominator==1
    return {1:aligned*(a-2)-int(third),2:(a*(a-1)-aligned)*(a-2),3:int(third)}


def between(s,d,b):
    if s[0]==d[0]:return b[0]==s[0] and min(s[1],d[1])<b[1]<max(s[1],d[1])
    return s[1]==d[1]==b[1] and min(s[0],d[0])<b[0]<max(s[0],d[0])


def test_closed_counts_against_exhaustive_distinct_triple_partition():
    for w,h in ((2,2),(2,3),(3,3),(3,4)):
        squares=[(x,y) for x in range(w) for y in range(h)]
        classified=Counter()
        for s,d,b in permutations(squares,3):
            aligned=s[0]==d[0] or s[1]==d[1]
            classified[3 if aligned and between(s,d,b) else 1 if aligned else 2]+=1
        expected=counts(w,h)
        assert all(classified[t]==expected[t] for t in (1,2,3))
        assert sum(expected.values())==w*h*(w*h-1)*(w*h-2)


def shortest(start,target,blocker,*,n=3,allow_promotion=True):
    # Pure independent explicit ray model. Allowing promotion at ANY quiet
    # square is an even larger relaxation than the task's Shogi zone.
    queue=deque([(start,False,0)]);seen={(start,False)};candidate_checks=0
    while queue:
        (x,y),dragon,cost=queue.popleft()
        if cost>=3:continue
        ends=[]
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            xx,yy=x+dx,y+dy
            while 0<=xx<n and 0<=yy<n:
                candidate_checks+=1
                assert candidate_checks<=5000
                if (xx,yy)==blocker:break
                ends.append((xx,yy))
                if (xx,yy)==target:break
                xx+=dx;yy+=dy
        if dragon:
            for dx,dy in ((-1,-1),(-1,1),(1,-1),(1,1)):
                end=(x+dx,y+dy);candidate_checks+=1
                if 0<=end[0]<n and 0<=end[1]<n and end!=blocker:ends.append(end)
        for end in ends:
            if end==target:return cost+1
            for promoted in ({dragon,True} if allow_promotion else {dragon}):
                node=(end,promoted)
                if node not in seen:seen.add(node);queue.append((end,promoted,cost+1))
        assert len(seen)<=128
    return None


def test_independent_ray_paths_and_promotion_relaxation_preserve_sample_bounds():
    cases=[((0,0),(2,0),(1,0),3),((0,0),(0,2),(0,1),3),
           ((0,0),(2,2),(0,1),2),((0,0),(2,0),(1,1),1)]
    for s,d,b,truth in cases:
        assert shortest(s,d,b,allow_promotion=False)==truth
        assert shortest(s,d,b,allow_promotion=True)==truth


def test_nine_by_nine_population_mass_and_one_dimensional_exclusion():
    c=counts(9,9)
    assert c=={1:99360,2:409536,3:3024}
    total=sum(c.values())
    assert [F(c[t],total) for t in (1,2,3)]==[F(46,237),F(4,5),F(7,1185)]
    import pytest
    with pytest.raises(AssertionError):counts(1,9)
