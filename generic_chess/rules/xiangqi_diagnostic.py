"""Internal single-ply Xiangqi RuleSet for generic semantic diagnostics.

This builder is deliberately not registered as a playable built-in product.
It covers ordinary movement and capture only; WXF history adjudication and an
independent Xiangqi behavior oracle remain outside this diagnostic.
"""

from __future__ import annotations

from ..core.coordinates import BoardShape
from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import Piece, PieceType
from .schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleSquareZoneGuard,
    RuleStateGuard,
    RuleTypeRef,
)


_WIDTH = 9
_HEIGHT = 10
_ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_HORSE = (
    (2, 1), (2, -1), (-2, 1), (-2, -1),
    (1, 2), (1, -2), (-1, 2), (-1, -2),
)
_BACK_RANK = ("R", "H", "E", "A", "G", "A", "E", "H", "R")
_PIECE_NAMES = {
    "G": "General",
    "A": "Advisor",
    "E": "Elephant",
    "H": "Horse",
    "R": "Chariot",
    "C": "Cannon",
    "S": "Soldier",
}


def _movement_atoms():
    return {
        "G": tuple(LeapAtom(offset) for offset in _ORTHOGONAL),
        "A": tuple(LeapAtom(offset) for offset in _DIAGONAL),
        "E": tuple(LeapAtom((2 * df, 2 * dr)) for df, dr in _DIAGONAL),
        "H": tuple(LeapAtom(offset) for offset in _HORSE),
        "R": tuple(RayAtom(direction) for direction in _ORTHOGONAL),
        "C": tuple(RayAtom(direction) for direction in _ORTHOGONAL),
        "S": tuple(LeapAtom(offset) for offset in ((0, 1), (1, 0), (-1, 0))),
    }


def _initial_position():
    rows = [[None] * _WIDTH for _ in range(_HEIGHT)]
    for file, type_id in enumerate(_BACK_RANK):
        rows[0][file] = Piece(0, type_id, type_id)
        rows[9][file] = Piece(1, type_id, type_id)
    for file in (1, 7):
        rows[2][file] = Piece(0, "C", "C")
        rows[7][file] = Piece(1, "C", "C")
    for file in (0, 2, 4, 6, 8):
        rows[3][file] = Piece(0, "S", "S")
        rows[6][file] = Piece(1, "S", "S")
    return tuple(tuple(row) for row in rows)


def _zone_squares(files, ranks):
    return tuple((file, rank) for file in files for rank in ranks)


_PALACE = _zone_squares(range(3, 6), range(3))
_OWN_HALF = _zone_squares(range(_WIDTH), range(5))
_AFTER_RIVER = _zone_squares(range(_WIDTH), range(5, _HEIGHT))


def _zone_guard(ref_kind, squares):
    return RuleSquareZoneGuard(
        square_ref=RuleSquareRef(kind=ref_kind),
        spatial=RuleSpatialSelector(kind="zone", zone_squares=squares),
        relation="inside",
        owner_relative=True,
    )


def _empty_offset_guard(offset):
    ref = RuleSquareRef(
        kind="offset_from_source", offset=offset, owner_relative=True
    )
    return RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef(kind="any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(kind="exact", refs=(ref,)),
        comparison="eq",
        value=0,
        subject_ref=ref,
    )


def _target_anchor_guard():
    target = RuleSquareRef(kind="target")
    return RuleStateGuard(
        aggregation="count",
        owner="opponent",
        type_ref=RuleTypeRef(kind="explicit", type_id="G"),
        compare_field="current",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(kind="exact", refs=(target,)),
        comparison="eq",
        value=1,
        subject_ref=target,
    )


def _move_effects():
    return (
        RuleActionEffect(
            "move", from_ref=RuleSquareRef(kind="source"),
            to_ref=RuleSquareRef(kind="target"),
        ),
    )


def _capture_effects():
    return (
        RuleActionEffect(
            "remove", square_ref=RuleSquareRef(kind="target"),
            disposition="remove_from_game", piece_owner="opponent",
        ),
        RuleActionEffect(
            "move", from_ref=RuleSquareRef(kind="source"),
            to_ref=RuleSquareRef(kind="target"),
        ),
    )


def _replace_selector(type_id, relation, geometry_kind):
    return RuleReplaceSelector(
        type_ids=(type_id,),
        action_family="board",
        target_relation=relation,
        geometry_kind=geometry_kind,
        replace_all_matching=True,
    )


def _move_action(
    name,
    type_id,
    geometry,
    relation,
    *,
    path=(),
    state_guards=(),
    square_zones=(),
    composition="replace_legacy",
):
    return RuleSemanticAction(
        name=name,
        type_ids=(type_id,),
        geometry=geometry,
        target_relation=relation,
        composition=composition,
        replace_selector=(
            _replace_selector(
                type_id, relation,
                "ray" if geometry.kind == "legacy_atoms" and geometry.atom_kind == "ray"
                else "leap" if geometry.kind == "legacy_atoms" and geometry.atom_kind == "leap"
                else geometry.kind,
            )
            if composition == "replace_legacy" else None
        ),
        path_constraints=path,
        state_guards=state_guards,
        effects=_move_effects() if relation == "empty" else _capture_effects(),
        invariants=(RuleInvariant("own_anchor_safe"),),
        square_zone_guards=square_zones,
    )


def _simple_piece_actions(type_id, geometry, *, zones=(), path=()):
    return tuple(
        _move_action(
            f"{type_id.lower()}_{relation}", type_id, geometry, relation,
            path=path,
            square_zones=zones,
        )
        for relation in ("empty", "enemy")
    )


def _leap_action_pair(type_id, name, offset, *, state_guards=(), zones=()):
    geometry = RuleGeometrySpec(kind="leap", offset=offset, owner_relative=True)
    return _simple_piece_actions(
        type_id, geometry, zones=zones, path=(),
    ) if not state_guards else tuple(
        _move_action(
            f"{name}_{relation}", type_id, geometry, relation,
            state_guards=state_guards,
            square_zones=zones,
        )
        for relation in ("empty", "enemy")
    )


def _semantic_actions():
    actions = []

    actions.extend(_simple_piece_actions(
        "G",
        RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        zones=(_zone_guard("source", _PALACE), _zone_guard("target", _PALACE)),
    ))
    actions.append(_move_action(
        "general_facing_capture",
        "G",
        RuleGeometrySpec(kind="ray", direction=(0, 1), owner_relative=True),
        "enemy",
        path=(RulePathConstraint("path_clear"),),
        state_guards=(_target_anchor_guard(),),
        square_zones=(_zone_guard("source", _PALACE),),
        composition="augment",
    ))

    actions.extend(_simple_piece_actions(
        "A",
        RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        zones=(_zone_guard("source", _PALACE), _zone_guard("target", _PALACE)),
    ))

    for df, dr in _DIAGONAL:
        eye = (df, dr)
        zones = (_zone_guard("source", _OWN_HALF), _zone_guard("target", _OWN_HALF))
        actions.extend(_leap_action_pair(
            "E", f"elephant_{df}_{dr}", (2 * df, 2 * dr),
            state_guards=(_empty_offset_guard(eye),),
            zones=zones,
        ))

    for df, dr in _HORSE:
        leg = (df // 2, 0) if abs(df) == 2 else (0, dr // 2)
        actions.extend(_leap_action_pair(
            "H", f"horse_{df}_{dr}", (df, dr),
            state_guards=(_empty_offset_guard(leg),),
        ))

    ray = RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray")
    actions.extend(_simple_piece_actions(
        "R", ray, path=(RulePathConstraint("path_clear"),)
    ))
    actions.append(_move_action(
        "cannon_quiet",
        "C",
        ray,
        "empty",
        path=(RulePathConstraint("path_clear"),),
    ))
    actions.append(_move_action(
        "cannon_capture_one_screen",
        "C",
        ray,
        "enemy",
        path=(RulePathConstraint("path_count_eq", count=1),),
    ))

    forward = RuleGeometrySpec(
        kind="leap", offset=(0, 1), owner_relative=True
    )
    actions.extend(_simple_piece_actions("S", forward))
    for df in (-1, 1):
        lateral = RuleGeometrySpec(
            kind="leap", offset=(df, 0), owner_relative=True
        )
        actions.extend(_simple_piece_actions(
            "S", lateral,
            zones=(_zone_guard("source", _AFTER_RIVER),),
        ))

    return tuple(actions)


def build_xiangqi_diagnostic_ruleset() -> RuleSet:
    """Build an internal, ordinary-movement-only standard Xiangqi RuleSet."""
    atoms = _movement_atoms()
    piece_types = tuple(
        PieceType(
            type_id=type_id,
            name=_PIECE_NAMES[type_id],
            movement_atoms=atoms[type_id],
            is_anchor=(type_id == "G"),
        )
        for type_id in _PIECE_NAMES
    )
    no_drops = (False,) * (_WIDTH * _HEIGHT)
    return RuleSet(
        board_size=None,
        board_width=_WIDTH,
        board_height=_HEIGHT,
        piece_types=piece_types,
        initial_position=_initial_position(),
        drop_allowed={
            type_id: (no_drops, no_drops)
            for type_id in _PIECE_NAMES
            if type_id != "G"
        },
        semantic_actions=_semantic_actions(),
        capture_disposition="remove_from_game",
        stalemate_result="loss",
        metadata={"diagnostic_scope": "single-ply movement only"},
    )
