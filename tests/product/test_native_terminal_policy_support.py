"""A legal-action kernel must not silently override no-move adjudication."""
import pytest
from dataclasses import replace
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native.compiler import compile_native_semantic_rules,NativeUnsupportedRuleError
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.semantic import terminal_status,fixed_depth_search,probe_search,semantic_iterative_search,root_parallel_search
from generic_chess.session.session import GameSession
from native_test_helpers import requires_native

pytestmark=requires_native


@pytest.mark.parametrize('entry',[terminal_status,fixed_depth_search,probe_search,semantic_iterative_search,root_parallel_search])
def test_old_binary_loss_binding_rejected_before_native_search_or_terminal(entry):
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    native=compile_native_semantic_rules(compiled)
    native._bound_stalemate_result = None  # Actual older C metadata lacks this field.
    args=(native,None) if entry is terminal_status else (native,None,1)
    with pytest.raises(NativeUnsupportedRuleError,match='stalemate loss'):
        entry(*args)


def test_old_binary_loss_keeps_legality_but_rejects_persistent_search():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    session=GameSession(compiled)
    provider=NativeSemanticLegalityProvider.try_create(compiled,strict=True)
    assert provider is not None
    assert {action for action,_ in provider(session.state.position,0)}==set(session.legal_actions())
    provider.native_rules._bound_stalemate_result = None
    with pytest.raises(NativeUnsupportedRuleError,match='stalemate loss'):
        SemanticSearchEngine(compiled,provider.native_rules,tt_megabytes=0)


def test_draw_policy_keeps_existing_native_search_entry():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    native=compile_native_semantic_rules(compiled)
    engine=SemanticSearchEngine(compiled,native,tt_megabytes=0)
    assert engine.ruleset_fingerprint==compiled.ruleset_fingerprint


@pytest.mark.parametrize('entry',[fixed_depth_search,probe_search])
def test_legacy_fixed_probe_reject_continuous_check_winner_policy(entry):
    rules=replace(build_builtin_ruleset('standard_shogi'),stalemate_result='draw')
    compiled=compile_ruleset_for_execution(rules)
    native=compile_native_semantic_rules(compiled)
    with pytest.raises(NativeUnsupportedRuleError,match='continuous-check winners'):
        entry(native,None,1)


def _stalemate(policy, repeated=False):
    from types import SimpleNamespace
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.identity import position_identity_key
    from generic_chess.core.terminal import terminal_result
    from generic_chess.native.adapter import pack_semantic_search_position
    from scripts.chess_development import root_from_fen

    original = root_from_fen(
        "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
        compile_ruleset_for_execution(build_builtin_ruleset("western_chess")),
    )
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("western_chess"), stalemate_result=policy,
        repetition_limit=4 if repeated else 100000,
    ))
    position = replace(original.position, ruleset_fingerprint=compiled.ruleset_fingerprint)
    key = position_identity_key(position, compiled)
    actors = (-1, 0, 1, 0) if repeated else (-1,)
    state = replace(original, position=position, ply_count=len(actors)-1,
                    history=tuple(HistoryRecord(key, a, "", False) for a in actors))
    state = replace(state, terminal_status=terminal_result(state, compiled))
    native = compile_native_semantic_rules(compiled)
    session = SimpleNamespace(compiled=compiled, state=state, result=state.terminal_status,
                              _search_witnesses=(position,)*len(actors))
    packed = pack_semantic_search_position(compiled, native, session)
    return compiled, native, session, packed


@pytest.mark.parametrize("policy,winner", [("draw", None), ("loss", 0)])
@pytest.mark.parametrize("repeated", [False, True])
def test_same_physical_stalemate_policy_and_repetition_precedence(policy, winner, repeated):
    from generic_chess.native import _module
    from generic_chess.native.semantic import snapshot, transient_legal_actions, in_check
    compiled, native, session, packed = _stalemate(policy, repeated)
    saved = snapshot(native, packed)
    info = _module().semantic_rules_info(native.capsule)
    assert info["stalemate_result"] == int(policy == "loss")
    assert info["fingerprint"] == compiled.ruleset_fingerprint
    assert not transient_legal_actions(native, packed)
    assert not in_check(native, packed, 1)
    if repeated:
        assert len(session.state.history) == compiled.support.repetition_limit == 4
        assert len({record.position_key for record in session.state.history}) == 1
    assert session.result.status.value == "stalemate"
    assert session.result.winner == winner
    assert terminal_status(native, packed) == {"status": "stalemate", "winner": winner}
    for entry in (fixed_depth_search, probe_search):
        result = entry(native, packed, 2)
        assert result["score"] == (0 if winner is None else -1000000)
        assert result["best_action"] is None
    for entry in (semantic_iterative_search, root_parallel_search):
        result = entry(native, packed, 2)
        assert result["score"] == (0 if winner is None else -100000000)
        assert result["best_action"] is None
    # Public persistent search returns its existing terminal_position sentinel;
    # the C persistent entry must also propagate the winner if invoked directly.
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=0)
    raw = _module().semantic_engine_search(engine._capsule, packed, 2, None, None, None)
    assert raw["score"] == (0 if winner is None else -100000000)
    assert raw["best_action"] is None
    assert snapshot(native, packed) == saved


def test_optional_policy_defaults_to_draw_and_rejects_unknown_codes():
    from generic_chess.native import _module
    from generic_chess.native.compiler import build_semantic_compile_payload
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    payload, _ = build_semantic_compile_payload(compiled)
    payload.pop("stalemate_result")
    capsule = _module().compile_semantic_rules(payload)
    assert _module().semantic_rules_info(capsule)["stalemate_result"] == 0
    for code in (-1, 2, 256, "loss"):
        with pytest.raises((ValueError, TypeError, OverflowError)):
            _module().compile_semantic_rules({**payload, "stalemate_result": code})


def test_real_standard_shogi_loss_capsule_supports_persistent_entry():
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("standard_shogi"))
    native = compile_native_semantic_rules(compiled)
    native.require_terminal_policy_support()
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=0)
    assert engine.ruleset_fingerprint == compiled.ruleset_fingerprint


@pytest.mark.parametrize("policy,score", [("draw", 0), ("loss", -99999999)])
def test_recursive_child_uses_shared_stalemate_winner(policy, score):
    from types import SimpleNamespace
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.identity import position_identity_key
    from generic_chess.core.terminal import terminal_result
    from generic_chess.core.transition import apply_action
    from generic_chess.native.adapter import pack_semantic_search_position
    from generic_chess.native import _module
    from generic_chess.native.semantic import snapshot
    from scripts.chess_development import root_from_fen
    from scripts.audit_lichess_complete_children import uci

    original = root_from_fen("7k/5K2/8/6Q1/8/8/8/8 w - - 0 1",
        compile_ruleset_for_execution(build_builtin_ruleset("western_chess")))
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("western_chess"), stalemate_result=policy))
    position = replace(original.position, ruleset_fingerprint=compiled.ruleset_fingerprint)
    key = position_identity_key(position, compiled)
    state = replace(original, position=position, history=(HistoryRecord(key, -1, "", False),))
    state = replace(state, terminal_status=terminal_result(state, compiled))
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (position,)
    action = next(a for a in session.legal_actions() if uci(a) == "g5g6")
    child = apply_action(state, action, compiled)
    assert child.terminal_status.status.value == "stalemate"
    assert child.terminal_status.winner == (None if policy == "draw" else 0)
    child_key = position_identity_key(child.position, compiled)
    native = compile_native_semantic_rules(compiled)
    packed = pack_semantic_search_position(compiled, native, session)
    saved = snapshot(native, packed)
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=0)
    raw = _module().semantic_engine_search(engine._capsule, packed, 1, None,
                                         None, None, None, False, True)
    matching = [r for r in raw["training_trace"] if r["position_identity"] == child_key]
    assert matching
    assert all(r["terminal"] and r["search_ply"] == 1 and r["score_native"] == score
               for r in matching)
    assert snapshot(native, packed) == saved
