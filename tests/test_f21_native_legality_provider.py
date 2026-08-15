"""F21 H21A provider-boundary and fail-safe integration tests."""

from __future__ import annotations

import pytest

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.semantic_executor import _semantic_public_action, semantic_engine_for
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.native import native_available


pytestmark = pytest.mark.skipif(not native_available(), reason="Native extension unavailable")


def _semantic_specs():
    from scripts.audit_f4_runtime_cost import corpus_specs

    return [spec for spec in corpus_specs() if spec["kind"] == "semantic"]


@pytest.mark.parametrize("spec", _semantic_specs(), ids=lambda row: row["id"])
def test_provider_matches_python_order_identity_and_binding(spec):
    from scripts.audit_f4_runtime_cost import make_session

    session = make_session(spec)
    provider = NativeSemanticLegalityProvider.try_create(session.compiled)
    assert provider is not None
    native_pairs = provider(session.state.position, session.state.ply_count)
    engine = semantic_engine_for(session.compiled)
    python_pairs = tuple(
        (_semantic_public_action(engine, action), (action, binding))
        for action, binding in engine.iter_legal_action_bindings(session.state.position)
    )
    assert native_pairs == python_pairs
    assert provider.last_call_metrics["actions"] == len(native_pairs)


def test_runtime_provider_cache_and_push_pop_restore():
    from scripts.audit_f4_runtime_cost import make_session

    session = make_session(_semantic_specs()[0])
    provider = NativeSemanticLegalityProvider.try_create(session.compiled)
    runtime = SearchPathRuntime.from_state(
        session.state,
        session.compiled,
        history_witnesses=session._search_witnesses,
        legal_binding_provider=provider,
    )
    root = runtime.legal_actions()
    assert root
    assert runtime.legal_actions() is root
    calls = runtime.legal_provider_calls
    runtime.push(root[0])
    child = runtime.legal_actions()
    assert runtime.legal_provider_calls == calls + (1 if child else 0)
    runtime.pop()
    assert runtime.legal_actions() == root
    runtime.assert_balanced()


def test_operational_provider_failure_falls_back_without_partial_cache():
    from scripts.audit_f4_runtime_cost import make_session

    session = make_session(_semantic_specs()[0])
    expected = SearchPathRuntime.from_state(
        session.state, session.compiled, history_witnesses=session._search_witnesses
    ).legal_actions()

    def broken_provider(position, ply_count, checkpoint):
        checkpoint()
        raise RuntimeError("injected F21 provider failure")

    runtime = SearchPathRuntime.from_state(
        session.state,
        session.compiled,
        history_witnesses=session._search_witnesses,
        legal_binding_provider=broken_provider,
    )
    assert runtime.legal_actions() == expected
    assert runtime.legal_provider_operational_failures == 1
    assert runtime.legal_provider_fallbacks == 1
    assert runtime._legal_provider_active is False
    assert runtime._bindings


def test_native_on_and_python_off_search_results_match():
    from scripts.audit_f4_runtime_cost import make_session
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits

    session = make_session(_semantic_specs()[0])
    limits = SearchLimits(max_depth=2, max_nodes=128, quiescence_max_depth=0)
    python_player = AlphaBetaPlayer(
        session.compiled,
        use_native_semantic_legality=False,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
    )
    native_player = AlphaBetaPlayer(
        session.compiled,
        use_native_semantic_legality=True,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
    )
    assert native_player.native_legality_provider is not None
    default_player = AlphaBetaPlayer(
        session.compiled,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
    )
    assert default_player.use_native_semantic_legality is True
    assert default_player.native_legality_provider is not None
    left = python_player.choose_action(session, limits)
    right = native_player.choose_action(session, limits)
    for name in (
        "action", "score", "principal_variation", "completed_depth",
        "selective_depth", "nodes", "qnodes", "termination_reason",
    ):
        assert getattr(left, name) == getattr(right, name), name


def test_legacy_ruleset_never_attempts_semantic_provider():
    from scripts.audit_f4_runtime_cost import corpus_specs, make_session
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer

    session = make_session(next(spec for spec in corpus_specs() if spec["kind"] == "legacy"))
    player = AlphaBetaPlayer(session.compiled, use_native_semantic_legality=True, use_disk_cache=False)
    assert player.native_legality_provider is None
