"""Independent small lattice/partition controls, not additional game samples."""
from collections import Counter,deque
from fractions import Fraction as F

GOLD=((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1))


def metric(start,target):
    dx=abs(target[0]-start[0]);dy=target[1]-start[1]
    return max(dx,dy) if dy>=0 else dx-dy


def bfs_gold(start,target,blocker=None):
    queue=deque([(start,0)]);seen={start}
    while queue:
        (x,y),distance=queue.popleft()
        if (x,y)==target:return distance
        for dx,dy in GOLD:
            next_=(x+dx,y+dy)
            if 0<=next_[0]<3 and 0<=next_[1]<3 and next_!=blocker and next_ not in seen:
                seen.add(next_);queue.append((next_,distance+1))
    return None


def test_gold_metric_against_all_three_by_three_lattice_pairs():
    squares=[(x,y) for x in range(3) for y in range(3)]
    for start in squares:
        for target in squares:assert bfs_gold(start,target)==metric(start,target)


def test_corner_backward_paths_can_avoid_the_declared_single_blocker():
    for start in ((0,1),(0,2)):
        for x in range(3):
            for y in range(3):
                target=(x,y)
                if target!=(1,0):assert bfs_gold(start,target,(1,0))==metric(start,target)
    # Different blocker geometry is not covered by the fixed-frame shortcut.
    assert bfs_gold((0,2),(0,0),(0,1))==4>metric((0,2),(0,0))


def targets():return [(x,y) for x in range(9) for y in range(9) if (x,y) not in ((0,6),(4,6))]


def rook_distance(d):
    x,y=d
    if x==0 or (y==6 and x<4):return 1
    if y==6:return 3
    return 2


def test_common_demand_partition_preserves_every_target_and_shared_denominator():
    demand=targets();assert len(set(demand))==79
    assert Counter(map(rook_distance,demand))=={1:11,2:64,3:4}
    dragon=lambda d:1 if abs(d[0])==abs(d[1]-6)==1 else rook_distance(d)
    assert Counter(map(dragon,demand))=={1:13,2:62,3:4}
    clear=lambda d:1 if d[0]==0 or d[1]==6 else 2
    assert Counter(map(clear,demand))=={1:15,2:64}
    for g in (F(1,3),F(1,2),F(2,3)):
        rm=sum(g**rook_distance(d) for d in demand)/79
        tm=sum(g**dragon(d) for d in demand)/79
        cm=sum(g**clear(d) for d in demand)/79
        assert tm-rm==F(2,79)*(g-g**2)
        assert cm-rm==F(4,79)*(g-g**3)


def test_lance_promotion_metric_partition_and_longest_task_distance():
    def lance(d):
        x,y=d
        if x==0 and y in (7,8):return 1
        return 1+min(metric((0,7),d),metric((0,8),d))
    counts=Counter(lance(d) for d in targets())
    assert [counts[t] for t in range(1,17)]==[2,2,4,5,6,6,8,9,9,7,6,5,4,3,2,1]
    assert sum(counts.values())==79 and lance((8,0))==16
    for d in targets():
        x,y=d
        expected=1 if x==0 and y in (7,8) else 1+x if y>=7 else 8+x-y
        assert lance(d)==expected


def test_advanced_pawn_knight_shared_demand_difference_telescopes():
    def lance(d):
        x,y=d
        return 1 if x==0 and y in (7,8) else 1+min(metric((0,7),d),metric((0,8),d))
    def pawn(d):return 2 if d==(0,8) else lance(d)
    def knight(d):return 1+abs(d[0]-1)+8-d[1]
    for g in (F(1,3),F(1,2),F(2,3)):
        l,p,n=(sum(g**f(d) for d in targets())/79 for f in (lance,pawn,knight))
        assert l-p==(g-g**2)/79
        assert n-p==(g**10-g**4)/79<0
    assert pawn((0,7))==1 and knight((0,7))==3


def test_ordinary_pawn_first_promotion_lower_bound_reverses_local_pair():
    target=(1,2)
    # First promotion at rank6/7/8 has cost6/7/8 plus its Gold continuation.
    alternatives=[rank+metric((0,rank),target) for rank in (6,7,8)]
    assert alternatives==[11,13,15]
    assert (1,2) in ((-1,2),(1,2)) # native Knight's one-action displacement
