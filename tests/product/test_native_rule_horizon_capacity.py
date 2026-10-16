"""Rule horizon is not the fixed Native history/stack allocation."""
import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.native import _module, SemanticSearchEngine, semantic
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import (
    compile_native_semantic_rules, build_semantic_compile_payload,
    NativeUnsupportedRuleError, GC_SEM_MAX_PLY,
)
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from test_native_q_history_deferral import cycle, checked_replay
from native_test_helpers import requires_native

pytestmark = requires_native


@pytest.mark.parametrize("horizon", (1025, 2048, 65535))
def test_rule_horizon_preserved_without_changing_runtime_storage(horizon):
    session = cycle(max_ply=horizon, repetition=10000, prefix=4)
    rules = compile_native_semantic_rules(session.compiled)
    assert rules.backend_module.semantic_rules_info(rules.capsule)["max_ply"] == horizon
    assert _module().semantic_search_runtime_sizes()["max_ply"] == GC_SEM_MAX_PLY == 1024
    result = SemanticSearchEngine(session.compiled, rules, tt_megabytes=0).search(
        session, SearchLimits(max_depth=2, max_nodes=128,
            quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert result.completed_depth == 2
    checked_replay(session, rules, result)


@pytest.mark.parametrize("prefix", (1023, 1024, 1025))
@pytest.mark.parametrize("q", (0, 1))
def test_long_rule_search_refuses_storage_instead_of_inventing_terminal(prefix, q):
    session = cycle(max_ply=2048, repetition=10000, prefix=prefix)
    rules = compile_native_semantic_rules(session.compiled)
    before = session.state, session._search_witnesses
    assert not session.state.terminal_status.is_terminal
    if prefix <= 1024:
        packed = pack_semantic_search_position(session.compiled, rules, session)
        assert semantic.terminal_status(rules, packed)["status"] == "ongoing"
    engine = SemanticSearchEngine(session.compiled, rules, tt_megabytes=0)
    with pytest.raises(NotImplementedError, match="history capacity.*Core"):
        engine.search(session, SearchLimits(max_depth=1, max_nodes=128,
            quiescence_max_depth=q, quiescence_hard_max_depth=4 if q else 0))
    assert (session.state, session._search_witnesses) == before


@pytest.mark.parametrize("entry", (semantic.fixed_depth_search,
    semantic.probe_search, semantic.semantic_iterative_search, semantic.root_parallel_search))
def test_direct_search_entries_enforce_long_rule_storage_before_work(entry):
    session = cycle(max_ply=2048, repetition=10000, prefix=1023)
    rules = compile_native_semantic_rules(session.compiled)
    packed = pack_semantic_search_position(session.compiled, rules, session)
    before = semantic.snapshot(rules, packed)
    with pytest.raises(NotImplementedError, match="history capacity.*Core"):
        entry(rules, packed, 1)
    assert semantic.snapshot(rules, packed) == before


def test_old_kernel_capability_keeps_conservative_admission():
    actual = _module()
    class OldKernel:
        def __getattr__(self, name):
            return getattr(actual, name)
        def native_capabilities(self):
            caps = dict(actual.native_capabilities())
            caps.pop("semantic_max_rule_ply")
            return caps
    long = cycle(max_ply=2048, repetition=10000)
    with pytest.raises(NativeUnsupportedRuleError, match="limit 1024"):
        compile_native_semantic_rules(long.compiled, backend_module=OldKernel())
    short = cycle(max_ply=1024, repetition=10000)
    assert compile_native_semantic_rules(short.compiled, backend_module=OldKernel()).native_executable
    # The pure payload builder has no bound backend: keep its old default.
    with pytest.raises(NativeUnsupportedRuleError, match="limit 1024"):
        build_semantic_compile_payload(long.compiled)


@pytest.mark.parametrize("capability", (True, 65536, "65535", 2048))
def test_unknown_rule_capacity_capability_refused(capability):
    actual = _module()
    class Kernel:
        def __getattr__(self, name):
            return getattr(actual, name)
        def native_capabilities(self):
            return dict(actual.native_capabilities(), semantic_max_rule_ply=capability)
    with pytest.raises(NativeUnsupportedRuleError, match="rule-ply capability"):
        compile_native_semantic_rules(cycle().compiled, backend_module=Kernel())


@pytest.mark.parametrize("horizon", (0, 65536))
def test_raw_c_parser_refuses_out_of_uint16_rule_horizon(horizon):
    payload, _ = build_semantic_compile_payload(cycle().compiled)
    with pytest.raises((ValueError, OverflowError)):
        _module().compile_semantic_rules(dict(payload, max_ply=horizon))


def test_core_legality_provider_declines_long_record_at_storage_boundary():
    session = cycle(max_ply=2048, repetition=10000)
    provider = NativeSemanticLegalityProvider.try_create(session.compiled, strict=True)
    assert provider is not None
    assert provider.supports_position(session.state.position, 1023)
    assert not provider.supports_position(session.state.position, 1024)
    assert not provider.supports_position(session.state.position, 1025)
