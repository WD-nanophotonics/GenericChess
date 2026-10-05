"""Fixed three-jump coordinate proof, not a native engine or goal producer."""
from collections import Counter

STEPS=tuple((a,b) for a in (-2,-1,1,2) for b in (-2,-1,1,2)
            if abs(a)+abs(b)==3)


def three_action_counts(n=8):
    if type(n) is not int or not 3<=n<=8:
        raise ValueError('bounded board side3..8 required')
    inside=lambda p:0<=p[0]<n and 0<=p[1]<n
    bins=Counter();sequence_tests=routes=0
    for x in range(n):
        for y in range(n):
            s=(x,y);intersections={}
            for a in STEPS:
                u=(x+a[0],y+a[1])
                if not inside(u):
                    continue
                for b in STEPS:
                    v=(u[0]+b[0],u[1]+b[1])
                    if not inside(v) or v==s:
                        continue
                    for c in STEPS:
                        sequence_tests+=1
                        d=(v[0]+c[0],v[1]+c[1])
                        if not inside(d) or (d[0]-x,d[1]-y) in STEPS:
                            continue
                        routes+=1;intermediate={u,v}
                        intersections[d]=(intermediate if d not in intersections
                                          else intersections[d]&intermediate)
            for dx in range(n):
                for dy in range(n):
                    d=(dx,dy)
                    if (dx+dy-x-y)%2!=1 or (dx-x,dy-y) in STEPS:
                        continue
                    bins['none' if d not in intersections else str(len(intersections[d]))]+=1
    exact=sum((n*n-2-int(k))*v for k,v in bins.items() if k!='none')
    return dict(pair_intersections=dict(sorted(bins.items())),exact_N3=exact,
                odd_unknown_ge5=sum(bins.values())*(n*n-2)-exact,
                route_count=routes,offset_sequence_tests=sequence_tests)
