"""Focused regression coverage for Phase 1.9B-2 Review R3 fixes.

These tests are not specification.  R3-01 asserts that ruleset identity
validation precedes any GameState-content early return for semantic public
Core operations; R3-02 asserts that the reference executor never re-infers
geometry at transition time (exact geometry_id only, no first-match
fallback).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.errors import IllegalActionError, RuleSetMismatchError
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticAction, SemanticEngine
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import apply_action, initial_state, legal_successors
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates

from rule_semantics_ir_fixtures import (
    cannon_ruleset,
    castling_ruleset,
    nifu_ruleset,
)


def _compile(ruleset):
    return compile_semantic_ruleset(ruleset)


def _engine(ruleset):
    return SemanticEngine(_compile(ruleset))


def _idx(support, file, rank):
    return rank * support.board_size + file


def _position(support, entries, side=0, hands=None, aux_state=()):
    board = [None] * (support.board_size * support.board_size)
    for file, rank, piece in entries:
        board[_idx(support, file, rank)] = piece
    if hands is None:
        hands = (Hands.empty(), Hands.empty())
    return Position(
        board=tuple(board),
        hands=hands,
        side_to_move=side,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=aux_state,
    )


# ---------------------------------------------------------------- R3-01


def test_terminal_mismatched_apply_action_raises_mismatch_first():
    a = _compile(cannon_ruleset())
    b = _compile(castling_ruleset())
    state = initial_state(a)
    terminal = replace(
        state, terminal_status=TerminalResult(TerminalStatus.STALEMATE)
    )
    with pytest.raises(RuleSetMismatchError):
        apply_action(terminal, BoardMove(Square(0, 0), Square(1, 0)), b)


def test_terminal_mismatched_legal_successors_raises_mismatch_first():
    a = _compile(cannon_ruleset())
    b = _compile(castling_ruleset())
    state = initial_state(a)
    terminal = replace(
        state, terminal_status=TerminalResult(TerminalStatus.STALEMATE)
    )
    with pytest.raises(RuleSetMismatchError):
        legal_successors(terminal, b)


def test_matched_terminal_state_keeps_terminal_contract():
    compiled = _compile(cannon_ruleset())
    state = initial_state(compiled)
    terminal = replace(
        state, terminal_status=TerminalResult(TerminalStatus.STALEMATE)
    )
    assert legal_actions(terminal, compiled) == []
    assert legal_successors(terminal, compiled) == ()
    with pytest.raises(IllegalActionError):
        apply_action(terminal, BoardMove(Square(0, 0), Square(1, 0)), compiled)


# ---------------------------------------------------------------- R3-02


def _cannon_quiet_engine_and_position():
    engine = _engine(cannon_ruleset())
    s = engine.support
    pos = _position(
        s,
        [
            (0, 0, Piece(0, "C", "C")),
            (7, 7, Piece(0, "K", "K")),
            (7, 5, Piece(1, "K", "K")),
        ],
        side=0,
    )
    pattern = next(
        p for p in engine.ir.patterns if p.pattern_id == "sem_00_cannon_quiet"
    )
    return engine, pos, pattern


def test_board_binding_missing_geometry_id_fails_closed():
    engine, pos, pattern = _cannon_quiet_engine_and_position()
    quiet = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_cannon_quiet"
    ]
    assert quiet
    # No runtime fallback remains in the reference executor (R3-02).
    assert not hasattr(engine, "_path_for")
    forged = SemanticAction(
        pattern_id="sem_00_cannon_quiet",
        source=quiet[0].source,
        target=quiet[0].target,
        actor_type="C",
        geometry_id=None,
    )
    with pytest.raises(IllegalActionError):
        engine.apply(pos, forged)
    with pytest.raises(IllegalActionError):
        engine._make_binding_from_action(pos, forged, pattern)


def test_board_binding_wrong_geometry_same_pattern_fails_closed():
    engine, pos, pattern = _cannon_quiet_engine_and_position()
    quiet = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_cannon_quiet"
    ]
    assert quiet
    source = quiet[0].source
    target = quiet[0].target
    reachable = {
        gid
        for gid in pattern.geometry_ids
        if any(
            t == target
            for t, _ in geometry_candidates(engine.ir.geometry[gid], "0", source)
        )
    }
    assert reachable
    wrong = next(gid for gid in pattern.geometry_ids if gid not in reachable)
    forged = SemanticAction(
        pattern_id=pattern.pattern_id,
        source=source,
        target=target,
        actor_type="C",
        geometry_id=wrong,
    )
    with pytest.raises(IllegalActionError):
        engine.apply(pos, forged)
    with pytest.raises(IllegalActionError):
        engine._make_binding_from_action(pos, forged, pattern)


def test_board_binding_geometry_from_different_pattern_fails_closed():
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import PieceType
    from generic_chess.rules.schema import (
        RuleActionEffect,
        RuleAuxState,
        RuleGeometrySpec,
        RuleInvariant,
        RuleSemanticAction,
        RuleSquareRef,
    )
    from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    flag = RuleAuxState("flag", "bool", "global", "persistent", 0)

    def semantic(name, value):
        return RuleSemanticAction(
            name=name,
            type_ids=("A",),
            geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
            target_relation="empty",
            composition="augment",
            aux_state=(flag,),
            effects=(
                RuleActionEffect(
                    "move",
                    from_ref=RuleSquareRef("source"),
                    to_ref=RuleSquareRef("target"),
                ),
                RuleActionEffect("set_bool", slot_name="flag", value=value),
            ),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )

    rows = tuple(
        tuple(
            Piece(0, "K", "K")
            if (rank, file) == (0, 0)
            else Piece(1, "K", "K")
            if (rank, file) == (4, 4)
            else Piece(0, "A", "A")
            if (rank, file) == (1, 1)
            else None
            for file in range(n)
        )
        for rank in range(n)
    )
    compiled = _compile(
        _semantic_ruleset(
            (_king_type(), a),
            (semantic("same_intent_zero", 0), semantic("same_intent_one", 1)),
            n=n,
            rows=rows,
        )
    )
    engine = SemanticEngine(compiled)
    s = engine.support
    pos = _position(
        s,
        [
            (0, 0, Piece(0, "K", "K")),
            (1, 1, Piece(0, "A", "A")),
            (4, 4, Piece(1, "K", "K")),
        ],
    )
    pattern_zero = next(
        p for p in engine.ir.patterns if p.pattern_id == "sem_00_same_intent_zero"
    )
    pattern_one = next(
        p for p in engine.ir.patterns if p.pattern_id == "sem_01_same_intent_one"
    )
    assert pattern_zero.geometry_ids != pattern_one.geometry_ids
    # pattern_one's geometry reaches the same source/target but belongs to a
    # different pattern: the binding must fail closed, not recover.
    forged = SemanticAction(
        pattern_id=pattern_zero.pattern_id,
        source=_idx(s, 1, 1),
        target=_idx(s, 2, 1),
        actor_type="A",
        geometry_id=pattern_one.geometry_ids[0],
    )
    with pytest.raises(IllegalActionError):
        engine.apply(pos, forged)
    with pytest.raises(IllegalActionError):
        engine._make_binding_from_action(pos, forged, pattern_zero)


def test_drop_binding_missing_or_board_geometry_fails_closed():
    engine = _engine(nifu_ruleset())
    s = engine.support
    n = s.board_size
    pos = _position(
        s,
        [
            (0, 0, Piece(0, "K", "K")),
            (n - 1, n - 1, Piece(1, "K", "K")),
        ],
        side=0,
        hands=(Hands((("P", 1),)), Hands.empty()),
    )
    pattern = next(
        p
        for p in engine.ir.patterns
        if p.pattern_id == "sem_00_drop_file_occupancy_guard"
    )
    drops = [
        a for a in engine.legal_actions(pos) if a.pattern_id == pattern.pattern_id
    ]
    assert drops
    legal_drop = drops[0]

    forged_none = replace(legal_drop, geometry_id=None)
    with pytest.raises(IllegalActionError):
        engine.apply(pos, forged_none)
    with pytest.raises(IllegalActionError):
        engine._make_binding_from_action(pos, forged_none, pattern)

    board_gid = next(
        g for g in engine.ir.geometry if engine.ir.geometry[g].kind != "drop"
    )
    forged_board = replace(legal_drop, geometry_id=board_gid)
    with pytest.raises(IllegalActionError):
        engine.apply(pos, forged_board)
    with pytest.raises(IllegalActionError):
        engine._make_binding_from_action(pos, forged_board, pattern)
