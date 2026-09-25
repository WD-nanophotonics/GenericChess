from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import BoardShape, Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.core.movegen import legal_actions
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleDeclaration,
    RuleDeclarationOutcomeBand,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleReplaceSelector,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
    RuleWeightedMaterialMetric,
)
from generic_chess.rules.validation import RuleValidationError
from generic_chess.core.declarations import assess_declaration


def _toy_rectangular_ruleset(*, hand_guard=False, edge_declaration=False):
    shape = BoardShape(9, 10)
    king = PieceType(
        "K",
        "Anchor",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )
    mover = PieceType("M", "Mover", ())
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[0][2] = Piece(0, "M", "M")
    rows[9][8] = Piece(1, "K", "K")
    rows[7][6] = Piece(1, "M", "M")
    action = RuleSemanticAction(
        name="horizontal_step",
        type_ids=("M",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        composition="augment",
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef(kind="source"),
                to_ref=RuleSquareRef(kind="target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    if hand_guard:
        action = replace(
            action,
            state_guards=(
                RuleStateGuard(
                    aggregation="exists",
                    owner="self",
                    type_ref=RuleTypeRef(kind="any"),
                    compare_field="base",
                    promoted="any",
                    location="hand",
                    spatial=RuleSpatialSelector(kind="any"),
                ),
            ),
        )
    declarations = ()
    if edge_declaration:
        edge = RuleSquareRef(kind="fixed", square=(8, 9))
        exact_edge = RuleSpatialSelector(kind="exact", refs=(edge,))
        edge_zone = RuleSpatialSelector(kind="zone", zone_squares=((8, 9),))
        declarations = (
            RuleDeclaration(
                declaration_id="edge_piece",
                owner=0,
                state_guards=(
                    RuleStateGuard(
                        aggregation="exists",
                        owner="opponent",
                        type_ref=RuleTypeRef(kind="explicit", type_id="K"),
                        compare_field="base",
                        promoted="any",
                        location="board",
                        spatial=exact_edge,
                        value=1,
                        subject_ref=edge,
                    ),
                ),
                require_not_in_check=False,
                weighted_metric=RuleWeightedMaterialMetric(
                    owner="any", weights={"K": 1}, spatial=edge_zone
                ),
                outcome_bands=(RuleDeclarationOutcomeBand(1, "WIN"),),
                failure_outcome="LOSS",
            ),
        )
    return RuleSet(
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        piece_types=(king, mover),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"M": ((False,) * shape.area, (False,) * shape.area)},
        semantic_actions=(action,),
        declarations=declarations,
    )


def test_public_9x10_semantic_core_initial_actions_transition_and_legality():
    compiled = compile_ruleset_for_execution(_toy_rectangular_ruleset())
    assert compiled.board_shape == BoardShape(9, 10)
    assert compiled.board_size is None
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.legacy_core_executable
    assert not compiled.ir.capabilities.native_executable

    state0 = initial_state(compiled)
    actions0 = legal_actions(state0, compiled)
    mover_action0 = next(
        action
        for action in actions0
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(2, 0)
    )
    assert mover_action0.to_square == Square(3, 0)

    state1 = apply_action(state0, mover_action0, compiled)
    assert state1.position.board_shape == BoardShape(9, 10)
    assert state1.position.side_to_move == 1
    actions1 = legal_actions(state1, compiled)
    mover_action1 = next(
        action
        for action in actions1
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(6, 7)
    )
    assert mover_action1.to_square == Square(5, 7)

    bad_action = replace(mover_action0, to_square=Square(9, 0))
    with pytest.raises(IllegalActionError, match="not a legal semantic action"):
        apply_action(state0, bad_action, compiled)


def test_rectangular_semantic_compiler_fails_closed_for_unsupported_hand_guard():
    with pytest.raises(RuleValidationError, match="HAND_PREDICATE_UNSUPPORTED"):
        compile_ruleset_for_execution(_toy_rectangular_ruleset(hand_guard=True))


def test_rectangular_declaration_uses_width_based_row_major_indexing():
    compiled = compile_ruleset_for_execution(
        _toy_rectangular_ruleset(edge_declaration=True)
    )
    state = initial_state(compiled)
    assessment = assess_declaration(state, compiled, "edge_piece")
    assert assessment.outcome == "WIN"
    assert assessment.weighted_score == 1


def _toy_horse_leg_ruleset(*, blocked_owner=None):
    shape = BoardShape(9, 10)
    king = PieceType(
        "K",
        "Anchor",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )
    horse = PieceType("H", "Leaper", (LeapAtom((2, 1)),))
    blocker = PieceType("B", "Blocker", ())
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[2][2] = Piece(0, "H", "H")
    rows[9][8] = Piece(1, "K", "K")
    rows[7][6] = Piece(1, "H", "H")
    if blocked_owner == 0:
        rows[2][3] = Piece(1, "B", "B")
    elif blocked_owner == 1:
        rows[7][5] = Piece(0, "B", "B")
    leg_guard = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef(kind="any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(
            kind="exact",
            refs=(
                RuleSquareRef(
                    kind="offset_from_source", offset=(1, 0), owner_relative=True
                ),
            ),
        ),
        comparison="eq",
        value=0,
    )
    action = RuleSemanticAction(
        name="offset_leap",
        type_ids=("H",),
        geometry=RuleGeometrySpec(kind="leap", offset=(2, 1)),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("H",),
            action_family="board",
            target_relation="empty",
            geometry_kind="leap",
            replace_all_matching=True,
        ),
        state_guards=(leg_guard,),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef(kind="source"),
                to_ref=RuleSquareRef(kind="target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    mask = (False,) * shape.area
    return RuleSet(
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        piece_types=(king, horse, blocker),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"H": (mask, mask), "B": (mask, mask)},
        semantic_actions=(action,),
    )


def test_public_9x10_path_guard_blocks_and_allows_leap_by_occupancy():
    outcomes_by_owner = {}
    for owner, source, target in (
        (0, Square(2, 2), Square(4, 3)),
        (1, Square(6, 7), Square(4, 6)),
    ):
        outcomes = []
        for blocked_owner in (None, owner):
            compiled = compile_ruleset_for_execution(
                _toy_horse_leg_ruleset(blocked_owner=blocked_owner)
            )
            state = initial_state(compiled)
            if owner == 1:
                opening = next(
                    action
                    for action in legal_actions(state, compiled)
                    if isinstance(action, SemanticBoardMove)
                    and action.from_square == Square(0, 0)
                    and action.to_square == Square(1, 0)
                )
                state = apply_action(state, opening, compiled)
                assert state.position.side_to_move == 1
            actions = legal_actions(state, compiled)
            outcomes.append(
                any(
                    isinstance(action, SemanticBoardMove)
                    and action.from_square == source
                    and action.to_square == target
                    for action in actions
                )
            )
        outcomes_by_owner[owner] = outcomes
    assert outcomes_by_owner == {0: [True, False], 1: [True, False]}
