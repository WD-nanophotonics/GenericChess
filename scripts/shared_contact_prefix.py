"""Research-only qualified simple board grammar and exact one-blocker prefix.

Compiled paths and promotion masks are authoritative; no Core or model calls.
Royal safety/full-game administration are the declared virtual-task omissions.
"""
from dataclasses import dataclass
from generic_chess.core.coordinates import index_to_square
from generic_chess.rules.ir import geometry_candidates


@dataclass(frozen=True)
class Profile:
    base: str
    current: str
    promoted: bool = False


class SharedContactPrefix:
    def __init__(self, compiled, profiles, *, owner=0, checkpoint=lambda:None):
        if type(owner) is not int or owner not in (0,1):
            raise ValueError('owner0/1 required')
        self.c=compiled;self.owner=owner;self.check=checkpoint
        self.shape=compiled.support.board_shape;self.area=self.shape.area
        self.profiles=tuple(profiles)
        if not self.profiles or len(set(self.profiles))!=len(self.profiles):
            raise ValueError('nonempty distinct explicit profiles required')
        closure=set(self.profiles)
        for p in tuple(closure):
            self._profile(p)
            if not p.promoted:
                closure.update(Profile(p.base,t,True) for t in compiled.support.type_metadata[p.base].promotion_target_ids)
        for p in closure:self._profile(p)
        self.closure=closure
        currents={p.current for p in closure};geometries={};patterns=[]
        self.stats=dict(checked_patterns=0,geometry_candidates=0,source_geometry_tables=0,
                        raw_pattern_candidates=0,max_quiet_variants=0)
        for p in compiled.ir.patterns:
            if not currents.intersection(p.type_ids):continue
            gs=[compiled.ir.geometry[g] for g in p.geometry_ids]
            if all(g.kind=='drop' for g in gs):continue
            self.check();self.stats['checked_patterns']+=1
            if self.stats['checked_patterns']>128:raise ValueError('128 pattern cap')
            self._pattern(p,gs)
            for g in gs:
                key=(g.kind,g.owner_relative,g.offset,g.direction,g.min_steps,g.max_steps)
                if key in geometries and geometries[key].paths!=g.paths:
                    raise ValueError('same geometry key has different compiled paths')
                geometries.setdefault(key,g)
                patterns.append((p,key))
        if any(not any(t in p.type_ids and p.target.kind==kind for p,_ in patterns)
               for t in currents for kind in ('target_empty','target_enemy')):
            raise ValueError('missing complete simple board grammar')
        cache={}
        for key,g in geometries.items():
            for s in range(self.area):
                self.check();self.stats['source_geometry_tables']+=1
                rows=geometry_candidates(g,str(owner),s)
                self.stats['geometry_candidates']+=len(rows)
                if self.stats['geometry_candidates']>5000:raise ValueError('5000 canonical candidate cap')
                cache[key,s]=tuple((d,sum(1<<x for x in path)) for d,path in rows)
        self.stats['canonical_geometries']=len(geometries)
        physical={t:{kind:[set() for _ in range(self.area)] for kind in ('target_empty','target_enemy')} for t in currents}
        for p,key in patterns:
            for s in range(self.area):
                self.stats['raw_pattern_candidates']+=len(cache[key,s])
                for t in currents.intersection(p.type_ids):
                    physical[t][p.target.kind][s].update(cache[key,s])
        self.quiet={};self.capture={}
        for p in closure:
            for s in range(self.area):
                self.check();quiet=set();capture={}
                for u,mask in physical[p.current]['target_empty'][s]:
                    quiet.update((u,mask,v) for v in self._variants(p,s,u))
                if len(quiet)>128:raise ValueError('128 quiet physical variant cap')
                self.stats['max_quiet_variants']=max(self.stats['max_quiet_variants'],len(quiet))
                for d,mask in physical[p.current]['target_enemy'][s]:
                    if self._variants(p,s,d):capture.setdefault(d,set()).add(mask)
                self.quiet[p,s]=tuple(quiet)
                self.capture[p,s]={d:tuple(masks) for d,masks in capture.items()}

    def _profile(self,p):
        meta=self.c.support.type_metadata.get(p.base)
        if meta is None or meta.is_anchor or p.current not in self.c.support.type_metadata:
            raise ValueError('ordinary known origin/current required')
        if (p.promoted and p.current not in meta.promotion_target_ids) or (not p.promoted and p.base!=p.current):
            raise ValueError('invalid source promotion/origin relationship')

    @staticmethod
    def _pattern(p,gs):
        if (p.target.kind not in ('target_empty','target_enemy') or p.guards or p.slot_guards
                or p.square_zone_guards or p.postconditions or p.promotion_mode!='inherit_compiled_masks'):
            raise ValueError('unsupported state/history/promotion pattern')
        if any(i.kind!='own_anchor_safe' for i in p.invariants):raise ValueError('unsupported dynamic invariant')
        capture=p.target.kind=='target_enemy'
        if tuple(e.kind for e in p.effects)!=(('remove','move') if capture else ('move',)):
            raise ValueError('unsupported compound physical effects')
        move=p.effects[-1]
        if (move.piece_owner!='self' or move.from_ref.kind!='source' or move.to_ref.kind!='target'
                or move.piece_type_ref is not None or move.count!=1):
            raise ValueError('unsupported source move')
        if capture:
            e=p.effects[0]
            if e.square_ref.kind!='target' or e.piece_owner!='opponent' or e.disposition not in ('capture_to_hand','remove_from_game') or e.count!=1:
                raise ValueError('unsupported target removal')
        for g in gs:
            if g.kind not in ('leap','ray') or not g.owner_relative:
                raise ValueError('unsupported geometry')
            if tuple(x.kind for x in p.path)!=(('path_clear',) if g.kind=='ray' else ()):
                raise ValueError('unsupported occupancy path')
            if any(x.owner_filter!='any' for x in p.path):raise ValueError('unsupported path owner restriction')

    def _variants(self,p,s,d):
        if p.promoted:return (p,)
        meta=self.c.support.type_metadata[p.base]
        if not meta.is_promotable:return (p,)
        a,b=index_to_square(s,self.shape),index_to_square(d,self.shape)
        if (a,b) not in self.c.support.promotion_allowed[p.base][self.owner]:return (p,)
        alive=tuple(Profile(p.base,t,True) for t in meta.promotion_target_ids
                    if self.c.support.empty_mobility[t][self.owner][d])
        return alive if b in self.c.support.promotion_forced[p.base][self.owner] else (p,)+alive

    def pair_success(self,p,s,d):
        if p not in self.profiles or s==d or not 0<=s<self.area or not 0<=d<self.area:
            raise ValueError('admitted profile and distinct source/target required')
        universe=((1<<self.area)-1)&~((1<<s)|(1<<d))
        first=0
        for mask in self.capture[p,s].get(d,()):first|=universe&~mask
        remaining=universe&~first;second=0
        if remaining:
            for u,mask,v in self.quiet[p,s]:
                if u==d or mask&(1<<d):continue
                for tail in self.capture[v,u].get(d,()):
                    second|=remaining&~((1<<u)|mask|tail)
        return first,second

    def counts(self):
        total=self.area*(self.area-1)*(self.area-2);result={}
        for p in self.profiles:
            first=second=0
            for s in range(self.area):
                self.check()
                for d in range(self.area):
                    if s==d:continue
                    a,b=self.pair_success(p,s,d);first+=a.bit_count();second+=b.bit_count()
            result[p]=dict(direct=first,second=second,remaining=total-first-second,total=total)
        return result
