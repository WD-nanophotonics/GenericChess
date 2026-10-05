"""Exact geometry mirror basis; predicates still evaluated on actual squares."""
from collections import defaultdict
from dataclasses import replace
from generic_chess.rules.ir import geometry_candidates
from scripts.shared_contact_prefix import SharedContactPrefix
from scripts.typed_shared_contact_prefix import actor_bound_view
from scripts.native_cube_contact_closure import NativeCubeKernel
from scripts.intrinsic_action_events import event_cubes_for_candidate
from scripts.rule_neutral_contact_constructor import ContactUnsupported

class MirroredNativeCubeKernel(NativeCubeKernel):
    def __init__(self,compiled,profiles,*,owner=0,checkpoint=lambda:None):
        if type(owner) is not int or owner not in (0,1):raise ValueError('owner0/1 required')
        self.c=compiled;self.owner=owner;self.check=checkpoint;self.shape=compiled.support.board_shape;self.area=self.shape.area
        self.profiles=tuple(profiles);self.closure=set(self.profiles)
        if not self.profiles or len(self.closure)!=len(self.profiles):raise ValueError('nonempty unique profiles')
        for p in self.profiles:
            meta=compiled.support.type_metadata.get(p.base)
            if meta is None or meta.is_promotable or meta.promotion_target_ids or p.promoted or p.base!=p.current:raise ContactUnsupported('native nonpromotable required')
            SharedContactPrefix._profile(self,p)
        currents={p.current for p in self.profiles};patterns=[];geometries={};basis={};self.stats=dict(checked_patterns=0,canonical_candidates=0,expanded_geometry_candidates=0,raw_pattern_candidates=0,reflection_path_checks=0)
        view=actor_bound_view(compiled)
        for p in view.ir.patterns:
            if not currents.intersection(p.type_ids):continue
            gs=[view.ir.geometry[gid] for gid in p.geometry_ids]
            if all(g.kind=='drop' for g in gs):continue
            self._pattern(p,gs);self.stats['checked_patterns']+=1
            if self.stats['checked_patterns']>128:raise ValueError('pattern cap')
            for g in gs:
                if not g.owner_relative:raise ContactUnsupported('mirror basis requires relative geometry')
                delta=g.offset if g.kind=='leap' else g.direction
                if delta is None or delta==(0,0):raise ContactUnsupported('ordinary nonzero geometry required')
                key=(g.kind,g.owner_relative,abs(delta[0]),abs(delta[1]),g.min_steps,g.max_steps)
                geometries[g.geometry_id]=(g,key);basis.setdefault(key,g);patterns.append((p,g.geometry_id))
        if any(not any(t in p.type_ids and p.target.kind==kind for p,_ in patterns) for t in currents for kind in ('target_empty','target_enemy')):raise ContactUnsupported('whole native grammar required')
        def flags(g):
            df,dr=g.offset if g.kind=='leap' else g.direction;sign=1 if owner==0 else -1
            return df*sign<0,dr*sign<0
        def reflect(square,axes):
            f,r=square%self.shape.width,square//self.shape.width
            return (self.shape.width-1-f if axes[0] else f)+self.shape.width*(self.shape.height-1-r if axes[1] else r)
        cache={}
        for key,g in basis.items():
            axes=flags(g);paths={source:tuple(reflect(q,axes) for q in g.paths.get(str(owner),{}).get(reflect(source,axes),())) for source in range(self.area)}
            canonical=replace(g,paths={str(owner):paths})
            for source in range(self.area):
                self.check();rows=geometry_candidates(canonical,str(owner),source);self.stats['canonical_candidates']+=len(rows)
                if self.stats['canonical_candidates']>5000:raise ValueError('canonical basis cap')
                cache[key,source]=rows
        derived={}
        for gid,(g,key) in geometries.items():
            axes=flags(g)
            for source in range(self.area):
                self.check();basis_source=reflect(source,axes)
                rows=tuple((reflect(d,axes),tuple(reflect(q,axes) for q in path)) for d,path in cache[key,basis_source])
                ordered=tuple(g.paths.get(str(owner),{}).get(source,()))
                expected=((ordered[0],()),) if g.kind=='leap' and ordered else () if g.kind=='leap' else tuple((ordered[i],ordered[:i]) for i in range(max(0,(g.min_steps or 1)-1),len(ordered)))
                if rows!=expected:raise ContactUnsupported('compiled path not a mirror of selected basis')
                self.stats['reflection_path_checks']+=1;self.stats['expanded_geometry_candidates']+=len(rows);derived[gid,source]=rows
        self.stats['canonical_geometries']=len(basis);self.quiet={};self.capture={}
        for profile in self.profiles:
            for source in range(self.area):
                quiet=defaultdict(set);capture=defaultdict(set)
                for p,gid in patterns:
                    if profile.current not in p.type_ids:continue
                    for dest,path in derived[gid,source]:
                        self.check();self.stats['raw_pattern_candidates']+=1
                        events=event_cubes_for_candidate(compiled,p,type_id=profile.current,owner=owner,source=source,target=dest,path=path)
                        for (_,_,_,_,state,removals,result),cubes in events.items():
                            if result!=profile.current:raise ContactUnsupported('native result changed unexpectedly')
                            if state=='empty':quiet[dest,profile].update(cubes)
                            else:capture[dest].update(cubes)
                if len(quiet)>128:raise ValueError('physical variant cap')
                self.quiet[profile,source]=dict(quiet);self.capture[profile,source]=dict(capture)
