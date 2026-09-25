from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import BoardShape, Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.core.movegen import legal_actions
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleDeclaration,
    RuleDeclarationOutcomeBand,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleSemanticAction,
    RuleReplaceSelector,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleSquareZoneGuard,
    RuleStateGuard,
    RuleTypeRef,
    RuleWeightedMaterialMetric,
    compute_fingerprint,
    ruleset_from_dict,
    ruleset_to_dict,
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


def test_state_guard_zone_does_not_filter_empty_target_coordinates():
    base = _toy_rectangular_ruleset()
    guard = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef(kind="any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(kind="zone", zone_squares=((4, 0),)),
        comparison="eq",
        value=0,
        subject_ref=RuleSquareRef(kind="target"),
    )
    template = base.semantic_actions[0]
    actions = tuple(
        replace(
            template,
            name=name,
            geometry=RuleGeometrySpec(kind="leap", offset=offset),
            state_guards=(guard,),
        )
        for name, offset in (("zone_target", (2, 0)), ("outside_target", (1, 0)))
    )
    compiled = compile_ruleset_for_execution(
        replace(base, semantic_actions=actions)
    )
    state = initial_state(compiled)
    legal = legal_actions(state, compiled)

    for target, pattern_suffix in (
        (Square(4, 0), "zone_target"),
        (Square(3, 0), "outside_target"),
    ):
        assert state.position.board[target.rank * 9 + target.file] is None
        assert any(
            isinstance(action, SemanticBoardMove)
            and action.from_square == Square(2, 0)
            and action.to_square == target
            and action.pattern_id.endswith(pattern_suffix)
            for action in legal
        )


def _palace_zone_ruleset():
    region = tuple((file, rank) for file in range(3, 6) for rank in range(3))

    def zone_guard(square, relation):
        return RuleSquareZoneGuard(
            square_ref=RuleSquareRef(kind=square),
            spatial=RuleSpatialSelector(kind="zone", zone_squares=region),
            relation=relation,
            owner_relative=True,
        )

    def move(name, offset, square_zone_guards):
        return RuleSemanticAction(
            name=name,
            type_ids=("M",),
            geometry=RuleGeometrySpec(kind="leap", offset=offset),
            target_relation="empty",
            effects=(
                RuleActionEffect(
                    "move",
                    from_ref=RuleSquareRef(kind="source"),
                    to_ref=RuleSquareRef(kind="target"),
                ),
            ),
            invariants=(RuleInvariant("own_anchor_safe"),),
            square_zone_guards=square_zone_guards,
        )

    base = _toy_rectangular_ruleset()
    return replace(
        base,
        semantic_actions=(
            move("enter_zone", (0, -1), (zone_guard("target", "inside"),)),
            move(
                "leave_zone",
                (0, 1),
                (zone_guard("source", "inside"), zone_guard("target", "outside")),
            ),
        ),
    )


def test_public_9x10_owner_relative_square_zone_guards_use_empty_squares():
    ruleset = _palace_zone_ruleset()
    serialized = ruleset_to_dict(ruleset)
    restored = ruleset_from_dict(serialized)
    assert ruleset_to_dict(restored) == serialized
    assert compute_fingerprint(restored) == compute_fingerprint(ruleset)
    compiled = compile_ruleset_for_execution(restored)
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.native_executable
    assert compiled.ir.fingerprint() == compile_ruleset_for_execution(ruleset).ir.fingerprint()
    from generic_chess.native.compiler import (
        NativeUnsupportedRuleError,
        build_semantic_compile_payload,
    )

    with pytest.raises(NativeUnsupportedRuleError, match="square zone guards"):
        build_semantic_compile_payload(compiled)

    def actions_for(owner, source):
        state = initial_state(compiled)
        board = list(state.position.board)
        for index, piece in enumerate(board):
            if piece is not None and piece.current_type_id == "M":
                board[index] = None
        source_index = source.rank * 9 + source.file
        board[source_index] = Piece(owner, "M", "M")
        position = replace(
            state.position, board=tuple(board), side_to_move=owner
        )
        state = replace(state, position=position)
        return state, legal_actions(state, compiled)

    cases = (
        # Entry into and exit from the mover's own palace (rank-flipped for side 1).
        (0, Square(4, 3), Square(4, 2), "enter_zone", True),
        (1, Square(4, 6), Square(4, 7), "enter_zone", True),
        (0, Square(4, 2), Square(4, 3), "leave_zone", True),
        (1, Square(4, 7), Square(4, 6), "leave_zone", True),
        # A mover placed in the opponent's palace must not inherit its source zone.
        (0, Square(4, 7), Square(4, 8), "leave_zone", False),
        (1, Square(4, 2), Square(4, 1), "leave_zone", False),
        # Target-region checks reject an empty target outside either palace.
        (0, Square(4, 4), Square(4, 3), "enter_zone", False),
        (1, Square(4, 5), Square(4, 6), "enter_zone", False),
    )
    for owner, source, target, pattern_name, expected in cases:
        state, actions = actions_for(owner, source)
        target_index = target.rank * 9 + target.file
        assert state.position.board[target_index] is None
        matching = [
            action
            for action in actions
            if isinstance(action, SemanticBoardMove)
            and action.from_square == source
            and action.to_square == target
            and action.pattern_id.endswith(pattern_name)
        ]
        assert len(matching) == int(expected)


def _public_9x10_cannon_ruleset(*, shift_screen_safe=True):
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
    cannon = PieceType(
        "C",
        "Ray",
        tuple(RayAtom(direction) for direction in ((1, 0), (-1, 0), (0, 1), (0, -1))),
    )
    blocker = PieceType("B", "Blocker", ())
    mover = PieceType("M", "Screen mover", ())
    quiet = RuleSemanticAction(
        name="cannon_quiet",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="empty",
        path_constraints=(RulePathConstraint("path_clear"),),
        effects=(
            RuleActionEffect(
                "move", from_ref=RuleSquareRef(kind="source"),
                to_ref=RuleSquareRef(kind="target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    capture = RuleSemanticAction(
        name="cannon_capture",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("C",), action_family="board", target_relation="enemy",
            geometry_kind="ray", replace_all_matching=True,
        ),
        path_constraints=(RulePathConstraint("path_count_eq", count=1),),
        effects=(
            RuleActionEffect(
                "remove", square_ref=RuleSquareRef(kind="target"),
                disposition="remove_from_game", piece_owner="opponent",
            ),
            RuleActionEffect(
                "move", from_ref=RuleSquareRef(kind="source"),
                to_ref=RuleSquareRef(kind="target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    shift_screen = RuleSemanticAction(
        name="shift_screen",
        type_ids=("M",),
        geometry=RuleGeometrySpec(kind="leap", offset=(2, 0), owner_relative=False),
        target_relation="empty",
        effects=(
            RuleActionEffect(
                "move", from_ref=RuleSquareRef(kind="source"),
                to_ref=RuleSquareRef(kind="target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),) if shift_screen_safe else (),
    )
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    rows[4][0] = Piece(0, "C", "C")
    mask = (False,) * shape.area
    return RuleSet(
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        piece_types=(king, cannon, blocker, mover),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"C": (mask, mask), "B": (mask, mask), "M": (mask, mask)},
        semantic_actions=(quiet, capture, shift_screen),
    )


def _public_cannon_state(compiled, owner, source, blockers=(), kings=None, extras=()):
    state = initial_state(compiled)
    kings = kings or (Square(0, 0), Square(8, 9))
    board = [None] * (9 * 10)
    for player, square in enumerate(kings):
        board[square.rank * 9 + square.file] = Piece(player, "K", "K")
    board[source.rank * 9 + source.file] = Piece(owner, "C", "C")
    for square, blocker_owner in blockers:
        board[square.rank * 9 + square.file] = Piece(blocker_owner, "B", "B")
    for square, piece_owner, type_id in extras:
        board[square.rank * 9 + square.file] = Piece(piece_owner, type_id, type_id)
    position = replace(
        state.position, board=tuple(board), side_to_move=owner
    )
    return replace(state, position=position)


def test_public_9x10_cannon_ray_path_count_and_attack_semantics():
    compiled = compile_ruleset_for_execution(_public_9x10_cannon_ruleset())
    engine = SemanticEngine(compiled)
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.native_executable
    for owner, source_file, rank, direction in ((0, 0, 4, 1), (1, 8, 5, -1)):
        source = Square(source_file, rank)
        target = lambda distance: Square(source_file + direction * distance, rank)

        no_screen = _public_cannon_state(compiled, owner, source)
        quiet_targets = {
            action.to_square
            for action in legal_actions(no_screen, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_quiet")
            and action.from_square == source
        }
        assert target(8) in quiet_targets

        first_screen = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(2), 1 - owner),),
        )
        quiet_targets = {
            action.to_square
            for action in legal_actions(first_screen, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_quiet")
            and action.from_square == source
        }
        assert target(1) in quiet_targets
        assert target(3) not in quiet_targets

        no_screen_capture = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(1), 1 - owner),),
        )
        assert not any(
            isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_capture")
            and action.from_square == source
            for action in legal_actions(no_screen_capture, compiled)
        )

        screen_before_target = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(2), owner), (target(1), 1 - owner)),
        )
        assert not any(
            isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_capture")
            and action.to_square == target(1)
            for action in legal_actions(screen_before_target, compiled)
        )

        one_screen_capture = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(2), owner), (target(4), 1 - owner)),
        )
        captures = {
            action.to_square
            for action in legal_actions(one_screen_capture, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_capture")
            and action.from_square == source
        }
        assert target(4) in captures
        capture_action = next(
            action
            for action in legal_actions(one_screen_capture, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_capture")
            and action.to_square == target(4)
        )
        captured_state = apply_action(one_screen_capture, capture_action, compiled)
        assert captured_state.position.board[target(4).rank * 9 + target(4).file] == Piece(
            owner, "C", "C"
        )
        assert captured_state.position.hands == one_screen_capture.position.hands

        farther_target = _public_cannon_state(
            compiled, owner, source,
            blockers=(
                (target(2), 1 - owner),
                (target(4), 1 - owner),
                (target(7), 1 - owner),
            ),
        )
        captures = {
            action.to_square
            for action in legal_actions(farther_target, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_capture")
            and action.from_square == source
        }
        assert target(4) in captures
        assert target(7) not in captures

        two_screens = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(2), owner), (target(4), 1 - owner), (target(7), 1 - owner)),
        )
        assert not any(
            isinstance(action, SemanticBoardMove)
            and action.pattern_id.endswith("cannon_capture")
            and action.to_square == target(7)
            for action in legal_actions(two_screens, compiled)
        )

        attack_target = target(8)
        attack_kings = (
            Square(0, 0), attack_target
        ) if owner == 0 else (
            attack_target, Square(8, 9)
        )
        one_screen_check = _public_cannon_state(
            compiled, owner, source, blockers=((target(2), 1 - owner),), kings=attack_kings
        )
        assert engine.in_check(one_screen_check.position, 1 - owner)
        no_screen_check = _public_cannon_state(
            compiled, owner, source, kings=attack_kings
        )
        assert not engine.in_check(no_screen_check.position, 1 - owner)
        two_screen_check = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(2), owner), (target(4), 1 - owner)),
            kings=attack_kings,
        )
        assert not engine.in_check(two_screen_check.position, 1 - owner)
        blocked_target_check = _public_cannon_state(
            compiled, owner, source,
            blockers=((target(2), 1 - owner),),
            kings=(
                (Square(0, 0), target(1)) if owner == 0
                else (target(1), Square(8, 9))
            ),
        )
        assert not engine.in_check(blocked_target_check.position, 1 - owner)


def test_public_9x10_cannon_path_guard_preserves_own_king_safety():
    safe_ruleset = _public_9x10_cannon_ruleset(shift_screen_safe=True)
    safe_compiled = compile_ruleset_for_execution(safe_ruleset)
    safe_engine = SemanticEngine(safe_compiled)
    kings = (Square(4, 8), Square(8, 9))
    source = Square(2, 4)
    cannon_source = Square(4, 0)
    extras = ((source, 0, "M"),)
    safe_state = _public_cannon_state(
        safe_compiled, 1, cannon_source, kings=kings, extras=extras
    )
    safe_state = replace(
        safe_state,
        position=replace(safe_state.position, side_to_move=0),
    )
    assert not safe_engine.in_check(safe_state.position, 0)
    assert not any(
        isinstance(action, SemanticBoardMove)
        and action.pattern_id.endswith("shift_screen")
        for action in legal_actions(safe_state, safe_compiled)
    )

    unsafe_ruleset = _public_9x10_cannon_ruleset(shift_screen_safe=False)
    unsafe_compiled = compile_ruleset_for_execution(unsafe_ruleset)
    unsafe_engine = SemanticEngine(unsafe_compiled)
    unsafe_state = _public_cannon_state(
        unsafe_compiled, 1, cannon_source, kings=kings, extras=extras
    )
    unsafe_state = replace(
        unsafe_state,
        position=replace(unsafe_state.position, side_to_move=0),
    )
    shift = next(
        action
        for action in legal_actions(unsafe_state, unsafe_compiled)
        if isinstance(action, SemanticBoardMove)
        and action.pattern_id.endswith("shift_screen")
    )
    child = apply_action(unsafe_state, shift, unsafe_compiled)
    assert unsafe_engine.in_check(child.position, 0)


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
