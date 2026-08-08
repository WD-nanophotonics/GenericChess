"""Frozen specification for Phase 1.9B-2.

These tests intentionally describe behavior not yet implemented at baseline
6d6ddd4. Do not weaken them in the implementation branch.
"""

from __future__ import annotations

import inspect

import pytest

from generic_chess.core.coordinates import Square
from generic_chess.core.position import Position
from generic_chess.rules.compiler import compile_ruleset, compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
)

from rule_semantics_ir_fixtures import castling_ruleset, en_passant_ruleset


def _pattern(ir, pattern_id):
    return next(p for p in ir.patterns if p.pattern_id == pattern_id)


def test_normalized_semantic_ir_preserves_anchor_normal_movement():
    ir = compile_semantic_ruleset(castling_ruleset()).ir
    # K is the anchor in this fixture. AUGMENT castling must not erase ordinary
    # K movement patterns inherited from the legacy rules.
    anchor_legacy = [
        p for p in ir.patterns
        if p.pattern_id.startswith("legacy_") and "K" in p.type_ids
    ]
    assert anchor_legacy, "normalized semantic IR dropped ordinary anchor movement"


def test_semantic_ruleset_has_standalone_generic_support_payload():
    compiled = compile_semantic_ruleset(castling_ruleset())
    assert hasattr(compiled, "support"), (
        "semantic executor support data must be explicit; _legacy_compiled is inspection-only"
    )
    support = compiled.support
    required = {
        "board_size",
        "initial_position",
        "type_metadata",
        "drop_allowed",
        "promotion_allowed",
        "promotion_forced",
        "repetition_limit",
        "max_ply",
        "stalemate_result",
    }
    missing = [name for name in required if not hasattr(support, name)]
    assert not missing, f"semantic support payload missing {missing}"
    # Executability must not depend on the legacy inspection handle.
    assert hasattr(compiled, "_legacy_compiled")


def test_semantic_support_contains_anchor_metadata_without_movement_atoms():
    compiled = compile_semantic_ruleset(castling_ruleset())
    support = compiled.support
    k_meta = support.type_metadata["K"]
    assert k_meta.is_anchor is True
    # Stripped metadata must not recreate high-level movement interpretation.
    assert not hasattr(k_meta, "movement_atoms")


def _absolute_geometry_ruleset():
    base = castling_ruleset()
    absolute = RuleSemanticAction(
        name="absolute_right_step",
        type_ids=("R",),
        geometry=RuleGeometrySpec(
            kind="leap", offset=(1, 0), owner_relative=False
        ),
        target_relation="empty",
        composition="augment",
        effects=(
            RuleActionEffect(
                "move",
                from_ref=base.semantic_actions[0].effects[0].from_ref,
                to_ref=base.semantic_actions[0].effects[0].to_ref,
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    return RuleSet(
        board_size=base.board_size,
        piece_types=base.piece_types,
        initial_position=base.initial_position,
        drop_allowed=base.drop_allowed,
        semantic_actions=(absolute,),
    )


def test_owner_relative_false_geometry_is_not_rotated_for_owner_one():
    ir = compile_semantic_ruleset(_absolute_geometry_ruleset()).ir
    pattern = _pattern(ir, "sem_00_absolute_right_step")
    geo = ir.geometry[pattern.geometry_ids[0]]
    # d8 (file=3, rank=7) -> e8 in absolute +file direction for owner 1 too.
    source = 7 * 8 + 3
    candidates = geometry_candidates(geo, "1", source)
    assert candidates == ((7 * 8 + 4, ()),)


def test_position_declares_canonical_aux_state_field():
    assert "aux_state" in Position.__dataclass_fields__, (
        "legality-affecting semantic auxiliary state must belong to Position"
    )


def test_semantic_position_key_api_accepts_semantic_compiled_ruleset():
    from generic_chess.core import keys

    assert hasattr(keys, "semantic_position_key") or "CompiledSemanticRuleset" in inspect.getsource(keys), (
        "semantic position identity must include aux state without routing through legacy CompiledRuleSet"
    )


def test_s4_semantic_rules_remain_fail_closed_in_b2():
    from rule_semantics_ir_fixtures import uchifuzume_ruleset

    compiled = compile_semantic_ruleset(uchifuzume_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    assert compiled.ir.capabilities.new_ir_core_executable is False
