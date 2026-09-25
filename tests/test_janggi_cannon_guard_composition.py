from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import legal_actions
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import guarded_actions, pack_action, pack_position
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
)


def _cannon_ruleset(width=9, height=10):
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
    cannon = PieceType("C", "Cannon", (RayAtom((1, 0)),))
    ordinary = PieceType("B", "Ordinary", ())

    no_cannon_screen = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef("explicit", "C"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(
            "path_between",
            refs=(RuleSquareRef("source"), RuleSquareRef("target")),
        ),
        comparison="eq",
        value=0,
    )
    no_cannon_target = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef("explicit", "C"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(
            "exact", refs=(RuleSquareRef("target"),)
        ),
        comparison="eq",
        value=0,
        subject_ref=RuleSquareRef("target"),
    )

    common = dict(
        type_ids=("C",),
        geometry=RuleGeometrySpec(
            kind="ray", direction=(1, 0), owner_relative=False
        ),
        path_constraints=(RulePathConstraint("path_count_eq", count=1),),
        state_guards=(no_cannon_screen,),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    quiet = RuleSemanticAction(
        name="janggi_cannon_quiet",
        target_relation="empty",
        effects=(RuleActionEffect(
            "move", from_ref=RuleSquareRef("source"),
            to_ref=RuleSquareRef("target"),
        ),),
        **common,
    )
    capture = RuleSemanticAction(
        name="janggi_cannon_capture",
        target_relation="enemy",
        state_guards=(no_cannon_screen, no_cannon_target),
        effects=(
            RuleActionEffect(
                "remove", square_ref=RuleSquareRef("target"),
                disposition="remove_from_game", piece_owner="opponent",
            ),
            RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        **{key: value for key, value in common.items() if key != "state_guards"},
    )

    rows = [[None] * width for _ in range(height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[height - 1][width - 1] = Piece(1, "K", "K")
    mask = (False,) * (width * height)
    return RuleSet(
        board_size=width if width == height else None,
        board_width=width,
        board_height=height,
        piece_types=(king, cannon, ordinary),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"C": (mask, mask), "B": (mask, mask)},
        semantic_actions=(quiet, capture),
        capture_disposition="remove_from_game",
    )


def _state(compiled, owner, screen_type, target_type=None):
    state = initial_state(compiled)
    width = compiled.support.board_shape.width
    source, screen, target = Square(0, 4), Square(2, 4), Square(4, 4)
    board = list(state.position.board)
    board[source.rank * width + source.file] = Piece(owner, "C", "C")
    board[screen.rank * width + screen.file] = Piece(1 - owner, screen_type, screen_type)
    if target_type is not None:
        board[target.rank * width + target.file] = Piece(1 - owner, target_type, target_type)
    return replace(
        state,
        position=replace(state.position, board=tuple(board), side_to_move=owner),
    )


def _actions(state, compiled, target):
    return {
        action.pattern_id.split("_", 2)[-1]
        for action in legal_actions(state, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(0, 4)
        and action.to_square == target
    }


def test_janggi_cannon_screen_and_capture_type_guards_compose_publicly():
    compiled = compile_ruleset_for_execution(_cannon_ruleset())
    source, target = Square(0, 4), Square(4, 4)

    for owner in (0, 1):
        ordinary_quiet = _state(compiled, owner, "B")
        cannon_quiet = _state(compiled, owner, "C")
        assert _actions(ordinary_quiet, compiled, target) == {"janggi_cannon_quiet"}
        assert _actions(cannon_quiet, compiled, target) == set()

        ordinary_capture = _state(compiled, owner, "B", "B")
        cannon_screen_capture = _state(compiled, owner, "C", "B")
        cannon_target_capture = _state(compiled, owner, "B", "C")
        assert _actions(ordinary_capture, compiled, target) == {"janggi_cannon_capture"}
        assert _actions(cannon_screen_capture, compiled, target) == set()
        assert _actions(cannon_target_capture, compiled, target) == set()

        capture = next(
            action for action in legal_actions(ordinary_capture, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.from_square == source and action.to_square == target
        )
        child = apply_action(ordinary_capture, capture, compiled)
        assert child.position.board[target.rank * 9 + target.file] == Piece(owner, "C", "C")
        assert child.position.board[4 * 9 + 2] == Piece(1 - owner, "B", "B")


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_janggi_cannon_guard_composition_matches_native_on_square_diagnostic():
    ruleset = _cannon_ruleset(10, 10)
    semantic = compile_semantic_ruleset(ruleset)
    compiled = compile_ruleset_for_execution(ruleset)
    native_rules = compile_native_semantic_rules(semantic)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    geometry_ids = {
        geometry_id: index
        for index, geometry_id in enumerate(sorted(semantic.ir.geometry))
    }
    pattern_ids = {
        pattern.pattern_id: index
        for index, pattern in enumerate(semantic.ir.patterns)
    }
    for owner, screen_type, target_type in (
        (0, "B", "B"), (0, "C", "B"), (0, "B", "C"),
        (1, "B", "B"), (1, "C", "B"), (1, "B", "C"),
    ):
        state = _state(compiled, owner, screen_type, target_type)
        python_actions = set()
        for action in legal_actions(state, compiled):
            source_index = action.from_square.rank * 10 + action.from_square.file
            target_index = action.to_square.rank * 10 + action.to_square.file
            piece = state.position.board[source_index]
            python_actions.add(pack_action({
                "to": target_index,
                "from": source_index,
                "promotion": type_ids[action.promotion_target_id] if action.promotion_target_id else 255,
                "base": type_ids[piece.base_type_id],
                "kind": 2,
                "pattern": pattern_ids[action.pattern_id],
                "geometry": geometry_ids[action.geometry_id],
                "actor_current": type_ids[action.actor_type_id],
            }))

        board = [
            None if piece is None else [
                type_ids[piece.base_type_id], type_ids[piece.current_type_id],
                piece.owner, int(piece.promoted),
            ]
            for piece in state.position.board
        ]
        native_position = pack_position(native_rules, {
            "side": state.position.side_to_move,
            "ply": 0,
            "board": board,
            "hands": [[0] * len(type_ids), [0] * len(type_ids)],
            "aux_state": state.position.aux_state,
        })
        assert set(guarded_actions(native_rules, native_position)) == python_actions
