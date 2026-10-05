"""Vacuous-path extension for exact one-step ray metadata, task-only."""
from dataclasses import replace
from scripts.shared_contact_prefix import SharedContactPrefix
from scripts.western_pawn_contact_prefix import WesternPawnContactPrefix

class QualifiedWesternPawnPrefix(WesternPawnContactPrefix):
    @staticmethod
    def _pattern(p,gs):
        if not p.path and all(g.kind=='ray' and g.min_steps==g.max_steps==1
                             and all(len(path)<=1 for table in g.paths.values() for path in table.values()) for g in gs):
            # Validation view only: candidate targets/intermediate paths remain
            # the original compiled ray data used by the parent's cache.
            gs=[replace(g,kind='leap') for g in gs]
        return SharedContactPrefix._pattern(p,gs)
