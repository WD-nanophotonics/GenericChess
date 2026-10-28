"""Conservative finite-board EMPTY geometry exposure, never rule equivalence.

Ray blockage is intentionally forgotten: Ray(1,0,max=2) and two Leaps can have
identical projections but different actual moves. A collision means potential
geometric exposure; absence never proves semantic independence/holdout.
"""
from scripts.leaper_motion_signature import motion_family_signature

def empty_geometry_signature(rule,n=8):
    if n!=8:raise ValueError('this prospective registry is fixed to board8')
    pieces=[]
    for p in rule['piece_types']:
        offsets=set()
        for a in p['movement_atoms']:
            kind=a['kind']
            if kind=='leap':
                x,y=a['offset']
                if max(abs(x),abs(y))<n:offsets.add((x,y))
            elif kind=='ray':
                x,y=a['direction'];span=max(abs(x),abs(y))
                if not span:raise ValueError('zero ray direction')
                maximum=(n-1)//span;declared=a.get('max_steps')
                if declared is not None:maximum=min(maximum,declared)
                offsets.update((x*j,y*j) for j in range(1,maximum+1))
            else:raise ValueError('unknown movement metadata kind')
        pieces.append({'is_anchor':p['is_anchor'],'movement_atoms':[{'kind':'leap','offset':o} for o in sorted(offsets)]})
    return motion_family_signature({'piece_types':pieces})
