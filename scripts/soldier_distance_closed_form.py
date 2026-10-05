"""Monotone one-own-blocker contact counts; not official game legality."""
from collections import Counter

def _shape(width,height,river):
    if any(type(x) is not int for x in (width,height,river)) or width<2 or height<2 or not 1<=river<height:
        raise ValueError('integer rectangle and interior river required')

def pair_counts(width,height,river,source_rank,target_rank,file_gap):
    _shape(width,height,river)
    if any(type(x) is not int for x in (source_rank,target_rank,file_gap)) or not 0<=source_rank<height or not 0<=target_rank<height or not 0<=file_gap<width:
        raise ValueError('invalid rank/gap')
    s,t,k=source_rank,target_rank,file_gap
    if s==t and k==0:raise ValueError('distinct source/target required')
    total=width*height-2
    if t<s or (s<river and t<river and k>0):return {0:total}
    base=t-s+k;blocked=detours=0
    if s<river:
        if k==0 and t<=river:blocked=t-s-1
        elif k==0:
            blocked=river-s;detours=t-river-1
        else:
            blocked=river-s
            if t==river:blocked+=k-1
    elif t==s:blocked=k-1
    elif k==0:detours=t-s-1
    counts={base:total-blocked-detours}
    if blocked:counts[0]=blocked
    if detours:counts[base+2]=detours
    assert all(n>=0 for n in counts.values()) and sum(counts.values())==total
    return counts

def histogram(width,height,river):
    _shape(width,height,river)
    counts=Counter();strata=0
    for source in range(height):
        for target in range(height):
            for gap in range(width):
                if source==target and gap==0:continue
                multiplicity=width if gap==0 else 2*(width-gap)
                for tau,count in pair_counts(width,height,river,source,target,gap).items():
                    counts[tau]+=multiplicity*count
                strata+=1
    total=width*height*(width*height-1)*(width*height-2)
    assert sum(counts.values())==total
    return dict(histogram={t:n for t,n in sorted(counts.items()) if t and n},
                unreachable=counts[0],total=total,strata=strata)
