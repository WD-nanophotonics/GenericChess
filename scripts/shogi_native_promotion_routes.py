"""Constructive S/N/B promotion support, not game search or a full graph."""
from scripts.gold_contact_routing import gold_route


def _knight_walk(x,r,k,direction):
    route=[]
    for _ in range(k):
        if not 0<=x+direction<9:direction=-direction
        x+=direction;r+=2;route.append(r*9+x)
    return route


def promotion_prefix(mode,source,blocker,owner=0):
    if mode not in ('S','N','B') or owner not in (0,1) or source==blocker or any(type(i) is not int or not 0<=i<81 for i in (source,blocker)):
        raise ValueError('native S/N/B, distinct9x9 source/blocker and owner0/1 required')
    if owner==1:
        p=promotion_prefix(mode,80-source,80-blocker,0)
        return None if p is None else [80-x for x in p]
    x,r=source%9,source//9;route=[source]
    if mode=='N':
        if r>=7:return None
        k=max(1,(7-r)//2)
        if x in (0,8):
            u=x+(1 if x==0 else -1);first=(r+2)*9+u
            candidates=[[first]+_knight_walk(u,r+2,k-1,d) for d in (-1,1)]
        else:candidates=[_knight_walk(x,r,k,d) for d in (-1,1)]
        return next((route+p for p in candidates if blocker not in p),None)
    if r>=6:
        atoms=((0,1),(-1,1),(1,1),(-1,-1),(1,-1)) if mode=='S' else ((-1,1),(1,1),(-1,-1),(1,-1))
        for dx,dy in atoms:
            a,b=x+dx,r+dy
            if 0<=a<9 and 0<=b<9 and b*9+a!=blocker:return route+[b*9+a]
        return None
    detours=0
    while r<6:
        candidates=((-1,1),(1,1),(0,1)) if mode=='S' else ((-1,1),(1,1))
        choices=[(x+dx,r+dy) for dx,dy in candidates
                 if 0<=x+dx<9 and (r+dy)*9+x+dx!=blocker]
        if choices:
            x,r=choices[0];route.append(r*9+x);continue
        if mode!='B' or r==0:return None
        if x not in (0,8) or detours:raise AssertionError('one blocker creates at most one edge detour')
        direction=1 if x==0 else -1
        route.extend(((r-1)*9+x+direction,r*9+x+2*direction));x+=2*direction
        detours+=1
    return route


def native_contact_route(mode,source,target,blocker,owner=0):
    if target in (source,blocker) or type(target) is not int or not 0<=target<81:
        raise ValueError('distinct ordinary target required')
    prefix=promotion_prefix(mode,source,blocker,owner)
    if prefix is None:return None
    if target in prefix[1:]:return prefix[:prefix.index(target)+1]
    return prefix+gold_route(prefix[-1],target,blocker)[1:]
