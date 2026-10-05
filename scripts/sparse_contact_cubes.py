"""Shared IR geometry plus exact single-blocker cube projection, research only."""
from generic_chess.rules.ir import geometry_candidates
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
from scripts.intrinsic_action_events import event_cubes_for_candidate
from scripts.audit_static_semantic_material_prior_v2 import _simple_source_guard_supported


def blocker_mask(cube,*,area,source,target,enemy):
    """Exact own-b worlds: source own, enemy enemy, quiet/capture target distinct."""
    out=((1<<area)-1)&~((1<<source)|(1<<enemy))
    for square,labels in cube:
        if not 0<=square<area:raise ValueError('cube square outside board')
        if square==source:
            if 'own' not in labels:return 0
        elif square==enemy:
            if 'enemy' not in labels:return 0
        elif 'empty' in labels:
            if 'own' not in labels:out&=~(1<<square)
        elif 'own' in labels:out&=1<<square
        else:return 0
    # A quiet landing square cannot already be the blocker or designated enemy.
    if target!=enemy:out&=~(1<<target)
    return out


class SparseContactCubes:
    def __init__(self,compiled,profiles,*,owner=0,checkpoint=lambda:None):
        if type(owner) is not int or owner not in (0,1):raise ValueError('owner0/1 required')
        self.c=compiled;self.owner=owner;self.check=checkpoint
        self.shape=compiled.support.board_shape;self.area=self.shape.area
        self.profiles=tuple(profiles)
        if not self.profiles or len(set(self.profiles))!=len(self.profiles):raise ValueError('distinct explicit profiles')
        closure=set(self.profiles)
        for p in tuple(closure):
            SharedContactPrefix._profile(self,p)
            if not p.promoted:closure.update(Profile(p.base,t,True) for t in compiled.support.type_metadata[p.base].promotion_target_ids)
        for p in closure:SharedContactPrefix._profile(self,p)
        currents={p.current for p in closure};patterns=[];geometries={}
        self.stats=dict(checked_patterns=0,canonical_candidates=0,raw_pattern_candidates=0)
        for p in compiled.ir.patterns:
            if not currents.intersection(p.type_ids):continue
            gs=[compiled.ir.geometry[g] for g in p.geometry_ids]
            if all(g.kind=='drop' for g in gs):continue
            self.check();self.stats['checked_patterns']+=1
            if self.stats['checked_patterns']>128:raise ValueError('128 pattern cap')
            self._pattern(p,gs)
            for g in gs:
                key=(g.kind,g.owner_relative,g.offset,g.direction,g.min_steps,g.max_steps)
                if key in geometries and geometries[key].paths!=g.paths:raise ValueError('same key/different paths')
                geometries.setdefault(key,g);patterns.append((p,key))
        if any(not any(t in p.type_ids and p.target.kind==kind for p,_ in patterns) for t in currents for kind in ('target_empty','target_enemy')):raise ValueError('missing whole board grammar')
        cache={}
        for key,g in geometries.items():
            for s in range(self.area):
                self.check();rows=geometry_candidates(g,str(owner),s)
                self.stats['canonical_candidates']+=len(rows)
                if self.stats['canonical_candidates']>5000:raise ValueError('5000 canonical candidate cap')
                cache[key,s]=rows
        self.stats['canonical_geometries']=len(geometries)
        self.quiet={};self.capture={}
        for profile in closure:
            for s in range(self.area):
                quiet={};capture={}
                for p,key in patterns:
                    if profile.current not in p.type_ids:continue
                    for d,path in cache[key,s]:
                        self.check();self.stats['raw_pattern_candidates']+=1
                        events=event_cubes_for_candidate(compiled,p,type_id=profile.current,owner=owner,source=s,target=d,path=path)
                        for (_,_,_,_,state,removals,result),cubes in events.items():
                            next_profile=profile if result==profile.current else Profile(profile.base,result,True)
                            if next_profile not in closure:raise ValueError('unqualified result/origin closure')
                            if state=='empty':quiet.setdefault((d,next_profile),set()).update(cubes)
                            else:capture.setdefault(d,set()).update(cubes)
                if len(quiet)>128:raise ValueError('128 quiet physical variants')
                self.quiet[profile,s]=quiet;self.capture[profile,s]=capture

    @staticmethod
    def _pattern(p,gs):
        if p.slot_guards or p.postconditions or p.promotion_mode not in ('none','inherit_compiled_masks'):raise ValueError('unsupported history/promotion grammar')
        if any(i.kind!='own_anchor_safe' for i in p.invariants):raise ValueError('unsupported invariant')
        if p.target.kind not in ('target_empty','target_enemy'):raise ValueError('unsupported target')
        capture=p.target.kind=='target_enemy'
        if tuple(e.kind for e in p.effects)!=(('remove','move') if capture else ('move',)):raise ValueError('unsupported compound/auxiliary effects')
        move=p.effects[-1]
        if move.from_ref.kind!='source' or move.to_ref.kind!='target' or move.piece_owner!='self' or move.piece_type_ref is not None or move.count!=1:raise ValueError('unsupported source move')
        if capture:
            removal=p.effects[0]
            if removal.square_ref.kind!='target' or removal.piece_owner!='opponent' or removal.count!=1:raise ValueError('unsupported target removal')
        if any(g.kind not in ('leap','ray') for g in gs):raise ValueError('unsupported geometry')
        if any(x.owner_filter!='any' or x.kind not in ('path_clear','path_count_eq') for x in p.path):raise ValueError('unsupported path predicate')
        if any(x.kind=='path_count_eq' and x.count not in (0,1) for x in p.path):raise ValueError('unsupported sparse path count')
        for guard in p.guards:
            if _simple_source_guard_supported(guard):continue
            refs=guard.spatial.refs
            if not (guard.aggregation=='count' and guard.owner=='any' and guard.type_ref.kind=='any'
                    and guard.promoted=='any' and guard.location=='board' and guard.spatial.kind=='exact'
                    and len(refs)==1 and guard.subject_ref==refs[0] and guard.comparison=='eq' and guard.value==0
                    and refs[0].kind in ('source','target','path_step','fixed','offset_from_source','offset_from_target')):
                raise ValueError('unsupported occupancy guard')
        if any(g.spatial.kind!='zone' or g.relation not in ('inside','outside') for g in p.square_zone_guards):raise ValueError('unsupported zone guard')

    def pair_success(self,p,s,d):
        if p not in self.profiles or s==d or not 0<=s<self.area or not 0<=d<self.area:raise ValueError('admitted profile/distinct pair required')
        universe=((1<<self.area)-1)&~((1<<s)|(1<<d));first=0;second=0
        for cube in self.capture[p,s].get(d,()):first|=blocker_mask(cube,area=self.area,source=s,target=d,enemy=d)
        for (u,q),cubes in self.quiet[p,s].items():
            if u==d:continue
            head=0;tail=0
            for cube in cubes:head|=blocker_mask(cube,area=self.area,source=s,target=u,enemy=d)
            if not head:continue
            for cube in self.capture[q,u].get(d,()):tail|=blocker_mask(cube,area=self.area,source=u,target=d,enemy=d)
            second|=head&tail&universe&~first
        return first,second
