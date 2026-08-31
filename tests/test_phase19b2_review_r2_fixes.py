"""Focused regression coverage for Phase 1.9B-2 Review R2 fixes.

These tests are not specification; they exercise the production contracts
from ADR-015 through the public Core path.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.core.actions import (
    BoardMove,
    SemanticBoardMove,
    SemanticDropMove,
    action_from_dict,
    action_to_dict,
)
from generic_chess.core.coordinates import Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import (
    compile_ruleset,
    compile_semantic_ruleset,
    lower_legacy_to_ir,
    _build_semantic_support,
)
from generic_chess.rules.ir import CompiledSemanticRuleset

from rule_semantics_ir_fixtures import cannon_ruleset, castling_ruleset


def _compile(ruleset):
    return compile_semantic_ruleset(ruleset)


def test_semantic_drop_action_dict_round_trip():
    action = SemanticDropMove(
        pattern_id="sem_00_drop",
        geometry_id="g2",
        base_type_id="P",
        to_square=Square(3, 2),
    )
    assert action_from_dict(action_to_dict(action)) == action


def test_legacy_board_move_ambiguous_across_semantic_patterns_fails_closed():
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import Piece, PieceType
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
            (semantic("zero", 0), semantic("one", 1)),
            n=n,
            rows=rows,
        )
    )
    state = initial_state(compiled)
    public = legal_actions(state, compiled)
    semantic_actions = [
        action
        for action in public
        if isinstance(action, SemanticBoardMove)
        and action.pattern_id.startswith("sem_")
        and action.from_square == Square(1, 1)
        and action.to_square == Square(2, 1)
    ]
    assert len(semantic_actions) == 2
    with pytest.raises(IllegalActionError, match="ambiguous"):
        apply_action(state, BoardMove(Square(1, 1), Square(2, 1)), compiled)


def test_session_record_serialization_preserves_semantic_actions():
    from generic_chess.session.record import GameRecord
    from generic_chess.session.serialization import (
        deserialize_game_record,
        serialize_game_record,
    )

    record = GameRecord(
        schema_version=1,
        ruleset_fingerprint="fp",
        actions=(
            SemanticBoardMove(
                pattern_id="sem_00_x",
                geometry_id="g0",
                actor_type_id="A",
                from_square=Square(0, 0),
                to_square=Square(1, 0),
            ),
        ),
        resigned_by=None,
    )
    restored = deserialize_game_record(serialize_game_record(record))
    assert restored == record


def test_public_semantic_apply_rejects_ruleset_mismatch():
    from generic_chess.core.errors import RuleSetMismatchError

    a = _compile(cannon_ruleset())
    b = _compile(castling_ruleset())
    state = initial_state(a)
    with pytest.raises(RuleSetMismatchError):
        apply_action(state, action_from_dict(action_to_dict(legal_actions(state, a)[0])), b)


def test_public_legal_successors_legacy_differential():
    """Semantic public path (legal_actions/legal_successors/apply_action)
    matches the legacy engine for a legacy-lowered ruleset."""
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.core.movegen import legal_actions_from_position
    from generic_chess.core.transition import _transition, legal_successors

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    legacy = build_compiled(specs["gen_classic_like_4_101"])
    ir = lower_legacy_to_ir(legacy)
    semantic = CompiledSemanticRuleset(
        ir=replace(
            ir,
            capabilities=replace(ir.capabilities, new_ir_core_executable=True),
        ),
        _legacy_compiled=legacy,
        support=_build_semantic_support(legacy),
    )
    state = initial_state(semantic)

    legacy_initial = initial_state(legacy)
    public_actions = legal_actions(state, semantic)
    legacy_actions = legal_actions_from_position(legacy_initial.position, legacy)
    assert len(public_actions) == len(legacy_actions)

    successors = legal_successors(state, semantic)
    assert [action for action, _ in successors] == list(public_actions)
    # Every public child matches the mechanical legacy child.
    from generic_chess.core.actions import BoardMove, DropMove

    for action, child in successors:
        legacy_move = None
        if isinstance(action, SemanticBoardMove):
            legacy_move = BoardMove(action.from_square, action.to_square, action.promotion_target_id)
        else:
            legacy_move = DropMove(action.base_type_id, action.to_square)
        legacy_child = _transition(legacy_initial, legacy_move, legacy)
        assert child.position.board == legacy_child.position.board
        assert child.position.hands == legacy_child.position.hands
        assert child.position.side_to_move == legacy_child.position.side_to_move
        assert child.terminal_status == legacy_child.terminal_status
