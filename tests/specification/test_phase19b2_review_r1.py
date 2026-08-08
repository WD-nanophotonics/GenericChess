"""Frozen independent-review regressions for Phase 1.9B-2 R1.

These tests were authored from an independent source review of impl 6a7bd95.
Do not weaken them to make the implementation pass.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


def _engine(builder):
    from generic_chess.core.semantic_executor import SemanticEngine
    from generic_chess.rules.compiler import compile_semantic_ruleset

    return SemanticEngine(compile_semantic_ruleset(builder()))


def _idx(support, file, rank):
    return rank * support.board_size + file


def _position(support, pieces, side=0, hands=None, aux_state=()):
    from generic_chess.core.position import Hands, Position

    board = [None] * (support.board_size * support.board_size)
    for idx, piece in pieces:
        board[idx] = piece
    if hands is None:
        hands = (Hands.empty(), Hands.empty())
    return Position(
        board=tuple(board),
        hands=hands,
        side_to_move=side,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=aux_state,
    )


def test_per_owner_castling_rights_are_independent():
    from generic_chess.core.pieces import Piece
    from rule_semantics_ir_fixtures import castling_ruleset

    engine = _engine(castling_ruleset)
    s = engine.support
    n = s.board_size

    # Both sides are set up for the owner-relative castle pattern:
    # owner 0: K e1 / R h1; owner 1: K d8 / R a8.
    pos = _position(
        s,
        [
            (_idx(s, 4, 0), Piece(0, "K", "K")),
            (_idx(s, 7, 0), Piece(0, "R", "R")),
            (_idx(s, 3, n - 1), Piece(1, "K", "K")),
            (_idx(s, 0, n - 1), Piece(1, "R", "R")),
        ],
        side=0,
    )

    pattern_by_id = {p.pattern_id: p for p in engine.ir.patterns}
    white_king_step = next(
        a
        for a in engine.legal_actions(pos)
        if a.source == _idx(s, 4, 0)
        and a.target == _idx(s, 3, 0)
        and a.pattern_id.startswith("legacy_")
        and "K" in pattern_by_id[a.pattern_id].type_ids
    )
    child = engine.apply(pos, white_king_step)
    assert child.side_to_move == 1

    # Losing owner-0's right must not consume owner-1's independent right.
    black_castles = [
        a
        for a in engine.legal_actions(child)
        if a.pattern_id == "sem_00_king_side_shift"
        and a.source == _idx(s, 3, n - 1)
        and a.target == _idx(s, 1, n - 1)
    ]
    assert black_castles, "PER_OWNER slot collapsed both owners into one value"


def test_capture_trigger_survives_target_reoccupation_and_is_owner_relative():
    from generic_chess.core.pieces import Piece
    from rule_semantics_ir_fixtures import castling_ruleset

    engine = _engine(castling_ruleset)
    s = engine.support
    n = s.board_size

    # Black rook captures the watched white partner on h1.
    pos = _position(
        s,
        [
            (_idx(s, 4, 0), Piece(0, "K", "K")),
            (_idx(s, 7, 0), Piece(0, "R", "R")),
            (_idx(s, 3, n - 1), Piece(1, "K", "K")),
            (_idx(s, 7, n - 1), Piece(1, "R", "R")),
        ],
        side=1,
    )
    capture = next(
        a
        for a in engine.legal_actions(pos)
        if a.source == _idx(s, 7, n - 1)
        and a.target == _idx(s, 7, 0)
        and a.pattern_id.startswith("legacy_")
    )
    child = engine.apply(pos, capture)

    # Later a replacement white rook occupies h1. The original right must stay
    # dead. This also catches trigger logic that only checks final post==None.
    board = list(child.board)
    board[_idx(s, 7, 0)] = Piece(0, "R", "R")
    replacement = type(child)(
        board=tuple(board),
        hands=child.hands,
        side_to_move=0,
        ruleset_fingerprint=child.ruleset_fingerprint,
        aux_state=child.aux_state,
    )
    assert not [
        a
        for a in engine.legal_actions(replacement)
        if a.pattern_id == "sem_00_king_side_shift"
    ], "capture/removal event failed to permanently invalidate the victim owner's right"


def test_nifu_action_base_does_not_match_different_type_piece():
    from generic_chess.core.pieces import Piece
    from generic_chess.core.position import Hands
    from rule_semantics_ir_fixtures import nifu_ruleset

    engine = _engine(nifu_ruleset)
    s = engine.support

    # A K on the file is a different base type and must not trigger the P nifu
    # guard. The K is also the required own anchor.
    pos = _position(
        s,
        [
            (_idx(s, 4, 0), Piece(0, "K", "K")),
            (_idx(s, 7, 7), Piece(1, "K", "K")),
        ],
        side=0,
        hands=(Hands((("P", 1),)), Hands.empty()),
    )
    drops = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_drop_file_occupancy_guard"
        and a.target == _idx(s, 4, 2)
    ]
    assert drops, "ACTION_BASE was resolved from the scanned K instead of the drop actor P"


def test_anchor_is_attackable_but_not_legally_capturable():
    from generic_chess.core.pieces import Piece
    from rule_semantics_ir_fixtures import cannon_ruleset

    engine = _engine(cannon_ruleset)
    s = engine.support

    target = _idx(s, 2, 0)
    pos = _position(
        s,
        [
            (_idx(s, 0, 0), Piece(0, "C", "C")),
            (_idx(s, 1, 0), Piece(1, "C", "C")),  # one screen
            (target, Piece(1, "K", "K")),
            (_idx(s, 7, 7), Piece(0, "K", "K")),
        ],
        side=0,
    )
    assert engine.is_square_attacked(pos, target, 0) is True
    assert not [
        a
        for a in engine.legal_actions(pos)
        if a.target == target and a.pattern_id == "sem_01_cannon_capture"
    ], "enemy anchor appeared as a legal capture"


def test_b3_supported_s4_ruleset_is_executable_as_a_whole():
    from generic_chess.core.semantic_executor import SemanticEngine
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from rule_semantics_ir_fixtures import uchifuzume_ruleset

    compiled = compile_semantic_ruleset(uchifuzume_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    assert compiled.ir.capabilities.new_ir_core_executable is True
    engine = SemanticEngine(compiled)
    assert engine.ir.capabilities.new_ir_core_executable is True


def test_public_semantic_apply_rejects_forged_geometry_binding():
    from generic_chess.core.errors import IllegalActionError
    from generic_chess.core.pieces import Piece
    from generic_chess.core.semantic_executor import SemanticAction
    from rule_semantics_ir_fixtures import cannon_ruleset

    engine = _engine(cannon_ruleset)
    s = engine.support
    source = _idx(s, 0, 0)
    pos = _position(
        s,
        [
            (source, Piece(0, "C", "C")),
            (_idx(s, 7, 7), Piece(0, "K", "K")),
            (_idx(s, 6, 7), Piece(1, "K", "K")),
        ],
        side=0,
    )

    forged = SemanticAction(
        pattern_id="sem_00_cannon_quiet",
        source=source,
        target=_idx(s, 1, 1),  # diagonal: not produced by cannon ray geometry
    )
    with pytest.raises(IllegalActionError):
        engine.apply(pos, forged)


def test_existing_public_core_lifecycle_accepts_semantic_rulesets():
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action, initial_state
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from rule_semantics_ir_fixtures import castling_ruleset

    compiled = compile_semantic_ruleset(castling_ruleset())
    state = initial_state(compiled)
    actions = legal_actions(state, compiled)
    assert actions
    child = apply_action(state, actions[0], compiled)
    assert child.ply_count == state.ply_count + 1
    assert child.position.side_to_move == 1 - state.position.side_to_move
    assert child.repetition_counts


def test_forced_promotion_with_no_alive_target_has_no_unpromoted_fallback():
    from generic_chess.core.coordinates import Square
    from generic_chess.core.pieces import Piece
    from generic_chess.core.semantic_executor import SemanticEngine

    n = 3
    source = 0
    target = n  # a2
    from_sq = Square(0, 0)
    to_sq = Square(0, 1)

    engine = object.__new__(SemanticEngine)
    engine.support = SimpleNamespace(
        board_size=n,
        promotion_allowed={
            "P": (frozenset({(from_sq, to_sq)}), frozenset())
        },
        promotion_forced={
            "P": (frozenset({to_sq}), frozenset())
        },
        type_metadata={
            "P": SimpleNamespace(
                is_promotable=True,
                promotion_target_ids=("DEAD",),
            )
        },
        # DEAD has no mobility from the forced destination.
        empty_mobility={
            "DEAD": (
                tuple(() for _ in range(n * n)),
                tuple(() for _ in range(n * n)),
            )
        },
    )
    pattern = SimpleNamespace(promotion_mode="inherit_compiled_masks")
    piece = Piece(0, "P", "P")
    assert engine._promotion_choices(pattern, piece, source, target) == ()


def test_multi_type_legacy_atom_pattern_does_not_cross_product_geometry():
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.rules.schema import (
        RuleActionEffect,
        RuleGeometrySpec,
        RuleInvariant,
        RuleSemanticAction,
        RuleSquareRef,
    )
    from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset

    a_type = PieceType("A", "A", (LeapAtom((1, 0)),))
    b_type = PieceType("B", "B", (LeapAtom((0, 1)),))
    action = RuleSemanticAction(
        name="multi_type_legacy_atoms",
        type_ids=("A", "B"),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        composition="augment",
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    ruleset = _semantic_ruleset((_king_type(), a_type, b_type), (action,), n=5)
    engine = _engine(lambda: ruleset)
    s = engine.support

    source = _idx(s, 2, 2)
    pos = _position(
        s,
        [
            (source, Piece(0, "A", "A")),
            (_idx(s, 0, 0), Piece(0, "K", "K")),
            (_idx(s, 4, 4), Piece(1, "K", "K")),
        ],
        side=0,
    )
    sem_targets = {
        a.target
        for a in engine.legal_actions(pos)
        if a.pattern_id.startswith("sem_") and a.source == source
    }
    assert _idx(s, 3, 2) in sem_targets
    assert _idx(s, 2, 3) not in sem_targets, (
        "type A incorrectly inherited type B's legacy atom geometry"
    )


def test_path_between_is_strict_lattice_segment_not_bounding_box():
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.rules.schema import (
        RuleActionEffect,
        RuleGeometrySpec,
        RuleInvariant,
        RuleSemanticAction,
        RuleSpatialSelector,
        RuleSquareRef,
        RuleStateGuard,
        RuleTypeRef,
    )
    from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset

    mover = PieceType("A", "A", (LeapAtom((2, 2)),))
    guard = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef(kind="any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(
            kind="path_between",
            refs=(RuleSquareRef("source"), RuleSquareRef("target")),
        ),
        comparison="eq",
        value=0,
    )
    action = RuleSemanticAction(
        name="strict_between",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(2, 2)),
        target_relation="empty",
        state_guards=(guard,),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    ruleset = _semantic_ruleset((_king_type(), mover), (action,), n=5)
    engine = _engine(lambda: ruleset)
    s = engine.support

    source = _idx(s, 1, 1)
    target = _idx(s, 3, 3)
    # b? Put a piece inside the bounding rectangle but off the A->B lattice
    # segment. It must not count as PATH_BETWEEN. Endpoints are excluded too.
    pos = _position(
        s,
        [
            (source, Piece(0, "A", "A")),
            (_idx(s, 2, 1), Piece(1, "A", "A")),  # off-line
            (_idx(s, 0, 0), Piece(0, "K", "K")),
            (_idx(s, 4, 4), Piece(1, "K", "K")),
        ],
        side=0,
    )
    actions = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id.startswith("sem_") and a.source == source and a.target == target
    ]
    assert actions, "PATH_BETWEEN used a bounding rectangle or included endpoints"
