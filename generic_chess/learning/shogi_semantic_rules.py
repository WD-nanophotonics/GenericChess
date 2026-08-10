"""Canonical Standard Shogi definition lowered through the generic Semantic DSL.

This certification fixture deliberately keeps the historical schema-v1
definition available while replacing only the static pawn-drop pattern with a
generic state guard plus the bounded S4 postcondition.  The executor and Core
remain unaware of the game definition.
"""

from __future__ import annotations

from dataclasses import replace

from ..rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RulePostcondition,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
)
from .shogi_rules import build_shogi_ruleset


def _target_ref() -> RuleSquareRef:
    return RuleSquareRef(kind="target")


def _pawn_drop_pattern() -> RuleSemanticAction:
    """Generic drop contract for one base type with two independent guards."""
    return RuleSemanticAction(
        name="standard_drop_contract",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("P",),
            action_family="drop",
            target_relation="empty",
        ),
        state_guards=(
            RuleStateGuard(
                aggregation="count",
                owner="self",
                type_ref=RuleTypeRef(kind="action_base"),
                compare_field="base",
                promoted="no",
                location="board",
                spatial=RuleSpatialSelector(
                    kind="same_file", refs=(_target_ref(),)
                ),
                comparison="eq",
                value=0,
            ),
        ),
        effects=(
            RuleActionEffect(
                "remove_from_hand",
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
            RuleActionEffect(
                "place",
                to_ref=_target_ref(),
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
        ),
        invariants=(RuleInvariant(kind="own_anchor_safe"),),
        postconditions=(
            RulePostcondition("action_delivers_check"),
            RulePostcondition("no_legal_reply", max_stratum="S3"),
        ),
    )


def build_semantic_shogi_ruleset() -> RuleSet:
    """Return Standard Shogi with its benchmark-blocking rules lowered generically."""
    base = build_shogi_ruleset(corrected_promotion=True)
    return replace(
        base,
        semantic_actions=(_pawn_drop_pattern(),),
        semantic_dsl_version=2,
        metadata={
            "preset": "standard_shogi_semantic",
            "source": "round4_semantic_certification",
        },
    )
