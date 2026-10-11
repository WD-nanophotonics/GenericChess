"""Mixed wildcard victims must not disappear from the Native frontier."""
from dataclasses import replace
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from native_test_helpers import requires_native
from test_f24c_mixed_mechanic_certification import _compiled
from test_f24c_mixed_mechanic_certification_r1 import _simultaneous


@requires_native
def test_mixed_complete_frontier_and_capture_children_match_core():
    compiled = _compiled()
    position = _simultaneous(compiled)
    engine = semantic_engine_for(compiled)
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    assert provider is not None
    core = {_semantic_public_action(engine, action): action
            for action in engine.legal_actions(position)}
    native = dict(provider(position, 0))
    assert set(native) == set(core)
    captures = [a for a in core if "capture_" in a.pattern_id]
    assert len(captures) == 3
    for action in captures:
        semantic, binding = native[action]
        assert engine._transition(position, semantic, binding) == engine.apply(position, core[action])


def test_only_filter_wildcards_are_lowered_to_absent_type_constraint():
    from generic_chess.native.compiler import _sem_effect
    compiled = _compiled()
    effects = [e for p in semantic_engine_for(compiled)._patterns for e in p.effects]
    wildcard = next(e for e in effects if e.kind == "remove" and e.piece_type_ref is not None and e.piece_type_ref.kind == "any")
    mapping = {name: i for i, name in enumerate(compiled.support.type_metadata)}
    for kind in ("move", "shift", "remove"):
        effect = replace(wildcard, kind=kind)
        assert _sem_effect(effect, 7, mapping, "test")["piece_type_ref"] is None
    # Operations requiring a type operand must keep their reference.
    for kind in ("place", "remove_from_hand"):
        assert _sem_effect(replace(wildcard, kind=kind), 7, mapping, "test")["piece_type_ref"]["kind"] == 3
