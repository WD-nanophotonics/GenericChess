"""The built-in, perft-certified Western Chess semantic RuleSet.

This is production data, intentionally independent of the F24F/F24G audit
modules.  The definition is kept explicit so its gameplay fingerprint and
semantic fields remain reviewable and reproducible.
"""

from __future__ import annotations

from ..core.coordinates import Square
from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import Piece, PieceType
from ..rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSet,
    RuleSlotGuard,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTransitionTrigger,
    RuleTypeRef,
)


REF = lambda kind, **kwargs: RuleSquareRef(kind=kind, **kwargs)
BASE = RuleTypeRef(kind="action_base")
EXPLICIT = lambda type_id: RuleTypeRef(kind="explicit", type_id=type_id)


def _leaps(offsets):
    return tuple(LeapAtom(offset) for offset in offsets)


def _rays(directions):
    return tuple(RayAtom(direction) for direction in directions)


def _western_types():
    return (
        PieceType("K", "King", _leaps(
            (df, dr) for df in (-1, 0, 1) for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ), is_anchor=True),
        PieceType("P", "Pawn", (), is_promotable=True,
                  promotion_target_ids=("Q", "R", "B", "N")),
        PieceType("N", "Knight", _leaps((
            (1, 2), (2, 1), (-1, 2), (-2, 1),
            (1, -2), (2, -1), (-1, -2), (-2, -1),
        ))),
        PieceType("B", "Bishop", _rays(((1, 1), (-1, 1), (1, -1), (-1, -1)))),
        PieceType("R", "Rook", _rays(((1, 0), (-1, 0), (0, 1), (0, -1)))),
        PieceType("Q", "Queen", _rays((
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, 1), (1, -1), (-1, -1),
        ))),
    )


def _standard_rows():
    return (
        tuple(Piece(0, tid, tid) for tid in ("R", "N", "B", "Q", "K", "B", "N", "R")),
        tuple(Piece(0, "P", "P") for _ in range(8)),
        (None,) * 8,
        (None,) * 8,
        (None,) * 8,
        (None,) * 8,
        tuple(Piece(1, "P", "P") for _ in range(8)),
        tuple(Piece(1, tid, tid) for tid in ("R", "N", "B", "Q", "K", "B", "N", "R")),
    )


def _promotion_masks():
    owner0 = set()
    owner1 = set()
    for file in range(8):
        for df in (-1, 0, 1):
            if 0 <= file + df < 8:
                owner0.add((Square(file, 6), Square(file + df, 7)))
                owner1.add((Square(file, 1), Square(file + df, 0)))
    return (frozenset(owner0), frozenset(owner1))


def _guard(*, type_ref, subject_ref, spatial, owner="self", value=1,
           comparison="eq", promoted="no"):
    return RuleStateGuard(
        aggregation="count", owner=owner, type_ref=type_ref,
        compare_field="base", promoted=promoted, location="board",
        spatial=spatial, comparison=comparison, value=value,
        subject_ref=subject_ref,
    )


def _exact_ref(file, rank):
    return REF("fixed", square=(file, rank), owner_relative=False)


def _non_pawn_actions():
    actions = []
    for tid, atom_kind in (("K", "leap"), ("N", "leap"), ("B", "ray"),
                           ("R", "ray"), ("Q", "ray")):
        selector_base = dict(
            type_ids=(tid,), action_family="board",
            geometry_kind="leap" if atom_kind == "leap" else "ray",
            replace_all_matching=True,
        )
        path_constraints = (
            (RulePathConstraint("path_clear"),) if atom_kind == "ray" else ()
        )
        actions.append(RuleSemanticAction(
            name=f"{tid.lower()}_quiet", type_ids=(tid,),
            geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind=atom_kind),
            target_relation="empty", composition="replace_legacy",
            replace_selector=RuleReplaceSelector(target_relation="empty", **selector_base),
            path_constraints=path_constraints,
            effects=(RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),),
            invariants=(RuleInvariant("own_anchor_safe"),),
        ))
        actions.append(RuleSemanticAction(
            name=f"{tid.lower()}_capture", type_ids=(tid,),
            geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind=atom_kind),
            target_relation="enemy", composition="replace_legacy",
            replace_selector=RuleReplaceSelector(target_relation="enemy", **selector_base),
            path_constraints=path_constraints,
            effects=(
                RuleActionEffect("remove", square_ref=REF("target"),
                                 disposition="remove_from_game", piece_owner="opponent"),
                RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
            ),
            invariants=(RuleInvariant("own_anchor_safe"),),
        ))
    return actions


def _pawn_actions():
    ep = (RuleAuxState("ep_target", "square_or_none", "global", "expire_next_turn", None),)
    start = _guard(
        type_ref=BASE, subject_ref=REF("source"),
        spatial=RuleSpatialSelector(kind="same_rank", refs=(REF("fixed", square=(0, 1)),)),
    )
    one = RuleSemanticAction(
        name="pawn_one_step", type_ids=("P",),
        geometry=RuleGeometrySpec(kind="ray", direction=(0, 1), min_steps=1, max_steps=1),
        target_relation="empty", effects=(
            RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
        ), invariants=(RuleInvariant("own_anchor_safe"),),
        promotion_mode="inherit_compiled_masks",
    )
    double = RuleSemanticAction(
        name="pawn_double_step", type_ids=("P",),
        geometry=RuleGeometrySpec(kind="ray", direction=(0, 1), min_steps=2, max_steps=2),
        target_relation="empty", path_constraints=(RulePathConstraint("path_clear"),),
        state_guards=(start,), aux_state=ep, effects=(
            RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
            RuleActionEffect("set_token", slot_name="ep_target", square_ref=REF("path_step", step=0)),
        ), invariants=(RuleInvariant("own_anchor_safe"),),
    )
    actions = [one, double]
    for name, offset in (("right", (1, 1)), ("left", (-1, 1))):
        actions.append(RuleSemanticAction(
            name=f"pawn_capture_{name}", type_ids=("P",),
            geometry=RuleGeometrySpec(kind="leap", offset=offset),
            target_relation="enemy", effects=(
                RuleActionEffect("remove", square_ref=REF("target"),
                                 disposition="remove_from_game", piece_owner="opponent"),
                RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
            ), invariants=(RuleInvariant("own_anchor_safe"),),
            promotion_mode="inherit_compiled_masks",
        ))
    for name, offset in (("right", (1, 1)), ("left", (-1, 1))):
        victim = REF("offset_from_target", offset=(0, -1))
        actions.append(RuleSemanticAction(
            name=f"en_passant_{name}", type_ids=("P",),
            geometry=RuleGeometrySpec(kind="leap", offset=offset),
            target_relation="empty", aux_state=ep,
            slot_guards=(RuleSlotGuard(slot_name="ep_target", square_ref=REF("target")),),
            state_guards=(_guard(type_ref=EXPLICIT("P"), owner="opponent", subject_ref=victim,
                                 spatial=RuleSpatialSelector(kind="exact", refs=(victim,))),),
            effects=(
                RuleActionEffect("remove", square_ref=victim,
                                 disposition="remove_from_game", piece_owner="opponent",
                                 piece_type_ref=EXPLICIT("P")),
                RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
                RuleActionEffect("clear_token", slot_name="ep_target"),
            ), invariants=(RuleInvariant("own_anchor_safe"),),
        ))
    return actions


def _castle_action(name, source, target, rook_source, rook_target, slot_name,
                   extra_empty=None, triggers=()):
    source_ref = REF("source")
    rook_ref = REF("offset_from_source", offset=(rook_source[0] - source[0], 0),
                    owner_relative=False)
    guards = [
        _guard(type_ref=EXPLICIT("K"), subject_ref=source_ref,
               spatial=RuleSpatialSelector(kind="exact", refs=(_exact_ref(*source),))),
        _guard(type_ref=EXPLICIT("R"), subject_ref=rook_ref,
               spatial=RuleSpatialSelector(kind="exact", refs=(_exact_ref(*rook_source),))),
    ]
    if extra_empty is not None:
        guards.append(_guard(type_ref=RuleTypeRef(kind="any"), owner="any", promoted="any",
                             subject_ref=_exact_ref(*extra_empty),
                             spatial=RuleSpatialSelector(kind="exact", refs=(_exact_ref(*extra_empty),)),
                             value=0))
    direction = 1 if target[0] > source[0] else -1
    return RuleSemanticAction(
        name=name, type_ids=("K",),
        geometry=RuleGeometrySpec(kind="ray", direction=(direction, 0),
                                  min_steps=2, max_steps=2, owner_relative=False),
        target_relation="empty", path_constraints=(RulePathConstraint("path_clear"),),
        state_guards=tuple(guards), slot_guards=(RuleSlotGuard(slot_name=slot_name, value=1),),
        aux_state=tuple(RuleAuxState(slot, "bool", "global", "persistent", 1)
                        for slot in ("w_ks", "w_qs", "b_ks", "b_qs")),
        effects=(
            RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
            RuleActionEffect("move", from_ref=_exact_ref(*rook_source), to_ref=_exact_ref(*rook_target),
                             piece_owner="self", piece_type_ref=EXPLICIT("R")),
            RuleActionEffect("clear_right", slot_name=slot_name),
        ),
        invariants=(
            RuleInvariant("own_anchor_safe"),
            RuleInvariant("squares_not_attacked", square_refs=(
                REF("source"), REF("path_step", step=0), REF("target"),
            )),
        ), triggers=triggers,
    )


def build_western_chess_ruleset() -> RuleSet:
    """Build the canonical product Western Chess semantic RuleSet."""
    triggers = tuple(
        trigger
        for slot, king, rook in (
            ("w_ks", (4, 0), (7, 0)), ("w_qs", (4, 0), (0, 0)),
            ("b_ks", (4, 7), (7, 7)), ("b_qs", (4, 7), (0, 7)),
        )
        for trigger in (
            RuleTransitionTrigger(slot, "piece_leaves_square", _exact_ref(*king), "any"),
            RuleTransitionTrigger(slot, "piece_leaves_square", _exact_ref(*rook), "any"),
            RuleTransitionTrigger(slot, "piece_removed_from_square", _exact_ref(*rook), "any"),
        )
    )
    castles = [
        _castle_action("castle_w_ks", (4, 0), (6, 0), (7, 0), (5, 0), "w_ks", triggers=triggers),
        _castle_action("castle_w_qs", (4, 0), (2, 0), (0, 0), (3, 0), "w_qs", extra_empty=(1, 0)),
        _castle_action("castle_b_ks", (4, 7), (6, 7), (7, 7), (5, 7), "b_ks"),
        _castle_action("castle_b_qs", (4, 7), (2, 7), (0, 7), (3, 7), "b_qs", extra_empty=(1, 7)),
    ]
    return RuleSet(
        schema_version=1, board_size=8, piece_types=_western_types(),
        initial_position=_standard_rows(),
        drop_allowed={tid: ((False,) * 64, (False,) * 64)
                      for tid in ("P", "N", "B", "R", "Q")},
        promotion_allowed={"P": _promotion_masks()},
        promotion_forced={"P": (
            frozenset(Square(file, 7) for file in range(8)),
            frozenset(Square(file, 0) for file in range(8)),
        )},
        repetition_limit=100000, max_ply=1000, stalemate_result="draw",
        semantic_actions=tuple(_non_pawn_actions() + _pawn_actions() + castles),
        metadata={"fixture": "F24F-western-chess-certification"},
    )

