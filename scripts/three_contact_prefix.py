"""Extend the pinned simple grammar by a finite three-action blocker union."""


def third_counts(kernel):
    out={}
    for p in kernel.profiles:
        first=second=third=0
        for s in range(kernel.area):
            kernel.check()
            for d in range(kernel.area):
                if s==d:continue
                a,b=kernel.pair_success(p,s,d)
                remaining=((1<<kernel.area)-1)&~((1<<s)|(1<<d)|a|b)
                exact=0
                for u,m1,p1 in kernel.quiet[p,s]:
                    if u==d or m1&(1<<d):continue
                    for v,m2,p2 in kernel.quiet[p1,u]:
                        if v==d or m2&(1<<d):continue
                        for m3 in kernel.capture[p2,v].get(d,()):
                            exact|=remaining&~((1<<u)|(1<<v)|m1|m2|m3)
                first+=a.bit_count();second+=b.bit_count();third+=exact.bit_count()
        total=kernel.area*(kernel.area-1)*(kernel.area-2)
        out[p]=dict(direct=first,second=second,third=third,
                    remaining=total-first-second-third,total=total)
    return out
