"""Qualified current/origin promotion closure for target-present virtual cubes."""
from scripts.typed_sparse_contact_cubes import TypedSparseContactCubes
from scripts.sparse_contact_cubes import SparseContactCubes
from scripts.rule_neutral_contact_constructor import ContactUnsupported
from scripts.shared_contact_prefix import Profile,SharedContactPrefix

class PromotableContactCubes(TypedSparseContactCubes):
    def __init__(self,compiled,profiles,**kwargs):
        profiles=tuple(profiles);self._metadata=compiled.support.type_metadata
        closure=set(profiles)
        for p in profiles:
            # Validate with the original compiled semantics before projecting actor IR.
            self.c=compiled;SharedContactPrefix._profile(self,p)
            if not p.promoted:closure.update(Profile(p.base,t,True) for t in self._metadata[p.base].promotion_target_ids)
        for p in closure:
            SharedContactPrefix._profile(self,p)
            if p.promoted and (self._metadata[p.current].is_promotable or self._metadata[p.current].promotion_target_ids):
                raise ContactUnsupported('promoted-current promotion metadata needs physical-profile qualification')
        try:super().__init__(compiled,profiles,**kwargs)
        except ValueError as error:raise ContactUnsupported(str(error)) from error
        self.closure=closure
        if {p for p,_ in self.quiet}!=closure or {p for p,_ in self.capture}!=closure:
            raise ContactUnsupported('whole quiet/current profile closure not preserved')

    def _pattern(self,pattern,geometries):
        SparseContactCubes._pattern(pattern,geometries)
        for guard in pattern.guards:
            if guard.type_ref.kind!='any' or guard.owner!='any' or guard.promoted!='any':
                raise ContactUnsupported('physical origin/owner/promoted source guard unsupported')
        if pattern.promotion_mode=='none' and any(self._metadata[t].is_promotable or self._metadata[t].promotion_target_ids for t in pattern.type_ids):
            raise ContactUnsupported('NONE promotion on promotable current requires separate qualification')
