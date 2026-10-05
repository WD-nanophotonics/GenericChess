"""Qualified target-free first-hit BFS on compiled simple virtual contact grammar."""
from collections import Counter

def qualify_target_free(kernel):
    for profile in kernel.closure:
        for source in range(kernel.area):
            quiet={(target,mask) for target,mask,_ in kernel.quiet[profile,source]}
            captures={(target,mask) for target,masks in kernel.capture[profile,source].items() for mask in masks}
            if quiet!=captures:raise ValueError('quiet/capture mask equivalence required')
            for target,mask in quiet:
                interior=mask
                while interior:
                    bit=interior&-interior;interior-=bit;mid=bit.bit_length()-1
                    if not any(d==mid and path&~mask==0 for d,path in captures):
                        raise ValueError('prefix-closed capture required')

def full_distance_slabs(kernel):
    """Yield blocker-complete histograms; all target mass includes dead sources."""
    qualify_target_free(kernel)
    profiles=tuple(sorted(kernel.closure,key=lambda p:(p.base,p.current,p.promoted)))
    index={p:i for i,p in enumerate(profiles)};area=kernel.area;mask=(1<<area)-1
    for blocker in range(area):
        kernel.check();adj=[]
        for profile in profiles:
            for source in range(area):
                edges=0
                if source!=blocker:
                    for target,path,next_profile in kernel.quiet[profile,source]:
                        if target!=blocker and not path&(1<<blocker):edges|=1<<(index[next_profile]*area+target)
                adj.append(edges)
        slab={p:Counter() for p in kernel.profiles};zeros={p:0 for p in kernel.profiles}
        for profile in kernel.profiles:
            kernel.check()
            for source in range(area):
                if source==blocker:continue
                frontier=1<<(index[profile]*area+source);visited=frontier
                seen_squares=(1<<source)|(1<<blocker);distance=0
                while frontier:
                    nxt=0
                    while frontier:
                        bit=frontier&-frontier;frontier-=bit;nxt|=adj[bit.bit_length()-1]
                    nxt&=~visited;visited|=nxt;distance+=1
                    squares=0
                    for i in range(len(profiles)):squares|=(nxt>>(i*area))&mask
                    newly=squares&~seen_squares
                    if newly:slab[profile][distance]+=newly.bit_count()
                    seen_squares|=squares;frontier=nxt
                zeros[profile]+=area-seen_squares.bit_count()
        yield blocker,{p:dict(histogram=dict(slab[p]),unreachable=zeros[p]) for p in kernel.profiles}
