"""Compiled classification changes scheduling cost, never state eligibility."""
from dataclasses import replace

import pytest

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.core.semantic_executor import SemanticEngine
from rule_semantics_ir_fixtures import (
    cannon_ruleset, castling_ruleset, uchifuzume_ruleset, weird_rulesets,
)


@pytest.mark.parametrize("rule", [
    build_builtin_ruleset("western_chess"),
    build_builtin_ruleset("standard_shogi"),
    cannon_ruleset(), castling_ruleset(), uchifuzume_ruleset(), *weird_rulesets(),
])
def test_drop_dispatch_keeps_children_first_action_and_reply_polling(rule):
    compiled = compile_ruleset_for_execution(rule)
    fallback = replace(compiled)
    object.__setattr__(fallback, "_pattern_drop_kinds", None)
    indexed, plain = SemanticEngine(compiled), SemanticEngine(fallback)
    parent = indexed._initial_position()
    actions = indexed.legal_actions(parent)
    assert actions == plain.legal_actions(parent)
    states = [parent]
    for action in actions:
        child = indexed.apply(parent, action)
        assert child == plain.apply(parent, action)
        states.append(child)
    for position in states:
        assert indexed.legal_actions(position) == plain.legal_actions(position)
        for name in ("has_legal_action", "_exists_s3_reply"):
            results = []
            for engine in (indexed, plain):
                polls = []
                result = getattr(engine, name)(
                    position, checkpoint=lambda: polls.append(None),
                )
                results.append((result, len(polls)))
            assert results[0] == results[1]
            for at in (1, max(1, results[0][1] // 2), results[0][1]):
                count = 0
                def cancel():
                    nonlocal count
                    count += 1
                    if count == at:
                        raise InterruptedError("kind dispatch poll")
                with pytest.raises(InterruptedError, match="kind dispatch poll"):
                    getattr(indexed, name)(position, checkpoint=cancel)
                assert indexed.has_legal_action(position) == results[0][0]


def test_replacement_rebuilds_kind_from_geometry_and_foreign_pattern_falls_back():
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("standard_shogi"))
    drop = next(p for p in compiled.ir.patterns if compiled._pattern_drop_kinds[p.geometry_ids])
    gid = drop.geometry_ids[0]
    geometry = dict(compiled.ir.geometry)
    geometry[gid] = replace(geometry[gid], kind="leap")
    changed = replace(compiled, ir=replace(compiled.ir, geometry=geometry))
    assert changed._pattern_drop_kinds is not compiled._pattern_drop_kinds
    assert compiled._pattern_drop_kinds[drop.geometry_ids] is True
    assert changed._pattern_drop_kinds[drop.geometry_ids] is False
    engine = SemanticEngine(compiled)
    foreign = replace(drop, geometry_ids=())
    assert foreign.geometry_ids not in compiled._pattern_drop_kinds
    assert engine._pattern_is_drop(foreign) is False


def test_mixed_and_missing_geometry_keep_original_drop_classification():
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("standard_shogi"))
    drop = next(p for p in compiled.ir.patterns if compiled._pattern_drop_kinds[p.geometry_ids])
    board = next(p for p in compiled.ir.patterns if not compiled._pattern_drop_kinds[p.geometry_ids])
    mixed = replace(drop, geometry_ids=("absent-geometry",) + board.geometry_ids + drop.geometry_ids)
    changed = replace(compiled, ir=replace(compiled.ir, patterns=(mixed,)))
    assert SemanticEngine(changed)._pattern_is_drop(mixed) is True


def test_serialized_dispatch_uses_geometry_semantics():
    import pickle

    compiled = compile_ruleset_for_execution(build_builtin_ruleset("standard_shogi"))
    # Full compiled products contain mappingproxy fields and have no pickle
    # contract. This checks only the new private table's representation.
    restored = replace(compiled)
    object.__setattr__(restored, "_pattern_drop_kinds",
                       pickle.loads(pickle.dumps(compiled._pattern_drop_kinds)))
    engine = SemanticEngine(restored)
    for pattern in restored.ir.patterns:
        expected = any(restored.ir.geometry[g].kind == "drop"
                       for g in pattern.geometry_ids if g in restored.ir.geometry)
        assert engine._pattern_is_drop(pattern) is expected
        assert restored._pattern_drop_kinds[pattern.geometry_ids] is expected
    root = engine._initial_position()
    assert engine.legal_actions(root) == SemanticEngine(compiled).legal_actions(root)


def test_dispatch_preserves_simultaneous_hand_aux_and_capture_children():
    from test_f24c_mixed_mechanic_certification import _compiled, A0
    from test_f24c_mixed_mechanic_certification_r1 import _simultaneous

    compiled = _compiled()
    fallback = replace(compiled)
    object.__setattr__(fallback, "_pattern_drop_kinds", None)
    indexed, plain = SemanticEngine(compiled), SemanticEngine(fallback)
    root = _simultaneous(compiled)
    assert root.hands[0].count(A0) > 0
    states = [root] + [indexed.apply(root, action)
                       for action in indexed.legal_actions(root)]
    assert any(action.source is None for action in indexed.legal_actions(root))
    for position in states:
        assert indexed.legal_actions(position) == plain.legal_actions(position)
        assert indexed.has_legal_action(position) == plain.has_legal_action(position)
        assert indexed._exists_s3_reply(position) == plain._exists_s3_reply(position)
