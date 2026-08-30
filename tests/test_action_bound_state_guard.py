"""F24E tests for the generic action-bound state-guard subject."""

from dataclasses import replace

import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.native.compiler import NativeUnsupportedRuleError, build_semantic_compile_payload
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
    compute_fingerprint,
    ruleset_from_dict,
    ruleset_to_dict,
)


REF = lambda kind, **kwargs: RuleSquareRef(kind=kind, **kwargs)


def _guard(*, subject_ref, type_id, owner="self", spatial=None):
    return RuleStateGuard(
        aggregation="count", owner=owner,
        type_ref=RuleTypeRef(kind="explicit", type_id=type_id),
        compare_field="base", promoted="no", location="board",
        spatial=spatial or RuleSpatialSelector(kind="exact", refs=(subject_ref,)),
        comparison="eq", value=1, subject_ref=subject_ref,
    )


def _generic_ruleset():
    k = PieceType("K", "K", tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)), is_anchor=True)
    x = PieceType("X", "X", ())
    v = PieceType("V", "V", ())
    w = PieceType("W", "W", ())
    rows = [[None] * 8 for _ in range(8)]
    rows[0][4] = Piece(0, "K", "K")
    rows[7][4] = Piece(1, "K", "K")
    capture = (
        RuleActionEffect("remove", square_ref=REF("target"), disposition="remove_from_game", piece_owner="opponent"),
        RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
    )
    source = RuleSemanticAction(
        name="opaque_source_bound", type_ids=("X",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)), target_relation="enemy",
        state_guards=(_guard(subject_ref=REF("source"), type_id="X", spatial=RuleSpatialSelector(kind="same_file", refs=(REF("fixed", square=(2, 0), owner_relative=False),))),),
        effects=capture, invariants=(RuleInvariant("own_anchor_safe"),),
    )
    target = RuleSemanticAction(
        name="opaque_target_bound", type_ids=("X",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)), target_relation="enemy",
        state_guards=(_guard(subject_ref=REF("target"), type_id="V", owner="opponent"),),
        effects=capture, invariants=(RuleInvariant("own_anchor_safe"),),
    )
    empty = RuleSemanticAction(
        name="opaque_empty_subject", type_ids=("X",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)), target_relation="empty",
        state_guards=(_guard(subject_ref=REF("target"), type_id="V", owner="opponent"),),
        effects=(RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    unresolved = RuleSemanticAction(
        name="opaque_unresolved_subject", type_ids=("X",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)), target_relation="enemy",
        state_guards=(_guard(subject_ref=REF("path_step", step=0), type_id="V", owner="opponent"),),
        effects=capture, invariants=(RuleInvariant("own_anchor_safe"),),
    )
    drop = {tid: ((False,) * 64, (False,) * 64) for tid in ("X", "V", "W")}
    return RuleSet(
        board_size=8, piece_types=(k, x, v, w), initial_position=tuple(tuple(row) for row in rows),
        drop_allowed=drop, semantic_actions=(source, target, empty, unresolved),
    )


def _position(engine, *, target_type="V", source=10, target=11, sibling=False):
    board = list(engine._initial_position().board)
    board[source] = Piece(0, "X", "X")
    board[target] = Piece(1, target_type, target_type)
    if sibling:
        board[63] = Piece(1, "V", "V")
    return replace(engine._initial_position(), board=tuple(board))


def test_action_bound_subject_source_target_empty_and_unresolved():
    engine = semantic_engine_for(compile_semantic_ruleset(_generic_ruleset()))
    p = _position(engine)
    names = {a.pattern_id for a in engine.legal_actions(p)}
    assert any("opaque_source_bound" in name for name in names)
    assert any("opaque_target_bound" in name for name in names)
    assert not any("opaque_empty_subject" in name for name in names)
    assert not any("opaque_unresolved_subject" in name for name in names)

    sibling = _position(engine, target_type="W", source=9, target=10, sibling=True)
    assert not any("opaque_source_bound" in a.pattern_id for a in engine.legal_actions(sibling))
    assert not engine.is_square_attacked(sibling, 10, 0)
    assert engine.is_square_attacked(p, 11, 0)


def test_action_bound_target_only_inspects_target_occupant():
    engine = semantic_engine_for(compile_semantic_ruleset(_generic_ruleset()))
    p = _position(engine, target_type="W", sibling=True)
    assert not any("opaque_target_bound" in a.pattern_id for a in engine.legal_actions(p))
    p = _position(engine, target_type="V", sibling=True)
    assert any("opaque_target_bound" in a.pattern_id for a in engine.legal_actions(p))


def test_action_bound_schema_round_trip_and_fingerprint_contract():
    rules = _generic_ruleset()
    payload = ruleset_to_dict(rules)
    guards = payload["semantic_actions"][0]["state_guards"]
    assert guards[0]["subject_ref"]["kind"] == "source"
    old_payload = dict(payload)
    old_payload["semantic_actions"] = [dict(action) for action in payload["semantic_actions"]]
    old_payload["semantic_actions"][0]["state_guards"] = [dict(guards[0])]
    old_payload["semantic_actions"][0]["state_guards"][0].pop("subject_ref")
    restored = ruleset_from_dict(payload)
    assert restored == rules
    assert compute_fingerprint(restored) == compute_fingerprint(rules)
    assert compute_fingerprint(ruleset_from_dict(old_payload)) != compute_fingerprint(rules)
    metadata_only = replace(rules, metadata={"audit": "different"})
    assert compute_fingerprint(metadata_only) == compute_fingerprint(rules)
    with pytest.raises(ValueError):
        bad = dict(payload)
        bad["semantic_actions"] = [dict(action) for action in payload["semantic_actions"]]
        bad["semantic_actions"][0]["state_guards"] = [dict(guards[0])]
        bad["semantic_actions"][0]["state_guards"][0]["subject_ref"] = "source"
        ruleset_from_dict(bad)


def test_action_bound_compiled_ir_and_native_fail_closed():
    semantic = compile_semantic_ruleset(_generic_ruleset())
    pattern = next(p for p in semantic.ir.patterns if p.name == "opaque_source_bound")
    assert pattern.guards[0].subject_ref.kind == "source"
    assert semantic.ir.capabilities.native_executable is False
    with pytest.raises(NativeUnsupportedRuleError, match="subject_ref"):
        build_semantic_compile_payload(semantic)
