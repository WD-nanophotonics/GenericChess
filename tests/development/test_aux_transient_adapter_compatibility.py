"""Portable subset of sandbox76da1ff8's transient-import contract checks.

Uses an explicit fake ABI to exercise Python routing. This never substitutes
for the new C capsule lifecycle tests, which require the absent private binary.
No producer/PRIMARY ledger dependency, build, Player or search execution.
"""
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import generic_chess.native as native

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession


@pytest.fixture(scope="module")
def root():
    data = json.loads((Path(__file__).parents[1] / "fixtures" /
                       "leaper_occupancy_projection.json").read_text())
    compiled = compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(data["RuleSet"]))
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(data["record"])))
    return compiled, session.state.position


def adapter(compiled, *, requested=False, new_abi=True):
    calls = []
    def ordinary(rules, payload):
        calls.append(("ordinary", dict(payload)))
        return object()
    def transient(rules, payload):
        calls.append(("transient", dict(payload)))
        return object()
    backend = SimpleNamespace(semantic_pack_position=ordinary,
        semantic_in_check=lambda *_: False, semantic_has_legal_action=lambda *_: True,
        semantic_transient_legal_actions=lambda *_: ())
    if new_abi:
        backend.semantic_pack_transient_position = transient
    native = SimpleNamespace(type_ids=tuple(compiled.support.type_metadata),
        pattern_ids=tuple(p.pattern_id for p in compiled.ir.patterns),
        geometry_ids=tuple(compiled.ir.geometry), capsule=object(),
        backend_module=backend, fingerprint=compiled.ruleset_fingerprint, native_executable=True)
    result = NativeSemanticLegalityProvider(compiled, semantic_engine_for(compiled), native,
                                            transient_imports=requested)
    return result, calls


@pytest.mark.parametrize("requested,new_abi,expected", [(False, True, False),
                                                       (True, False, False),
                                                       (True, True, True)])
def test_opt_in_and_older_abi_keep_expected_payload_route(root, requested, new_abi, expected):
    compiled, position = root
    provider, calls = adapter(compiled, requested=requested, new_abi=new_abi)
    assert provider.transient_imports is expected
    provider._pack_position(position, 2)
    kind, payload = calls[-1]
    assert kind == ("transient" if expected else "ordinary")
    assert payload["ply"] == 2 and len(payload["board"]) == compiled.board_shape.area
    assert "history" not in payload and "history_events" not in payload
    if not expected:
        assert payload["aux"] == []  # Existing ordinary Python normalization.


def test_ir_facade_declines_only_transient_route_without_legacy_metadata(root):
    compiled, position = root
    facade = CompiledSemanticRuleset(compiled.ir, support=compiled.support)
    provider, calls = adapter(facade, requested=True)
    assert not provider.transient_imports
    provider._pack_position(position, 2)
    assert calls[-1][0] == "ordinary"


def test_transient_route_rejects_unexpected_aux_before_fake_abi(root):
    compiled, position = root
    provider, calls = adapter(compiled, requested=True)
    payload = provider._state_only_payload(position, 0)
    payload["aux_state"] = (((99, -1), 1),)
    with pytest.raises(ValueError, match="unexpectedly contains aux"):
        provider._pack_payload(payload)
    assert calls == []


def test_check_availability_handoff_does_not_supply_actual_ply_frontier(root):
    compiled, position = root
    provider, calls = adapter(compiled, requested=True)
    assert provider.in_check(position, 0) is False
    assert provider.has_legal_action(position) is True
    assert len(calls) == 1 and calls[0][1]["ply"] == 0
    # Fake ABI returns no actions; this tests import routing, NOT legal parity.
    assert provider(position, 2) == ()
    assert len(calls) == 2 and calls[1][1]["ply"] == 2
    assert provider.availability_metrics["reused_imports"] == 1


def test_availability_abort_consumes_one_use_handoff(root):
    compiled, position = root
    provider, calls = adapter(compiled, requested=True)
    provider.in_check(position, 0)
    def stop():
        raise RuntimeError("test cancellation")
    with pytest.raises(RuntimeError, match="test cancellation"):
        provider.has_legal_action(position, checkpoint=stop)
    assert len(calls) == 1
    assert provider.has_legal_action(position) is True
    assert len(calls) == 2  # The pre-abort input was already consumed.


def test_player_default_does_not_enable_new_route():
    assert inspect.signature(AlphaBetaPlayer).parameters["use_native_transient_imports"].default is False


@pytest.mark.skipif(not native.native_available(), reason="optional Native unavailable")
def test_actual_older_installed_binary_falls_back_to_existing_readonly_queries(root):
    if hasattr(native._module(), "semantic_pack_transient_position"):
        pytest.skip("this control specifically exercises an older installed ABI")
    compiled, position = root
    provider = NativeSemanticLegalityProvider.try_create(compiled, transient_imports=True)
    assert provider is not None and not provider.transient_imports
    engine = semantic_engine_for(compiled)
    for side in (0, 1):
        assert provider.in_check(position, side) == engine.in_check(position, side)
    assert provider.has_legal_action(position) == engine.has_legal_action(position)
