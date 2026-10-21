"""Research child check/availability sharing one exact immutable ply0 projection."""
import time
from scripts.native_core_availability import NativeCoreAvailability
from generic_chess.native import semantic as ns

class NativeCoreProbe(NativeCoreAvailability):
    def __init__(self, compiled, *, shared):
        super().__init__(compiled)
        self.shared=shared
        self._position=self._packed=None
        self.reuses=self.check_calls=self.check_queries=self.check_fallbacks=0

    def _pack(self, position):
        if position.ruleset_fingerprint != self.provider.native_rules.fingerprint:
            raise ValueError('probe compiled source mismatch')
        if self.shared and position is self._position:
            self.reuses+=1
            return self._packed
        started=time.perf_counter()
        packed=ns.pack_position(self.provider.native_rules,self.provider._state_only_payload(position,0))
        self.imports+=1
        self.payload_seconds+=time.perf_counter()-started
        if self.shared:self._position,self._packed=position,packed
        return packed

    def check(self, position, checkpoint=None):
        self.check_calls+=1
        if checkpoint:checkpoint()
        if self.provider is None:
            self.check_fallbacks+=1
            return None
        packed=self._pack(position)
        started=time.perf_counter()
        value=ns.in_check(self.provider.native_rules,packed,position.side_to_move)
        self.check_queries+=1
        self.query_seconds+=time.perf_counter()-started
        if checkpoint:checkpoint()
        return value

    def for_position(self, position, checkpoint=None):
        self.calls+=1
        if checkpoint:checkpoint()
        if self.provider is None or (self.provider._requires_reply_probe and self.compiled.support.max_ply<=1):
            from generic_chess.core.semantic_executor import semantic_engine_for
            self.fallbacks+=1
            return semantic_engine_for(self.compiled).has_legal_action(position,checkpoint=checkpoint)
        packed=self._pack(position)
        started=time.perf_counter()
        value=ns.has_legal_action(self.provider.native_rules,packed)
        self.queries+=1
        self.query_seconds+=time.perf_counter()-started
        if checkpoint:checkpoint()
        return value
