"""Research-only availability consumer; Core keeps terminal/history authority."""
import inspect, textwrap, time
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core import terminal as terminal_module
from generic_chess.core import search_runtime as runtime_module
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.native import semantic as ns

class NativeCoreAvailability:
    def __init__(self, compiled):
        self.compiled=compiled
        self.provider=NativeSemanticLegalityProvider.try_create(compiled,strict=True)
        self.calls=self.imports=self.queries=self.fallbacks=0
        self.payload_seconds=self.query_seconds=0.0

    def for_position(self, position, checkpoint=None):
        self.calls+=1
        if checkpoint: checkpoint()
        provider=self.provider
        if provider is None or (provider._requires_reply_probe and self.compiled.support.max_ply<=1):
            self.fallbacks+=1
            return semantic_engine_for(self.compiled).has_legal_action(position,checkpoint=checkpoint)
        if position.ruleset_fingerprint != provider.native_rules.fingerprint:
            raise ValueError('availability compiled source mismatch')
        started=time.perf_counter()
        # The existing availability primitive ignores ply/history cutoffs;
        # the unchanged Core caller supplies adjudication in its own order.
        packed=ns.pack_position(provider.native_rules,provider._state_only_payload(position,0))
        self.imports+=1;self.payload_seconds+=time.perf_counter()-started
        started=time.perf_counter();value=ns.has_legal_action(provider.native_rules,packed)
        self.queries+=1;self.query_seconds+=time.perf_counter()-started
        if checkpoint: checkpoint()
        return value

    def __call__(self, runtime, checkpoint=None):
        if runtime.compiled is not self.compiled:
            raise ValueError('availability compiled source mismatch')
        return self.for_position(runtime.position,checkpoint=checkpoint)

    def install(self):
        source=textwrap.dedent(inspect.getsource(terminal_module.terminal_from_search_runtime))
        target='has_legal = engine.has_legal_action(position, checkpoint=checkpoint)'
        assert source.count(target)==1
        source=source.replace(target,'has_legal = native_availability(runtime, checkpoint=checkpoint)')
        namespace=dict(terminal_module.__dict__,native_availability=self)
        exec(compile(source,'<research-native-availability-terminal>','exec'),namespace)
        self.terminal_source=source
        self._original=runtime_module.terminal_from_search_runtime
        runtime_module.terminal_from_search_runtime=namespace['terminal_from_search_runtime']

    def restore(self):
        runtime_module.terminal_from_search_runtime=self._original
