"""Research-only incrementally guarded ordinary-Leap Boolean provider.

No product defaults or transition replacement. Actual Core remains authority.
The predicted two-cell state is used ONLY after full physical Position equality;
otherwise existing Native/Core callbacks answer. Attack is queried through
already compiled reverse geometry and incrementally maintained type bitboards.
Availability returns fast True only for an EMPTY safe royal step; never fastFalse.
"""
from dataclasses import dataclass,replace
from contextlib import contextmanager
from unittest.mock import patch
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.actions import action_is_board,action_source_square,action_target_square,action_promotion_target_id
from generic_chess.core.coordinates import square_to_index
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry

@dataclass
class Snapshot:
    position:object
    boards:dict
    occupied:int
    anchors:tuple

class IncrementalRoyalProvider:
    def __init__(self,compiled,native=None):
        self.compiled=compiled;self.native=native;self.engine=semantic_engine_for(compiled);self.cache=None;self.undo=[];self.runtime=None
        self.metrics=dict(initial_builds=0,predictions=0,guard_hits=0,guard_misses=0,check_calls=0,check_fast=0,availability_calls=0,availability_certificates=0,fallback_checks=0,fallback_availability=0,pushes=0,pops=0,rollbacks=0)
        geometry=ordinary_leap_geometry(compiled);self.admitted=geometry is not None;self.forward={};self.reverse={};self.anchor_types=set()
        if not self.admitted:return
        self.anchor_types={t for t,p in compiled.types_by_id.items() if p.is_anchor}
        for (owner,tid,source),targets in geometry.items():
            mask=0
            for target in targets:
                mask|=1<<target;key=owner,tid,target;self.reverse[key]=self.reverse.get(key,0)|(1<<source)
            self.forward[owner,tid,source]=mask
        self.types=tuple(compiled.types_by_id)
    def _build(self,position):
        if not self.admitted or position.ruleset_fingerprint!=self.compiled.ruleset_fingerprint or position.board_shape!=self.compiled.board_shape or position.aux_state or any(h.counts for h in position.hands):return None
        boards={(o,t):0 for o in (0,1) for t in self.types};occupied=0;anchors=[[],[]]
        for i,p in enumerate(position.board):
            if p is None:continue
            if type(p.owner) is not int or p.owner not in (0,1) or p.current_type_id not in self.types or p.promoted or p.base_type_id!=p.current_type_id:return None
            boards[p.owner,p.current_type_id]|=1<<i;occupied|=1<<i
            if p.current_type_id in self.anchor_types:anchors[p.owner].append(i)
        if any(len(a)!=1 for a in anchors):return None
        self.metrics['initial_builds']+=1
        return Snapshot(position,boards,occupied,tuple(a[0] for a in anchors))
    def _matching(self,position):
        if self.cache is None:return None
        # Identity fastpath only after the full predicted physical guard passed.
        if position is self.cache.position:self.metrics['guard_hits']+=1;return self.cache
        if position==self.cache.position:
            self.cache.position=position;self.metrics['guard_hits']+=1;return self.cache
        self.metrics['guard_misses']+=1;return None
    def _predict(self,parent,action):
        if parent is None or not action_is_board(action) or action_promotion_target_id(action) is not None:return None
        pos=parent.position;shape=pos.board_shape;source=square_to_index(action_source_square(action),shape);target=square_to_index(action_target_square(action),shape)
        mover=pos.board[source];victim=pos.board[target]
        if source==target or mover is None or mover.owner!=pos.side_to_move or (victim is not None and (victim.owner==mover.owner or victim.current_type_id in self.anchor_types)):return None
        board=list(pos.board);board[source]=None;board[target]=mover;boards=dict(parent.boards)
        boards[mover.owner,mover.current_type_id]=(boards[mover.owner,mover.current_type_id]&~(1<<source))|(1<<target)
        if victim is not None:boards[victim.owner,victim.current_type_id]&=~(1<<target)
        anchors=list(parent.anchors)
        if mover.current_type_id in self.anchor_types:anchors[mover.owner]=target
        predicted=replace(pos,board=tuple(board),side_to_move=1-pos.side_to_move)
        self.metrics['predictions']+=1
        return Snapshot(predicted,boards,(parent.occupied&~(1<<source))|(1<<target),tuple(anchors))
    def _attacked(self,data,target,by):
        return any(self.reverse.get((by,tid,target),0)&data.boards[by,tid] for tid in self.types)
    def _take_handoff(self):
        if self.native is None:return None
        handoff=getattr(self.native._metrics_local,'check_handoff',None);self.native._metrics_local.check_handoff=None;return handoff
    @staticmethod
    def _poll(checkpoint):
        if checkpoint is not None:checkpoint()
    def in_check(self,position,side,checkpoint=None):
        self.metrics['check_calls']+=1;self._take_handoff();self._poll(checkpoint)
        data=self._matching(position)
        if data is not None and type(side) is int and side in (0,1):
            result=bool(self._attacked(data,data.anchors[side],1-side));self.metrics['check_fast']+=1
        else:
            self.metrics['fallback_checks']+=1
            result=self.native.in_check(position,side,checkpoint=None) if self.native is not None else self.engine.in_check(position,side,checkpoint=None)
        self._poll(checkpoint);return result
    def has_legal_action(self,position,checkpoint=None):
        self.metrics['availability_calls']+=1;handoff=self._take_handoff();self._poll(checkpoint);data=self._matching(position);certificate=False
        if data is not None:
            side=position.side_to_move;source=data.anchors[side];piece=position.board[source]
            targets=self.forward.get((side,piece.current_type_id,source),0)&~data.occupied
            while targets:
                bit=targets&-targets;target=bit.bit_length()-1;targets^=bit
                # Empty landing removes no enemy source; no ray blockers exist.
                if not self._attacked(data,target,1-side):certificate=True;break
        if certificate:self.metrics['availability_certificates']+=1;result=True
        else:
            self.metrics['fallback_availability']+=1
            if self.native is not None:
                self.native._metrics_local.check_handoff=handoff
                result=self.native.has_legal_action(position,checkpoint=None)
            else:result=self.engine.has_legal_action(position,checkpoint=None)
        self._poll(checkpoint);return result
    @contextmanager
    def installed(self):
        assert not self.undo;self.cache=None;self.runtime=None;original_push=SearchPathRuntime.push;original_pop=SearchPathRuntime.pop;model=self
        def owned(runtime):return runtime.compiled is model.compiled and getattr(runtime._check_provider,'__self__',None) is model and getattr(runtime.availability_provider,'__self__',None) is model
        def push(runtime,action,checkpoint=None):
            if not owned(runtime):return original_push(runtime,action,checkpoint)
            if model.runtime is not runtime:
                if model.undo:return original_push(runtime,action,checkpoint)
                model.runtime=runtime;model.cache=model._build(runtime.position)
            if model.cache is None or model.cache.position!=runtime.position:model.cache=model._build(runtime.position)
            parent=model.cache;model.undo.append(parent)
            try:
                try:model.cache=model._predict(parent,action)
                except (ValueError,TypeError,AttributeError,IndexError):model.cache=None
                result=original_push(runtime,action,checkpoint);model.metrics['pushes']+=1;return result
            except BaseException:
                model.cache=model.undo.pop();model.metrics['rollbacks']+=1;raise
        def pop(runtime):
            if not owned(runtime) or model.runtime is not runtime or not model.undo:return original_pop(runtime)
            result=original_pop(runtime);model.cache=model.undo.pop();model.metrics['pops']+=1;return result
        try:
            with patch.object(SearchPathRuntime,'push',push),patch.object(SearchPathRuntime,'pop',pop):yield self
        finally:
            # A leaked Core frame is a failed caller contract, not hidden success.
            assert not self.undo,'incremental provider undo stack leaked'
            self.cache=None;self.runtime=None
