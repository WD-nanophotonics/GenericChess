"""Production-owned semantic Standard Shogi RuleSet.

The ordinary movement, promotion, drop, nifu, uchifuzume and repetition
contracts are reproduced here independently of the historical learning/audit
modules.  Nyugyoku is an out-of-band declaration; the separate official
500-move impasse/no-contest procedure remains outside the current product.
"""

from __future__ import annotations

from ..core.coordinates import Square, index_to_square
from ..core.movement import LeapAtom, RayAtom, empty_mobility
from ..core.pieces import Piece, PieceType
from ..generation.drop_derivation import derive_drop_mask
from .schema import (
    RuleActionEffect,
    RuleDeclaration,
    RuleDeclarationOutcomeBand,
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
    RuleWeightedMaterialMetric,
)


N = 9
STANDARD_SHOGI_NYUGYOKU_SUPPORTED = True


def _king_atoms():
    return tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if df or dr
    )


def _gold_atoms():
    return (
        LeapAtom((0, 1)), LeapAtom((-1, 1)), LeapAtom((1, 1)),
        LeapAtom((-1, 0)), LeapAtom((1, 0)), LeapAtom((0, -1)),
    )


_GOLD = _gold_atoms()


def _bishop_rays():
    return (RayAtom((-1, -1)), RayAtom((-1, 1)), RayAtom((1, -1)), RayAtom((1, 1)))


def _rook_rays():
    return (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))


def _bishop_horse():
    return _bishop_rays() + (LeapAtom((0, 1)), LeapAtom((0, -1)), LeapAtom((1, 0)), LeapAtom((-1, 0)))


def _rook_dragon():
    return _rook_rays() + (LeapAtom((-1, -1)), LeapAtom((-1, 1)), LeapAtom((1, -1)), LeapAtom((1, 1)))


_ATOMS = {
    "P": (LeapAtom((0, 1)),),
    "L": (RayAtom((0, 1)),),
    "N": (LeapAtom((-1, 2)), LeapAtom((1, 2))),
    "S": (LeapAtom((0, 1)), LeapAtom((-1, 1)), LeapAtom((1, 1)), LeapAtom((-1, -1)), LeapAtom((1, -1))),
    "G": _GOLD,
    "B": _bishop_rays(),
    "R": _rook_rays(),
    "K": _king_atoms(),
    "TP": _GOLD,
    "TL": _GOLD,
    "TN": _GOLD,
    "TS": _GOLD,
    "TB": _bishop_horse(),
    "TR": _rook_dragon(),
}
_PROMOTABLE = ("P", "L", "N", "S", "B", "R")
_PROMOTION_TARGET = {"P": "TP", "L": "TL", "N": "TN", "S": "TS", "B": "TB", "R": "TR"}
_DROPPABLE = ("P", "L", "N", "S", "G", "B", "R")


def _piece_types():
    return tuple(
        PieceType(
            type_id=tid, name=tid, movement_atoms=_ATOMS[tid], is_anchor=tid == "K",
            is_promotable=tid in _PROMOTABLE,
            promotion_target_ids=(_PROMOTION_TARGET[tid],) if tid in _PROMOTABLE else (),
        )
        for tid in ("K", "P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR")
    )


def _initial_rows():
    def piece(tid, owner):
        return Piece(owner=owner, base_type_id=tid, current_type_id=tid)

    rows = [
        tuple(piece(t, 0) for t in ("L", "N", "S", "G", "K", "G", "S", "N", "L")),
    ]
    row = [None] * N
    row[1] = piece("R", 0)
    row[7] = piece("B", 0)
    rows.append(tuple(row))
    rows.append(tuple(piece("P", 0) for _ in range(N)))
    rows.extend((None,) * N for _ in range(3))
    rows.append(tuple(piece("P", 1) for _ in range(N)))
    row = [None] * N
    row[1] = piece("B", 1)
    row[7] = piece("R", 1)
    rows.append(tuple(row))
    rows.append(tuple(piece(t, 1) for t in ("L", "N", "S", "G", "K", "G", "S", "N", "L")))
    return tuple(rows)


def _promotion_data(player):
    zone_ranks = (6, 7, 8) if player == 0 else (0, 1, 2)
    allowed = {}
    forced = {}
    for base in _PROMOTABLE:
        pairs = set()
        forced_squares = set()
        for idx in range(N * N):
            source = index_to_square(idx, N)
            for target in empty_mobility(N, player, source, _ATOMS[base]):
                if target.rank in zone_ranks or source.rank in zone_ranks:
                    pairs.add((source, target))
                    if not empty_mobility(N, player, target, _ATOMS[base]):
                        forced_squares.add(target)
        allowed[base] = frozenset(pairs)
        forced[base] = frozenset(forced_squares)
    return allowed, forced


def _target_ref():
    return RuleSquareRef(kind="target")


def _pawn_drop_pattern():
    target = _target_ref()
    return RuleSemanticAction(
        name="standard_drop_contract", type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"), target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(type_ids=("P",), action_family="drop", target_relation="empty"),
        state_guards=(RuleStateGuard(
            aggregation="count", owner="self", type_ref=RuleTypeRef(kind="action_base"),
            compare_field="base", promoted="no", location="board",
            spatial=RuleSpatialSelector(kind="same_file", refs=(target,)),
            comparison="eq", value=0,
        ),),
        effects=(
            RuleActionEffect("remove_from_hand", piece_type_ref=RuleTypeRef(kind="action_base")),
            RuleActionEffect("place", to_ref=target, piece_type_ref=RuleTypeRef(kind="action_base")),
        ),
        invariants=(RuleInvariant(kind="own_anchor_safe"),),
        postconditions=(RulePostcondition("action_delivers_check"), RulePostcondition("no_legal_reply", max_stratum="S3")),
    )


def _declaration_definitions():
    """Return the certified owner-bound Standard Shogi nyugyoku claims."""
    def declaration(owner: int) -> RuleDeclaration:
        ranks = (6, 7, 8) if owner == 0 else (0, 1, 2)
        zone = tuple((file, rank) for rank in ranks for file in range(N))
        spatial = RuleSpatialSelector("zone", zone_squares=zone)
        return RuleDeclaration(
            declaration_id=f"claim_owner_{owner}",
            owner=owner,
            state_guards=(
                RuleStateGuard(
                    "exists", "self", RuleTypeRef("explicit", "K"),
                    "base", "any", "board", spatial, value=1,
                ),
                RuleStateGuard(
                    "count", "self", RuleTypeRef("any"),
                    "base", "any", "board", spatial,
                    comparison="ge", value=11,
                ),
            ),
            ply_limit=500,
            weighted_metric=RuleWeightedMaterialMetric(
                weights={"K": 0, "P": 1, "L": 1, "N": 1, "S": 1,
                         "G": 1, "B": 5, "R": 5},
                spatial=spatial,
                include_hands=True,
            ),
            outcome_bands=(
                RuleDeclarationOutcomeBand(31, "WIN"),
                RuleDeclarationOutcomeBand(24, "RESTART"),
            ),
        )

    return (declaration(0), declaration(1))


def build_standard_shogi_ruleset() -> RuleSet:
    """Build the certified ordinary Standard Shogi product definition."""
    promotion_allowed = {}
    promotion_forced = {}
    drop_allowed = {}
    for player in (0, 1):
        allowed, forced = _promotion_data(player)
        for base in _PROMOTABLE:
            promotion_allowed.setdefault(base, [None, None])[player] = allowed[base]
            promotion_forced.setdefault(base, [None, None])[player] = forced[base]
        for base in _DROPPABLE:
            drop_allowed.setdefault(base, [None, None])[player] = derive_drop_mask(N, player, _ATOMS[base])
        for base in _PROMOTION_TARGET.values():
            drop_allowed.setdefault(base, [None, None])[player] = (False,) * (N * N)

    return RuleSet(
        schema_version=1, board_size=N, piece_types=_piece_types(), initial_position=_initial_rows(),
        drop_allowed={key: tuple(value) for key, value in drop_allowed.items()},
        promotion_allowed={key: tuple(value) for key, value in promotion_allowed.items()},
        promotion_forced={key: tuple(value) for key, value in promotion_forced.items()},
        repetition_limit=4, repetition_policy="continuous_check_loss", max_ply=512,
        stalemate_result="draw", semantic_actions=(_pawn_drop_pattern(),), semantic_dsl_version=2,
        declarations=_declaration_definitions(),
        metadata={
            "preset": "standard_shogi_semantic",
            "source": "round4_semantic_certification",
            "nyugyoku_supported": STANDARD_SHOGI_NYUGYOKU_SUPPORTED,
            "unsupported_rules": ("standard_shogi_500_move_impasse_no_contest",),
        },
    )
