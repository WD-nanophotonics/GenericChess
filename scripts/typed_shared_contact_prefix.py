"""Actor-bound shared-prefix views; original executable compiled object retained."""
from dataclasses import replace
from scripts.shared_contact_prefix import SharedContactPrefix
from scripts.nonpromotable_contact_prefix import NonpromotableContactPrefix
def actor_bound_view(compiled):
    patterns=[]
    for pattern in compiled.ir.patterns:
        for current in pattern.type_ids:
            ids=tuple(gid for gid in pattern.geometry_ids
                if compiled.ir.geometry[gid].atom_source is None or compiled.ir.geometry[gid].atom_source[0]==current)
            if ids:patterns.append(replace(pattern,type_ids=(current,),geometry_ids=ids))
    return replace(compiled,ir=replace(compiled.ir,patterns=tuple(patterns)))
class TypedSharedContactPrefix(SharedContactPrefix):
    def __init__(self,compiled,profiles,**kwargs):
        super().__init__(actor_bound_view(compiled),profiles,**kwargs)
        self.c=compiled
class TypedNonpromotableContactPrefix(NonpromotableContactPrefix):
    def __init__(self,compiled,profiles,**kwargs):
        super().__init__(actor_bound_view(compiled),profiles,**kwargs)
        self.c=compiled
