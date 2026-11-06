"""Experimental exact Boolean projection for a strict plain-Leaper subdomain.

Caller supplied only: no default/backend activation. Core retains all history,
clock, terminal and action semantics; complete action generation is unchanged.
"""
from __future__ import annotations
from ...core.search_runtime import _plain_leaper_hash_patterns
from ...core.semantic_executor import semantic_engine_for


class PlainLeaperBooleans:
    def __init__(self, compiled):
        self.compiled=compiled
        self.engine=semantic_engine_for(compiled)
        if self.engine is None:
            raise ValueError('requires executable semantic Core')
        self.metrics=dict(check_calls=0,availability_calls=0,position_builds=0,cache_hits=0,fallbacks=0)
        self._position=None;self._data=None
        self.quiet={};self.capture={}
        self.anchor_types=frozenset(t for t,m in compiled.support.type_metadata.items() if m.is_anchor)
        self.admitted=compiled.board_shape.area<=64 and _plain_leaper_hash_patterns(compiled) is not None
        if not self.admitted:return
        for pattern in compiled.ir.patterns:
            geometries=[compiled.ir.geometry[g] for g in pattern.geometry_ids]
            if all(g.kind=='drop' for g in geometries):continue
            if len(pattern.invariants)!=1 or pattern.invariants[0].kind!='own_anchor_safe':
                self.admitted=False;return
            table=self.quiet if pattern.target.kind=='target_empty' else self.capture
            for tid in pattern.type_ids:
                for g in geometries:
                    if g.atom_source is not None and g.atom_source[0]!=tid:continue
                    for owner in (0,1):
                        for source,path in g.paths.get(str(owner),{}).items():
                            if path:
                                key=tid,owner,source
                                table[key]=table.get(key,0)|(1<<path[0])

    def clear(self):
        self._position=None;self._data=None

    @staticmethod
    def _poll(checkpoint):
        if checkpoint is not None:checkpoint()

    def _prepare(self,position,checkpoint):
        self._poll(checkpoint);self.engine._ensure_match(position)
        if position is self._position:
            self.metrics['cache_hits']+=1
            return self._data
        if (not self.admitted or position.aux_state
                or any(hand.counts for hand in position.hands)
                or position.board_shape!=self.compiled.board_shape):return None
        occupied=[0,0];pieces=[[],[]];anchors=[[],[]]
        for source,piece in enumerate(position.board):
            self._poll(checkpoint)
            if piece is None:continue
            if (piece.owner not in (0,1) or piece.promoted
                    or piece.current_type_id!=piece.base_type_id
                    or piece.current_type_id not in self.compiled.support.type_metadata):return None
            occupied[piece.owner]|=1<<source
            pieces[piece.owner].append((source,piece))
            if piece.current_type_id in self.anchor_types:anchors[piece.owner].append(source)
        if any(len(squares)!=1 for squares in anchors):return None
        unions=[0,0];without=[{},{}]
        for owner in (0,1):
            masks=[self.capture.get((p.current_type_id,owner,s),0) for s,p in pieces[owner]]
            prefix=[0]
            for mask in masks:prefix.append(prefix[-1]|mask)
            suffix=[0]*(len(masks)+1)
            for i in range(len(masks)-1,-1,-1):suffix[i]=suffix[i+1]|masks[i]
            unions[owner]=prefix[-1]
            # Remove a SOURCE by union of all other sources, never XOR.
            without[owner]={source:prefix[i]|suffix[i+1] for i,(source,_) in enumerate(pieces[owner])}
        self._poll(checkpoint)
        data=occupied,pieces,[a[0] for a in anchors],unions,without
        self._position=position;self._data=data
        self.metrics['position_builds']+=1
        return data

    def in_check(self,position,side,checkpoint=None):
        self.metrics['check_calls']+=1
        if type(side) is not int or side not in (0,1):raise ValueError('side must be0or1')
        data=self._prepare(position,checkpoint)
        if data is None:
            self.metrics['fallbacks']+=1
            return self.engine.in_check(position,side,checkpoint=checkpoint)
        _,_,anchors,unions,_=data
        return bool(unions[1-side]&(1<<anchors[side]))

    def has_legal_action(self,position,checkpoint=None):
        self.metrics['availability_calls']+=1
        data=self._prepare(position,checkpoint)
        if data is None:
            self.metrics['fallbacks']+=1
            return self.engine.has_legal_action(position,checkpoint=checkpoint)
        occupied,pieces,anchors,unions,without=data
        side=position.side_to_move;enemy=1-side
        all_occupied=occupied[0]|occupied[1];king_bit=1<<anchors[side]
        checked=bool(unions[enemy]&king_bit)
        for source,piece in pieces[side]:
            self._poll(checkpoint)
            key=piece.current_type_id,side,source
            quiet=self.quiet.get(key,0)&~all_occupied
            # The generic remove effect forbids capturing an anchor, even
            # though that anchor still contributes geometric attack coverage.
            captures=self.capture.get(key,0)&occupied[enemy]&~(1<<anchors[enemy])
            candidates=quiet|captures
            if not candidates:continue
            if source==anchors[side]:
                if candidates&~unions[enemy]:return True
                # Capturing a source can remove its own coverage; retain all
                # overlapping other-source attacks at the landing square.
                for target,remaining in without[enemy].items():
                    if captures&(1<<target) and not remaining&(1<<target):return True
            elif not checked:
                return True
            else:
                # With no blockers/effects, a non-anchor can only evade by
                # capturing the last source attacking the unchanged anchor.
                for target,remaining in without[enemy].items():
                    if captures&(1<<target) and not remaining&king_bit:return True
        return False
