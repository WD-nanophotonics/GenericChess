"""Occupancy cubes plus exact physical inherited/NONE profile dispatch."""
from dataclasses import replace
from generic_chess.rules.ir import geometry_candidates
from scripts.sparse_contact_cubes import SparseContactCubes
from scripts.shared_contact_prefix import SharedContactPrefix,Profile
from scripts.intrinsic_action_events import event_cubes_for_candidate
from scripts.rule_neutral_contact_constructor import ContactUnsupported

class PhysicalProfileEventCubes(SparseContactCubes):
    def __init__(self,compiled,profiles,*,owner=0,checkpoint=lambda:None):
        if type(owner) is not int or owner not in (0,1):raise ContactUnsupported('owner scope')
        self.c=compiled;self.owner=owner;self.check=checkpoint;self.shape=compiled.support.board_shape;self.area=self.shape.area;self.profiles=tuple(profiles)
        if not self.profiles or len(set(self.profiles))!=len(self.profiles):raise ContactUnsupported('distinct profiles')
        closure=set(self.profiles)
        for p in tuple(closure):
            SharedContactPrefix._profile(self,p)
            if not p.promoted:closure.update(Profile(p.base,t,True) for t in compiled.support.type_metadata[p.base].promotion_target_ids)
        for p in closure:SharedContactPrefix._profile(self,p)
        self.closure=closure;currents={p.current for p in closure};patterns=[];geometries={}
        self.stats=dict(checked_patterns=0,canonical_candidates=0,raw_pattern_candidates=0)
        for pattern in compiled.ir.patterns:
            for current in currents.intersection(pattern.type_ids):
                gs=[compiled.ir.geometry[g] for g in pattern.geometry_ids if compiled.ir.geometry[g].atom_source is None or compiled.ir.geometry[g].atom_source[0]==current]
                if not gs or all(g.kind=='drop' for g in gs):continue
                p=replace(pattern,type_ids=(current,))
                try:SparseContactCubes._pattern(p,gs)
                except ValueError as error:raise ContactUnsupported(str(error)) from error
                if any(g.type_ref.kind!='any' or g.owner!='any' or g.promoted!='any' for g in p.guards):raise ContactUnsupported('physical source guard not qualified')
                self.stats['checked_patterns']+=1
                if self.stats['checked_patterns']>128:raise ContactUnsupported('pattern cap')
                for g in gs:
                    key=(g.kind,g.owner_relative,g.offset,g.direction,g.min_steps,g.max_steps)
                    if key in geometries and geometries[key].paths!=g.paths:raise ContactUnsupported('same geometry different paths')
                    geometries.setdefault(key,g);patterns.append((p,key))
        if any(not any(t in p.type_ids and p.target.kind==kind for p,_ in patterns) for t in currents for kind in ('target_empty','target_enemy')):raise ContactUnsupported('missing whole grammar')
        cache={}
        for key,g in geometries.items():
            for s in range(self.area):
                self.check();rows=geometry_candidates(g,str(owner),s);self.stats['canonical_candidates']+=len(rows)
                if self.stats['canonical_candidates']>5000:raise ContactUnsupported('candidate cap')
                cache[key,s]=rows
        self.stats['canonical_geometries']=len(geometries);self.quiet={};self.capture={}
        for profile in closure:
            for s in range(self.area):
                quiet={};capture={}
                for p,key in patterns:
                    if profile.current not in p.type_ids:continue
                    for d,path in cache[key,s]:
                        self.check();self.stats['raw_pattern_candidates']+=1
                        results=(profile,) if p.promotion_mode=='none' else SharedContactPrefix._variants(self,profile,s,d)
                        if not results:continue
                        events=event_cubes_for_candidate(compiled,replace(p,promotion_mode='none'),type_id=profile.current,owner=owner,source=s,target=d,path=path)
                        for (_,_,_,_,state,_,_),cubes in events.items():
                            for result in results:
                                if result not in closure:raise ContactUnsupported('profile closure')
                                if state=='empty':quiet.setdefault((d,result),set()).update(cubes)
                                else:capture.setdefault(d,set()).update(cubes)
                if len(quiet)>128:raise ContactUnsupported('quiet variant cap')
                self.quiet[profile,s]=quiet;self.capture[profile,s]=capture
