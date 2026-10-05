"""Scoped Western single-source aux projection, never an executable rule view."""
from dataclasses import replace
from scripts.shared_contact_prefix import SharedContactPrefix,Profile
FP='7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35'


class WesternPawnContactPrefix(SharedContactPrefix):
    def __init__(self,compiled,*,owner=0,checkpoint=lambda:None):
        if compiled.ruleset_fingerprint!=FP:raise ValueError('qualified Western rules required')
        patterns=[];geometry=dict(compiled.ir.geometry);self.discarded_ep=[];self.reduced_double=[]
        closure={'P','N','B','R','Q'}
        for p in compiled.ir.patterns:
            if not closure.intersection(p.type_ids):continue
            if any(e.kind=='clear_token' for e in p.effects):
                if p.type_ids!=('P',) or not p.slot_guards or tuple(e.kind for e in p.effects)!=('remove','move','clear_token'):
                    raise ValueError('unqualified auxiliary removal')
                self.discarded_ep.append(p.pattern_id);continue
            if any(e.kind=='set_token' for e in p.effects):
                if p.type_ids!=('P',) or tuple(e.kind for e in p.effects)!=('move','set_token') or len(p.guards)!=1:
                    raise ValueError('unqualified double effect')
                self.reduced_double.append(p.pattern_id)
                for gid in p.geometry_ids:
                    g=geometry[gid]
                    if g.kind!='ray' or g.direction!=(0,1) or g.min_steps!=2 or g.max_steps!=2:
                        raise ValueError('unexpected double geometry')
                    paths={side:{s:path for s,path in table.items() if s//8==(1 if side=='0' else 6)} for side,table in g.paths.items()}
                    geometry[gid]=replace(g,paths=paths)
                p=replace(p,guards=(),effects=p.effects[:1],promotion_mode='inherit_compiled_masks')
            if p.promotion_mode=='none':p=replace(p,promotion_mode='inherit_compiled_masks')
            # Actor-specific atoms must not leak grouped-current geometry.
            for current in closure.intersection(p.type_ids):
                gids=tuple(g for g in p.geometry_ids if geometry[g].atom_source is None or geometry[g].atom_source[0]==current)
                if gids:patterns.append(replace(p,type_ids=(current,),geometry_ids=gids))
        if len(self.discarded_ep)!=2 or len(self.reduced_double)!=1:raise ValueError('complete aux projection not established')
        view=replace(compiled,ir=replace(compiled.ir,patterns=tuple(patterns),geometry=geometry))
        super().__init__(view,(Profile('P','P'),),owner=owner,checkpoint=checkpoint)
        self.c=compiled
