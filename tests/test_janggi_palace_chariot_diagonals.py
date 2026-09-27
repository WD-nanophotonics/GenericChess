from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import legal_actions
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleSquareZoneGuard,
    RuleStateGuard,
    RuleTypeRef,
)


def _palace_chariot_ruleset():
    cross = tuple(
        (file, rank)
        for base in (0, 7)
        for file, rank in (
            (3, base), (4, base + 1), (5, base + 2),
            (5, base), (3, base + 2),
        )
    )
    zone = RuleSpatialSelector(kind="zone", zone_squares=cross)

    def inside(square_ref):
        return RuleSquareZoneGuard(
            square_ref=RuleSquareRef(square_ref),
            spatial=zone,
            relation="inside",
            owner_relative=False,
        )

    moves = tuple(
        RuleSemanticAction(
            name=f"palace_ray_{df}_{dr}",
            type_ids=("R",),
            geometry=RuleGeometrySpec(
                kind="ray", direction=(df, dr), max_steps=2,
                owner_relative=False,
            ),
            target_relation="empty",
            path_constraints=(RulePathConstraint("path_clear"),),
            effects=(RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),),
            invariants=(RuleInvariant("own_anchor_safe"),),
            square_zone_guards=(inside("source"), inside("target")),
        )
        for df, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1))
    )
    royal_moves = tuple(
        RuleSemanticAction(
            name=f"palace_royal_step_{df}_{dr}",
            type_ids=("K",),
            geometry=RuleGeometrySpec(
                kind="leap", offset=(df, dr), owner_relative=False,
            ),
            target_relation="empty",
            effects=(RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),),
            invariants=(RuleInvariant("own_anchor_safe"),),
            square_zone_guards=(inside("source"), inside("target")),
        )
        for df, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1))
    )
    rows = [[None] * 9 for _ in range(10)]
    rows[4][0] = Piece(0, "K", "K")
    rows[5][8] = Piece(1, "K", "K")
    rows[0][3] = Piece(0, "R", "R")
    return RuleSet(
        board_size=None,
        board_width=9,
        board_height=10,
        piece_types=(
            PieceType("K", "Anchor", (), is_anchor=True),
            PieceType("R", "Chariot", ()),
            PieceType("B", "Blocker", ()),
        ),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={
            type_id: ((False,) * 90, (False,) * 90)
            for type_id in ("R", "B")
        },
        semantic_actions=(*moves, *royal_moves),
    )


def _position(compiled, owner, source, blocker=None, mover="R"):
    state = initial_state(compiled)
    board = list(state.position.board)
    for index, piece in enumerate(board):
        if piece is not None and (
            piece.base_type_id in ("R", "B")
            or (mover == "K" and piece.base_type_id == "K" and piece.owner == owner)
        ):
            board[index] = None
    board[source.rank * 9 + source.file] = Piece(owner, mover, mover)
    if blocker is not None:
        square, blocker_owner = blocker
        board[square.rank * 9 + square.file] = Piece(blocker_owner, "B", "B")
    return replace(
        state,
        position=replace(state.position, board=tuple(board), side_to_move=owner),
    )


def _has_move(state, compiled, source, target):
    return any(
        isinstance(action, SemanticBoardMove)
        and action.from_square == source
        and action.to_square == target
        for action in legal_actions(state, compiled)
    )


def test_janggi_chariot_palace_diagonals_are_exact_and_apply_for_both_owners():
    compiled = compile_ruleset_for_execution(_palace_chariot_ruleset())
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.native_executable

    for owner in (0, 1):
        for base in (0, 7):
            corner, center, opposite = (
                Square(3, base), Square(4, base + 1), Square(5, base + 2)
            )

            for source, target in (
                (corner, center),
                (center, opposite),
                (corner, opposite),
            ):
                state = _position(compiled, owner, source)
                assert _has_move(state, compiled, source, target)
                if source == corner and target == opposite:
                    action = next(
                        action for action in legal_actions(state, compiled)
                        if isinstance(action, SemanticBoardMove)
                        and action.from_square == source and action.to_square == target
                    )
                    child = apply_action(state, action, compiled)
                    assert child.position.board[target.rank * 9 + target.file] == Piece(owner, "R", "R")
                    assert child.position.board[source.rank * 9 + source.file] is None

            blocked = _position(compiled, owner, corner, (center, 1 - owner))
            assert not _has_move(blocked, compiled, corner, opposite)

            off_palace = (Square(2, base), Square(3, base + 1))
            assert not _has_move(
                _position(compiled, owner, off_palace[0]), compiled, *off_palace
            )
            palace_corner, outside_target = Square(5, base), Square(6, base + 1)
            assert not _has_move(
                _position(compiled, owner, palace_corner),
                compiled,
                palace_corner,
                outside_target,
            )

            # The midpoint of a palace side is not on either marked X diagonal.
            side_edge = Square(3, base + 1)
            off_line_target = Square(4, base + 2)
            assert not _has_move(
                _position(compiled, owner, side_edge),
                compiled,
                side_edge,
                off_line_target,
            )


def test_janggi_palace_zone_guards_fail_closed_for_native():
    from generic_chess.native.compiler import (
        NativeUnsupportedRuleError,
        build_semantic_compile_payload,
    )

    compiled = compile_ruleset_for_execution(_palace_chariot_ruleset())
    with pytest.raises(NativeUnsupportedRuleError, match="square zone guards"):
        build_semantic_compile_payload(compiled)


def test_one_step_royal_diagonal_template_stays_on_marked_palace_edges():
    compiled = compile_ruleset_for_execution(_palace_chariot_ruleset())
    for owner in (0, 1):
        for base in (0, 7):
            corner = Square(3, base)
            center = Square(4, base + 1)
            opposite = Square(5, base + 2)
            state = _position(compiled, owner, corner, mover="K")
            assert _has_move(state, compiled, corner, center)
            assert not _has_move(state, compiled, corner, opposite)
            action = next(
                action for action in legal_actions(state, compiled)
                if isinstance(action, SemanticBoardMove)
                and action.from_square == corner and action.to_square == center
            )
            child = apply_action(state, action, compiled)
            assert child.position.board[center.rank * 9 + center.file] == Piece(owner, "K", "K")
            assert child.position.board[corner.rank * 9 + corner.file] is None

            side_edge = Square(3, base + 1)
            off_line_target = Square(4, base + 2)
            side_state = _position(compiled, owner, side_edge, mover="K")
            assert not _has_move(side_state, compiled, side_edge, off_line_target)


def _janggi_elephant_ruleset():
    king = PieceType(
        "K", "Anchor",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )

    def empty_intermediate(offset):
        return RuleStateGuard(
            aggregation="count",
            owner="any",
            type_ref=RuleTypeRef("explicit", "B"),
            compare_field="base",
            promoted="any",
            location="board",
            spatial=RuleSpatialSelector(
                "exact",
                refs=(RuleSquareRef(
                    "offset_from_source", offset=offset, owner_relative=True
                ),),
            ),
            comparison="eq",
            value=0,
        )

    elephant = RuleSemanticAction(
        name="elephant_three_by_two",
        type_ids=("E",),
        geometry=RuleGeometrySpec(
            kind="leap", offset=(2, 3), owner_relative=True
        ),
        target_relation="empty",
        state_guards=(empty_intermediate((0, 1)), empty_intermediate((1, 2))),
        effects=(RuleActionEffect(
            "move", from_ref=RuleSquareRef("source"),
            to_ref=RuleSquareRef("target"),
        ),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rows = [[None] * 9 for _ in range(10)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    rows[2][2] = Piece(0, "E", "E")
    mask = (False,) * 90
    return RuleSet(
        board_size=None,
        board_width=9,
        board_height=10,
        piece_types=(king, PieceType("E", "Elephant", ()), PieceType("B", "Blocker", ())),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"E": (mask, mask), "B": (mask, mask)},
        semantic_actions=(elephant,),
    )


def test_janggi_elephant_each_intermediate_blocker_is_independently_enforced():
    compiled = compile_ruleset_for_execution(_janggi_elephant_ruleset())
    for owner, source, target, blockers in (
        (0, Square(2, 2), Square(4, 5), (Square(2, 3), Square(3, 4))),
        (1, Square(6, 7), Square(4, 4), (Square(6, 6), Square(5, 5))),
    ):
        for blocked_index in (None, 0, 1):
            state = initial_state(compiled)
            board = list(state.position.board)
            for index, piece in enumerate(board):
                if piece is not None and piece.base_type_id in ("E", "B"):
                    board[index] = None
            board[source.rank * 9 + source.file] = Piece(owner, "E", "E")
            if blocked_index is not None:
                blocker = blockers[blocked_index]
                board[blocker.rank * 9 + blocker.file] = Piece(1 - owner, "B", "B")
            state = replace(
                state,
                position=replace(state.position, board=tuple(board), side_to_move=owner),
            )
            matches = [
                action for action in legal_actions(state, compiled)
                if isinstance(action, SemanticBoardMove)
                and action.from_square == source and action.to_square == target
            ]
            assert bool(matches) is (blocked_index is None)
            if blocked_index is None:
                child = apply_action(state, matches[0], compiled)
                assert child.position.board[target.rank * 9 + target.file] == Piece(owner, "E", "E")
