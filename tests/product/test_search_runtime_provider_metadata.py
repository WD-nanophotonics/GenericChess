"""Callable-object and bound-method provider metadata are the same contract."""
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution, initial_state
from generic_chess.core.search_runtime import SearchPathRuntime


@pytest.mark.parametrize('bound', [False, True])
def test_strict_failure_is_not_silently_relabelled_as_core(bound):
    class Provider:
        strict = True
        def __call__(self, position, ply, checkpoint):
            raise RuntimeError('provider unavailable')
    provider = Provider()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    runtime = SearchPathRuntime.from_state(initial_state(compiled), compiled,
        legal_binding_provider=provider.__call__ if bound else provider)
    with pytest.raises(RuntimeError, match='provider unavailable'):
        runtime.legal_actions()
    assert runtime.legal_provider_fallbacks == 0
    assert runtime.depth == 0


@pytest.mark.parametrize('bound', [False, True])
def test_provider_metrics_and_declared_non_strict_fallback(bound):
    class Provider:
        strict = False
        last_call_metrics = dict(payload_seconds=0.125, decode_binding_seconds=0.25)
        fail = False
        def __call__(self, position, ply, checkpoint):
            if self.fail:
                raise RuntimeError('provider unavailable')
            return ()
    provider = Provider()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    runtime = SearchPathRuntime.from_state(initial_state(compiled), compiled,
        legal_binding_provider=provider.__call__ if bound else provider)
    assert runtime.legal_actions() == ()
    assert runtime.legal_provider_calls == 1
    assert runtime.legal_provider_payload_seconds == 0.125
    assert runtime.legal_provider_decode_binding_seconds == 0.25
    provider.fail = True
    # A new runtime has no previous successful frontier cache.
    other = SearchPathRuntime.from_state(initial_state(compiled), compiled,
        legal_binding_provider=provider.__call__ if bound else provider)
    assert len(other.legal_actions()) == 30
    assert other.legal_provider_fallbacks == 1
    assert not other._legal_provider_active


@pytest.mark.parametrize('bound', [False, True])
def test_cancellation_never_becomes_provider_fallback(bound):
    class Abort(Exception):
        pass
    class Provider:
        strict = False
        def __call__(self, position, ply, checkpoint):
            checkpoint()
            return ()
    calls = 0
    def checkpoint():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise Abort
    provider = Provider()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    state = initial_state(compiled)
    runtime = SearchPathRuntime.from_state(state, compiled,
        legal_binding_provider=provider.__call__ if bound else provider)
    with pytest.raises(Abort):
        runtime.legal_actions(checkpoint)
    assert runtime.legal_provider_fallbacks == 0
    assert runtime.legal_provider_calls == 0
    assert runtime.position == state.position and runtime.depth == 0
