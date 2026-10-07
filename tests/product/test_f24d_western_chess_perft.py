"""F24D preflight for a certification-only Western Chess RuleSet.

The full perft certification is intentionally not started when the generic
DSL cannot bind a starting-rank predicate to the action source.
"""

from dataclasses import replace

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleSemanticAction,
    RuleSet,
    RuleSlotGuard,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTransitionTrigger,
    RuleTypeRef,
)


N = 8
REF = lambda kind, **kwargs: RuleSquareRef(kind=kind, **kwargs)
BASE = RuleTypeRef(kind="action_base")


def western_preflight_ruleset(*, source_bound=False):
    """Build the smallest complete-shape Western ruleset for DSL auditing."""
    king = PieceType(
        "K", "K",
        tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)),
        is_anchor=True,
    )
    pawn = PieceType("P", "P", (), is_promotable=True, promotion_target_ids=("Q", "R", "B", "N"))
    knight = PieceType("N", "N", tuple(LeapAtom(o) for o in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))))
    bishop = PieceType("B", "B", tuple(RayAtom(d) for d in ((1, 1), (-1, 1), (1, -1), (-1, -1))))
    rook = PieceType("R", "R", tuple(RayAtom(d) for d in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    queen = PieceType("Q", "Q", tuple(RayAtom(d) for d in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))))

    rights = tuple(RuleAuxState(n, "bool", "global", "persistent", 1) for n in ("w_ks", "w_qs", "b_ks", "b_qs"))
    ep = RuleAuxState("ep_target", "square_or_none", "global", "expire_next_turn", None)
    start_guard = RuleStateGuard(
        aggregation="count", owner="self", type_ref=BASE, compare_field="base",
        promoted="no", location="board",
        spatial=RuleSpatialSelector(kind="same_rank", refs=(REF("fixed", square=(0, 1)),)),
        comparison="ge", value=1,
        subject_ref=REF("source") if source_bound else None,
    )
    double = RuleSemanticAction(
        name="pawn_double_start_rank_probe", type_ids=("P",),
        geometry=RuleGeometrySpec(kind="ray", direction=(0, 1), min_steps=2, max_steps=2),
        target_relation="empty", composition="augment",
        path_constraints=(RulePathConstraint("path_clear"),), state_guards=(start_guard,),
        effects=(RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
                 RuleActionEffect("set_token", slot_name="ep_target", square_ref=REF("path_step", step=0))),
        aux_state=rights + (ep,), invariants=(RuleInvariant("own_anchor_safe"),),
    )
    castle_source_guard = RuleStateGuard(
        aggregation="count", owner="self", type_ref=RuleTypeRef(kind="explicit", type_id="K"),
        compare_field="base", promoted="no", location="board",
        spatial=RuleSpatialSelector(
            kind="exact", refs=(REF("fixed", square=(4, 0), owner_relative=False),)
        ),
        comparison="eq", value=1, subject_ref=REF("source"),
    )
    castle = RuleSemanticAction(
        name="castle_probe", type_ids=("K",),
        geometry=RuleGeometrySpec(kind="ray", direction=(1, 0), min_steps=2, max_steps=2, owner_relative=False),
        target_relation="empty", composition="augment",
        path_constraints=(RulePathConstraint("path_clear"),),
        state_guards=(castle_source_guard,) if source_bound else (),
        slot_guards=(RuleSlotGuard(slot_name="w_ks", value=1),),
        effects=(RuleActionEffect("move", from_ref=REF("source"), to_ref=REF("target")),
                 RuleActionEffect("move", from_ref=REF("fixed", square=(7, 0), owner_relative=False), to_ref=REF("fixed", square=(5, 0), owner_relative=False)),
                 RuleActionEffect("clear_right", slot_name="w_ks")),
        aux_state=rights + (ep,),
        invariants=(RuleInvariant("own_anchor_safe"), RuleInvariant("squares_not_attacked", square_refs=tuple(REF("fixed", square=s, owner_relative=False) for s in ((4, 0), (5, 0), (6, 0))))),
        triggers=(RuleTransitionTrigger("w_ks", "piece_leaves_square", REF("fixed", square=(4, 0), owner_relative=False), "any"),),
    )
    rows = [[None] * N for _ in range(N)]
    rows[0][4] = Piece(0, "K", "K")
    rows[7][4] = Piece(1, "K", "K")
    drop = {tid: ((False,) * 64, (False,) * 64) for tid in ("P", "N", "B", "R", "Q")}
    return RuleSet(
        board_size=N, piece_types=(king, pawn, knight, bishop, rook, queen),
        initial_position=tuple(tuple(row) for row in rows), drop_allowed=drop,
        promotion_allowed={"P": (frozenset(), frozenset())},
        promotion_forced={"P": (frozenset(), frozenset())},
        semantic_actions=(double, castle), metadata={"fixture": "F24D-preflight"},
    )


def test_f24d_preflight_compiles_castling_en_passant_and_promotion_shapes():
    semantic = compile_semantic_ruleset(western_preflight_ruleset())
    engine = semantic_engine_for(semantic)
    assert engine is not None
    assert any(p.name == "castle_probe" for p in semantic.ir.patterns)
    assert any(slot.value_kind == "square_or_none" for slot in semantic.ir.aux_slots)
    assert semantic.support.promotion_allowed["P"] == (frozenset(), frozenset())


def test_f24d_preflight_records_source_binding_gap_before_perft():
    semantic = compile_semantic_ruleset(western_preflight_ruleset())
    engine = semantic_engine_for(semantic)
    board = list(engine._initial_position().board)
    board[4] = Piece(0, "K", "K")
    board[60] = Piece(1, "K", "K")
    board[8] = Piece(0, "P", "P")       # a2: a real starting-rank pawn
    board[27] = Piece(0, "P", "P")       # d4: must not double-step
    position = replace(engine._initial_position(), board=tuple(board))
    leaked = [a for a in engine.legal_actions(position) if a.source == 27 and a.target == 43]
    assert leaked, "current same-rank guard is not source-bound; F24E is required"


def _pawn_position(engine, side, *, start=True, non_start=False, blocked=False):
    board = [None] * 64
    board[4] = Piece(0, "K", "K")
    board[60] = Piece(1, "K", "K")
    if side == 0:
        if start:
            board[8] = Piece(0, "P", "P")
            if blocked:
                board[16] = Piece(0, "N", "N")
        if non_start:
            board[27] = Piece(0, "P", "P")
    else:
        if start:
            board[48] = Piece(1, "P", "P")
            if blocked:
                board[40] = Piece(1, "N", "N")
        if non_start:
            board[35] = Piece(1, "P", "P")
    return replace(engine._initial_position(), board=tuple(board), side_to_move=side)


def _has_double(engine, position, source, target):
    return any(a.source == source and a.target == target for a in engine.legal_actions(position))


def test_f24e_source_bound_pawn_matrix_and_owner_mirror():
    semantic = compile_semantic_ruleset(western_preflight_ruleset(source_bound=True))
    engine = semantic_engine_for(semantic)
    assert _has_double(engine, _pawn_position(engine, 0, start=True), 8, 24)
    assert not _has_double(engine, _pawn_position(engine, 0, start=True, blocked=True), 8, 24)
    assert not _has_double(engine, _pawn_position(engine, 0, non_start=True), 27, 43)
    assert not _has_double(engine, _pawn_position(engine, 0, start=True, non_start=True), 27, 43)
    assert _has_double(engine, _pawn_position(engine, 1, start=True), 48, 32)
    assert not _has_double(engine, _pawn_position(engine, 1, start=True, blocked=True), 48, 32)
    assert not _has_double(engine, _pawn_position(engine, 1, non_start=True), 35, 19)
    assert not _has_double(engine, _pawn_position(engine, 1, start=True, non_start=True), 35, 19)


def test_f24e_castling_preflight_binds_king_guard_to_action_source():
    semantic = compile_semantic_ruleset(western_preflight_ruleset(source_bound=True))
    castle = next(pattern for pattern in semantic.ir.patterns if pattern.name == "castle_probe")
    assert castle.guards[0].subject_ref.kind == "source"
