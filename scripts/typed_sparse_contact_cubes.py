"""Actor-bound projection view for sparse intrinsic preprocessing only."""
from dataclasses import replace
from scripts.sparse_contact_cubes import SparseContactCubes


class TypedSparseContactCubes(SparseContactCubes):
    def __init__(self,compiled,profiles,**kwargs):
        patterns=[]
        for pattern in compiled.ir.patterns:
            for current in pattern.type_ids:
                ids=tuple(gid for gid in pattern.geometry_ids
                          if compiled.ir.geometry[gid].atom_source is None
                          or compiled.ir.geometry[gid].atom_source[0]==current)
                if ids:patterns.append(replace(pattern,type_ids=(current,),geometry_ids=ids))
        view=replace(compiled,ir=replace(compiled.ir,patterns=tuple(patterns)))
        super().__init__(view,profiles,**kwargs)
        # Never expose the non-executable projection as the original rules.
        self.c=compiled
