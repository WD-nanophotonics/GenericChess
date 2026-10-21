"""Finite research decoder reuse; C still owns complete checked transitions."""
from scripts.native_capsule_runtime import CapsulePathRuntime
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.native import semantic as ns


class DecodedCapsulePathRuntime(CapsulePathRuntime):
    def __init__(self, initial, compiled, witnesses):
        super().__init__(initial, compiled, witnesses)
        self._decoder = NativeSemanticLegalityProvider(compiled,
            semantic_engine_for(compiled), self.native, strict=True)
        self._public_cache = {}
        self.decoded_actions = self.public_cache_hits = self.public_cache_misses = 0

    def legal_actions(self, checkpoint=None):
        if checkpoint:
            checkpoint()
        self.legal_provider_calls += 1
        raw_actions = ns.transient_legal_actions(self.native, self.capsule)
        rawmap = {}
        position = self.position
        for index, raw in enumerate(raw_actions):
            if index and index % 64 == 0 and checkpoint:
                checkpoint()
            semantic = self._decoder._decode_action(int(raw), position)
            self.decoded_actions += 1
            public = self._public_cache.get(raw)
            if public is None:
                public = _semantic_public_action(self._decoder.engine, semantic)
                self.public_cache_misses += 1
                if len(self._public_cache) >= 2048:
                    self._public_cache.clear()
                self._public_cache[raw] = public
            else:
                self.public_cache_hits += 1
            rawmap[public] = raw
        if checkpoint:
            checkpoint()
        self._rawmap = rawmap
        return tuple(rawmap)
