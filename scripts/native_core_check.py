"""Scoped research readonly check consumer; Core owns check responsibility/history."""
import time
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native import semantic as ns

class NativeCoreCheck:
    def __init__(self, compiled):
        self.provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
        self.calls = self.imports = self.queries = self.fallbacks = 0
        self.payload_seconds = self.query_seconds = 0.0

    def for_position(self, position, side, checkpoint=None):
        self.calls += 1
        if checkpoint: checkpoint()
        provider = self.provider
        if provider is None:
            self.fallbacks += 1
            return None
        if position.ruleset_fingerprint != provider.native_rules.fingerprint:
            raise ValueError("check compiled source mismatch")
        started = time.perf_counter()
        packed = ns.pack_position(provider.native_rules, provider._state_only_payload(position, 0))
        self.imports += 1
        self.payload_seconds += time.perf_counter() - started
        started = time.perf_counter()
        value = ns.in_check(provider.native_rules, packed, side)
        self.queries += 1
        self.query_seconds += time.perf_counter() - started
        if checkpoint: checkpoint()
        return value
