"""Explicit none-contract extension for wholly nonpromotable native profiles."""
from dataclasses import replace
from scripts.shared_contact_prefix import SharedContactPrefix


class NonpromotableContactPrefix(SharedContactPrefix):
    def __init__(self,compiled,profiles,**kwargs):
        profiles=tuple(profiles)
        for p in profiles:
            meta=compiled.support.type_metadata.get(p.base)
            if meta is None or meta.is_promotable or p.base!=p.current or p.promoted:
                raise ValueError('all origins must be native nonpromotable')
        super().__init__(compiled,profiles,**kwargs)

    @staticmethod
    def _pattern(p,gs):
        if p.promotion_mode=='none':
            if p.explicit_promotion_type is not None:raise ValueError('none cannot have promotion target')
            p=replace(p,promotion_mode='inherit_compiled_masks')
        return SharedContactPrefix._pattern(p,gs)
