"""Phase 1.9B-1.5 v2 semantic-DSL stress fixtures (shared by tests)."""

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RulePostcondition,
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


def _king_type():
    return PieceType(
        "K",
        "K",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )


def _ray_type(tid, atoms):
    return PieceType(tid, tid, atoms)


def _own_anchor():
    return (RuleInvariant("own_anchor_safe"),)


def _semantic_ruleset(piece_types, actions, n=8, rows=None):
    if rows is None:
        rows = []
        for rank in range(n):
            row = []
            for file in range(n):
                if (rank, file) == (0, 0):
                    row.append(Piece(0, "K", "K"))
                elif (rank, file) == (n - 1, n - 1):
                    row.append(Piece(1, "K", "K"))
                else:
                    row.append(None)
            rows.append(tuple(row))
    drop_allowed = {}
    for pt in piece_types:
        if not pt.is_anchor:
            drop_allowed[pt.type_id] = ((False,) * (n * n), (False,) * (n * n))
    return RuleSet(
        board_size=n,
        piece_types=piece_types,
        initial_position=tuple(rows),
        drop_allowed=drop_allowed,
        semantic_actions=actions,
    )


def _ref(kind, **kwargs):
    return RuleSquareRef(kind=kind, **kwargs)


def cannon_ruleset():
    cannon = _ray_type(
        "C",
        (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))),
    )
    quiet = RuleSemanticAction(
        name="cannon_quiet",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="empty",
        composition="augment",
        path_constraints=(RulePathConstraint("path_clear"),),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=_ref("source"),
                to_ref=_ref("target"),
            ),
        ),
        invariants=_own_anchor(),
    )
    capture = RuleSemanticAction(
        name="cannon_capture",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("C",),
            action_family="board",
            target_relation="enemy",
            geometry_kind="ray",
            replace_all_matching=True,
        ),
        path_constraints=(RulePathConstraint("path_count_eq", count=1),),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=_ref("target"),
                disposition="capture_to_hand",
            ),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
        ),
        invariants=_own_anchor(),
    )
    return _semantic_ruleset((_king_type(), cannon), (quiet, capture))


def castling_ruleset():
    n = 8
    rows = []
    for rank in range(n):
        row = []
        for file in range(n):
            if rank == 0 and file == 4:
                row.append(Piece(0, "K", "K"))
            elif rank == 0 and file == 7:
                row.append(Piece(0, "R", "R"))
            elif rank == n - 1 and file == 3:
                row.append(Piece(1, "K", "K"))
            elif rank == n - 1 and file == 0:
                row.append(Piece(1, "R", "R"))
            else:
                row.append(None)
        rows.append(tuple(row))
    right = RuleAuxState(
        name="king_right", value_kind="bool", scope="per_owner",
        lifetime="persistent", initial=1,
    )
    castle = RuleSemanticAction(
        name="king_side_shift",
        type_ids=("K",),
        geometry=RuleGeometrySpec(
            kind="ray", direction=(1, 0), min_steps=2, max_steps=2, owner_relative=True
        ),
        target_relation="empty",
        composition="augment",
        path_constraints=(RulePathConstraint("path_clear"),),
        slot_guards=(RuleSlotGuard(slot_name="king_right", comparison="eq", value=1),),
        aux_state=(right,),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=_ref("source"),
                to_ref=_ref("target"),
                piece_owner="self",
            ),
            RuleActionEffect(
                "move",
                from_ref=_ref("offset_from_source", offset=(3, 0), owner_relative=True),
                to_ref=_ref("offset_from_source", offset=(1, 0), owner_relative=True),
                piece_owner="self",
                piece_type_ref=RuleTypeRef(kind="explicit", type_id="R"),
            ),
            RuleActionEffect("clear_right", slot_name="king_right"),
        ),
        invariants=(
            RuleInvariant(
                "squares_not_attacked",
                (
                    _ref("source"),
                    _ref("path_step", step=0),
                    _ref("target"),
                ),
            ),
        ),
        triggers=(
            RuleTransitionTrigger(
                slot_name="king_right",
                event="piece_leaves_square",
                square_ref=_ref("fixed", square=(4, 0)),
                owner="self",
            ),
            RuleTransitionTrigger(
                slot_name="king_right",
                event="piece_leaves_square",
                square_ref=_ref("fixed", square=(7, 0)),
                owner="self",
            ),
            RuleTransitionTrigger(
                slot_name="king_right",
                event="piece_removed_from_square",
                square_ref=_ref("fixed", square=(7, 0)),
                owner="self",
            ),
        ),
    )
    king = _king_type()
    rook = _ray_type(
        "R",
        (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))),
    )
    return _semantic_ruleset((king, rook), (castle,), n=n, rows=rows)


def en_passant_ruleset():
    pawn = _ray_type("P", (RayAtom((0, 1)),))
    token = RuleAuxState(
        name="ep_token", value_kind="square_or_none", scope="global",
        lifetime="expire_next_turn", initial=None,
    )
    creation = RuleSemanticAction(
        name="double_step_creates_token",
        type_ids=("P",),
        geometry=RuleGeometrySpec(
            kind="ray", direction=(0, 1), min_steps=2, max_steps=2, owner_relative=True
        ),
        target_relation="empty",
        composition="augment",
        path_constraints=(RulePathConstraint("path_clear"),),
        aux_state=(token,),
        effects=(
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
            RuleActionEffect("set_token", slot_name="ep_token", square_ref=_ref("path_step", step=0)),
        ),
        invariants=_own_anchor(),
    )
    capture = RuleSemanticAction(
        name="token_adjacent_capture_removes_off_target",
        type_ids=("P",),
        geometry=RuleGeometrySpec(
            kind="leap", offset=(1, 1), owner_relative=True
        ),
        target_relation="empty",
        composition="augment",
        slot_guards=(
            RuleSlotGuard(slot_name="ep_token", comparison="eq", square_ref=_ref("target")),
        ),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=_ref("offset_from_target", offset=(0, -1), owner_relative=True),
                disposition="capture_to_hand",
            ),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
            RuleActionEffect("clear_token", slot_name="ep_token"),
        ),
        invariants=_own_anchor(),
    )
    return _semantic_ruleset((_king_type(), pawn), (creation, capture))


def nifu_ruleset():
    pawn = _ray_type("P", (RayAtom((0, 1)),))
    guard = RuleStateGuard(
        aggregation="count",
        owner="self",
        type_ref=RuleTypeRef(kind="action_base"),
        compare_field="base",
        promoted="no",
        location="board",
        spatial=RuleSpatialSelector(kind="same_file", refs=(_ref("target"),)),
        comparison="eq",
        value=0,
    )
    action = RuleSemanticAction(
        name="drop_file_occupancy_guard",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("P",), action_family="drop", target_relation="empty"
        ),
        state_guards=(guard,),
        effects=(
            RuleActionEffect(
                "remove_from_hand",
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
            RuleActionEffect(
                "place",
                to_ref=_ref("target"),
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
        ),
        invariants=_own_anchor(),
    )
    return _semantic_ruleset((_king_type(), pawn), (action,))


def uchifuzume_ruleset():
    pawn = _ray_type("P", (RayAtom((0, 1)),))
    action = RuleSemanticAction(
        name="drop_no_legal_reply_forbidden",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("P",), action_family="drop", target_relation="empty"
        ),
        effects=(
            RuleActionEffect(
                "remove_from_hand",
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
            RuleActionEffect(
                "place",
                to_ref=_ref("target"),
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
        ),
        invariants=_own_anchor(),
        postconditions=(
            RulePostcondition("opponent_checked"),
            RulePostcondition("no_legal_reply", max_stratum="S3"),
        ),
    )
    return _semantic_ruleset((_king_type(), pawn), (action,))


def weird_rulesets():
    ray = _ray_type(
        "R",
        (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))),
    )
    promoted = _ray_type("TP", (LeapAtom((1, 0)),))
    weird_ray = RuleSemanticAction(
        name="ray_quiet_zero_capture_two_screens",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("R",), action_family="board", target_relation="enemy",
            geometry_kind="ray", replace_all_matching=True,
        ),
        path_constraints=(RulePathConstraint("path_count_eq", count=2),),
        effects=(
            RuleActionEffect("remove", square_ref=_ref("target"), disposition="capture_to_hand"),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
        ),
        invariants=_own_anchor(),
    )
    zone_drop = RuleSemanticAction(
        name="drop_zone_capacity_guard",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("R",), action_family="drop", target_relation="empty"
        ),
        state_guards=(
            RuleStateGuard(
                aggregation="count",
                owner="self",
                type_ref=RuleTypeRef(kind="action_base"),
                compare_field="current",
                promoted="any",
                location="board",
                spatial=RuleSpatialSelector(
                    kind="zone", zone_squares=((0, 0), (0, 1), (0, 2))
                ),
                comparison="lt",
                value=3,
            ),
        ),
        effects=(
            RuleActionEffect(
                "remove_from_hand",
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
            RuleActionEffect(
                "place",
                to_ref=_ref("target"),
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
        ),
        invariants=_own_anchor(),
    )
    temp_right = RuleSemanticAction(
        name="promotion_grants_one_turn_right",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 1)),
        target_relation="any",
        composition="augment",
        aux_state=(
            RuleAuxState(
                name="temp_right", value_kind="bool", scope="global",
                lifetime="expire_next_turn", initial=0,
            ),
        ),
        effects=(
            RuleActionEffect(
                "set_current_type",
                square_ref=_ref("target"),
                type_ref=RuleTypeRef(kind="explicit", type_id="TP"),
            ),
            RuleActionEffect("set_bool", slot_name="temp_right", value=1),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
        ),
        invariants=_own_anchor(),
    )
    compound = RuleSemanticAction(
        name="move_and_shift_adjacent_friendly",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 1)),
        target_relation="empty",
        composition="augment",
        effects=(
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
            RuleActionEffect(
                "shift",
                from_ref=_ref("offset_from_source", offset=(0, 1)),
                to_ref=_ref("offset_from_source", offset=(0, 2)),
                piece_owner="self",
            ),
        ),
        invariants=_own_anchor(),
    )
    restricted = RuleSemanticAction(
        name="action_class_no_immediate_mate",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("R",), action_family="board", target_relation="enemy",
            geometry_kind="ray", replace_all_matching=True,
        ),
        effects=(
            RuleActionEffect("remove", square_ref=_ref("target"), disposition="capture_to_hand"),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
        ),
        invariants=_own_anchor(),
        postconditions=(
            RulePostcondition("opponent_checked"),
            RulePostcondition("no_legal_reply", max_stratum="S3"),
        ),
    )
    return (
        _semantic_ruleset((_king_type(), ray), (weird_ray,)),
        _semantic_ruleset((_king_type(), ray), (zone_drop,)),
        _semantic_ruleset((_king_type(), ray, promoted), (temp_right,)),
        _semantic_ruleset((_king_type(), ray), (compound,)),
        _semantic_ruleset((_king_type(), ray), (restricted,)),
    )


STRESS_GROUPS = {
    "cannon": cannon_ruleset,
    "castling": castling_ruleset,
    "en_passant": en_passant_ruleset,
    "nifu": nifu_ruleset,
    "uchifuzume": uchifuzume_ruleset,
}
