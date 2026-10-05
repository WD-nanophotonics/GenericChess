"""Native typed occupancy-cube first contact; target remains present."""
from collections import Counter,deque
from fractions import Fraction as F
from scripts.typed_sparse_contact_cubes import TypedSparseContactCubes
from scripts.sparse_contact_cubes import SparseContactCubes,blocker_mask
from scripts.rule_neutral_contact_constructor import ContactUnsupported,deadline_moment

class NativeCubeKernel(TypedSparseContactCubes):
    def __init__(self,compiled,profiles,**kwargs):
        profiles=tuple(profiles)
        for p in profiles:
            meta=compiled.support.type_metadata.get(p.base)
            if meta is None or meta.is_promotable or meta.promotion_target_ids or p.promoted or p.base!=p.current:
                raise ContactUnsupported('native nonpromotable origin/current required')
        super().__init__(compiled,profiles,**kwargs)

    @staticmethod
    def _pattern(p,gs):
        try:
            SparseContactCubes._pattern(p,gs)
            for guard in p.guards:
                if guard.type_ref.kind!='any' or guard.owner!='any' or guard.promoted!='any':
                    raise ContactUnsupported('typed/base source guard lacks generic profile qualification')
        except ValueError as error:
            raise ContactUnsupported(p.pattern_id+': '+str(error)) from error

def cube_contact_census(kernel,*,world_observer=lambda *args:None):
    profiles=tuple(sorted(kernel.closure,key=lambda p:(p.base,p.current,p.promoted)))
    indices={p:i for i,p in enumerate(profiles)};area=kernel.area;size=area*len(profiles)
    hist={p:Counter() for p in kernel.profiles};zeros={p:0 for p in hist};worlds=0
    for target in range(area):
        kernel.check();edges=[];captures=[]
        for p in profiles:
            for source in range(area):
                if source==target:continue
                parent=indices[p]*area+source
                for (dest,nxt),cubes in kernel.quiet[p,source].items():
                    if dest==target:continue
                    mask=0
                    for cube in cubes:mask|=blocker_mask(cube,area=area,source=source,target=dest,enemy=target)
                    if mask:edges.append((parent,indices[nxt]*area+dest,mask))
                mask=0
                for cube in kernel.capture[p,source].get(target,()):mask|=blocker_mask(cube,area=area,source=source,target=target,enemy=target)
                if mask:captures.append((parent,mask))
        for blocker in range(area):
            if blocker==target:continue
            kernel.check();bit=1<<blocker;reverse=[[] for _ in range(size)]
            for parent,child,mask in edges:
                if mask&bit:reverse[child].append(parent)
            distance=[0]*size;queue=deque()
            for parent,mask in captures:
                if mask&bit:distance[parent]=1;queue.append(parent)
            while queue:
                child=queue.popleft()
                for parent in reverse[child]:
                    if distance[parent]==0:distance[parent]=distance[child]+1;queue.append(parent)
            for p in kernel.profiles:
                for source in range(area):
                    if source in (target,blocker):continue
                    t=distance[indices[p]*area+source];worlds+=1
                    if t:hist[p][t]+=1
                    else:zeros[p]+=1
                    world_observer(target,blocker,p,source,t)
    total=area*(area-1)*(area-2);rows={}
    for p in kernel.profiles:
        if sum(hist[p].values())+zeros[p]!=total:raise ValueError('incomplete full-population cube census')
        rows[p]=dict(histogram=dict(sorted(hist[p].items())),unreachable=zeros[p],total=total,
          means={law:sum(F(n)*deadline_moment(law,t) for t,n in hist[p].items())/total for law in ('geometric_half','linear_mixture')})
    return dict(rows=rows,worlds=worlds,algorithm='target_aware_occupancy_cubes')
