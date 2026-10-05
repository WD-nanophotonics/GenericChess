"""Research-only typed IR admission and passive virtual contact construction."""
from dataclasses import dataclass,replace
from collections import Counter
from fractions import Fraction as F
from scripts.shared_contact_prefix import SharedContactPrefix,Profile
from scripts.typed_shared_contact_prefix import actor_bound_view
from scripts.full_contact_distances import qualify_target_free,full_distance_slabs
from scripts.target_aware_contact_distances import target_aware_slabs

class ContactUnsupported(ValueError):
    pass

class TypedSimpleContactKernel(SharedContactPrefix):
    def __init__(self,compiled,profiles,**kwargs):
        profiles=tuple(profiles);closure=set(profiles)
        for p in profiles:
            meta=compiled.support.type_metadata.get(p.base)
            if meta is None:raise ContactUnsupported('unknown origin profile')
            if not p.promoted:closure.update(Profile(p.base,t,True) for t in meta.promotion_target_ids)
        self.admission_profiles=closure
        super().__init__(actor_bound_view(compiled),profiles,**kwargs)
        self.c=compiled

    def _pattern(self,p,gs):
        try:
            if p.promotion_mode=='none':
                if p.explicit_promotion_type is not None:raise ContactUnsupported('none with explicit promotion target')
                affected=(q for q in self.admission_profiles if q.current in p.type_ids)
                if any(not q.promoted and self.c.support.type_metadata[q.base].is_promotable for q in affected):
                    raise ContactUnsupported('none-contract on an unpromoted promotable origin')
                p=replace(p,promotion_mode='inherit_compiled_masks')
            if not p.path and all(g.kind=='ray' and g.min_steps==g.max_steps==1
                 and all(len(path)<=1 for table in g.paths.values() for path in table.values()) for g in gs):
                gs=[replace(g,kind='leap') for g in gs]
            SharedContactPrefix._pattern(p,gs)
        except ValueError as error:
            raise ContactUnsupported(p.pattern_id+': '+str(error)) from error

@dataclass
class ContactConstruction:
    kernel: TypedSimpleContactKernel
    algorithm: str
    first_hit_qualification: str

    def census(self):
        hist={p:Counter() for p in self.kernel.profiles};zeros={p:0 for p in hist}
        if self.algorithm=='target_free':
            for _,slab in full_distance_slabs(self.kernel):
                for p,row in slab.items():hist[p].update(row['histogram']);zeros[p]+=row['unreachable']
        else:
            for p in self.kernel.profiles:
                for _,row in target_aware_slabs(self.kernel,p):hist[p].update(row['histogram']);zeros[p]+=row['unreachable']
        total=self.kernel.area*(self.kernel.area-1)*(self.kernel.area-2)
        rows={}
        for p in hist:
            if sum(hist[p].values())+zeros[p]!=total:raise ValueError('complete population mass missing')
            rows[p]=dict(histogram=dict(sorted(hist[p].items())),unreachable=zeros[p],total=total,
                means={law:sum(F(n)*deadline_moment(law,t) for t,n in hist[p].items())/total
                       for law in ('geometric_half','linear_mixture')})
        return rows

def deadline_moment(law,time):
    if type(time) is not int or time<1:raise ValueError('positive finite first-hit time required')
    if law=='geometric_half':return F(1,2)**time
    if law=='linear_mixture':return F(2,(time+1)*(time+2))
    raise ValueError('explicit declared duration required')

def construct_contact(compiled,profiles,*,owner=0,checkpoint=lambda:None):
    kernel=TypedSimpleContactKernel(compiled,profiles,owner=owner,checkpoint=checkpoint)
    try:qualify_target_free(kernel)
    except ValueError as reason:
        return ContactConstruction(kernel,'target_aware',str(reason))
    return ContactConstruction(kernel,'target_free','typed admitted grammar, mask equivalence and capture-prefix closure')
