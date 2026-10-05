"""Exact reverse quiet-to-capture distances when quiet/capture masks differ."""
from collections import Counter,deque

def target_aware_slabs(kernel,initial):
    profiles=tuple(sorted(kernel.closure,key=lambda p:(p.base,p.current,p.promoted)))
    index={p:i for i,p in enumerate(profiles)};area=kernel.area;offset=index[initial]*area
    for blocker in range(area):
        kernel.check();quiet=[];capture=[];hist=Counter();unreachable=0
        for profile in profiles:
            for source in range(area):
                parent=index[profile]*area+source
                if source==blocker:continue
                for destination,path,nxt in kernel.quiet[profile,source]:
                    if destination!=blocker and not path&(1<<blocker):
                        quiet.append((parent,index[nxt]*area+destination,source,destination,path))
                capture.append((parent,source,{target for target,masks in kernel.capture[profile,source].items()
                    if target!=blocker and any(not mask&(1<<blocker) for mask in masks)}))
        for target in range(area):
            if target==blocker:continue
            kernel.check();size=len(profiles)*area;reverse=[[] for _ in range(size)]
            for parent,child,source,destination,path in quiet:
                if source!=target and destination!=target and not path&(1<<target):reverse[child].append(parent)
            distances=[-1]*size;queue=deque()
            for parent,source,targets in capture:
                if source!=target and target in targets:distances[parent]=1;queue.append(parent)
            while queue:
                child=queue.popleft()
                for parent in reverse[child]:
                    if distances[parent]<0:distances[parent]=distances[child]+1;queue.append(parent)
            for source in range(area):
                if source in (blocker,target):continue
                distance=distances[offset+source]
                if distance<0:unreachable+=1
                else:hist[distance]+=1
        yield blocker,dict(histogram=dict(sorted(hist.items())),unreachable=unreachable)
