"""Research-only exact Native-to-Core immutable binding memo.

Every Native query, packed decode, source/owner/base/current validation, public
Action and current legal set remains original. Only _make_binding_from_action
on THIS provider's engine instance is memoized. It stores no Position, Piece,
Session, runtime, legal-set, value or history. Strict ordinary Leap/source-field
admission; misses run the complete original builder; failure never enters cache.
"""
from contextlib import contextmanager
from dataclasses import fields
from unittest.mock import patch
from generic_chess.core.semantic_executor import SemanticAction,_ActionBinding
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry

class NativeBindingMemo:
    def __init__(self,native,maximum=4096):
        self.native=native;self.engine=native.engine;self.original=self.engine._make_binding_from_action;self.maximum=min(4096,max(1,int(maximum)));self.cache={};self._installed=False
        expected={'pattern','geometry_id','actor_owner','actor_type','actor_base','actor_current','source','target','promotion_target_id','path'}
        self.admitted=ordinary_leap_geometry(native.compiled) is not None and {f.name for f in fields(_ActionBinding)}==expected
        self.metrics=dict(calls=0,hits=0,misses=0,unsupported=0,clears=0,peak_entries=0)
    def bind(self,position,action,pattern):
        self.metrics['calls']+=1
        if (not self.admitted or type(action) is not SemanticAction or type(position.side_to_move) is not int or position.side_to_move not in (0,1) or type(action.source) is not int or not 0<=action.source<len(position.board) or self.native.pattern_by_id.get(action.pattern_id) is not pattern):
            self.metrics['unsupported']+=1;return self.original(position,action,pattern)
        piece=position.board[action.source]
        if piece is None or type(piece.owner) is not int or type(piece.base_type_id) is not str or type(piece.current_type_id) is not str:
            self.metrics['unsupported']+=1;return self.original(position,action,pattern)
        # Full SemanticAction includes pattern/geometry/actor/source/target/
        # promotion. Side selects owner-frame path; actor fields are exactly
        # the only position values read by _make_binding. Pattern stays owned
        # immutable compiled data, and identity prevents cross-pattern aliasing.
        key=(action,position.side_to_move,piece.owner,piece.base_type_id,piece.current_type_id,id(pattern))
        value=self.cache.get(key)
        if value is not None:self.metrics['hits']+=1;return value
        self.metrics['misses']+=1;value=self.original(position,action,pattern)
        if len(self.cache)>=self.maximum:self.cache.clear();self.metrics['clears']+=1
        self.cache[key]=value;self.metrics['peak_entries']=max(self.metrics['peak_entries'],len(self.cache));return value
    @contextmanager
    def installed(self):
        assert not self._installed;self._installed=True
        try:
            with patch.object(self.engine,'_make_binding_from_action',self.bind):yield self
        finally:self._installed=False;self.cache.clear()
