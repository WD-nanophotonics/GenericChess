from collections import Counter
from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import BoardShape, Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.keys import position_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.core.position import HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from generic_chess.native.compiler import (
    NativeUnsupportedRuleError,
    build_semantic_compile_payload,
)


def _state(compiled, pieces, *, side=0):
    state = initial_state(compiled)
    board = [None] * 90
    for owner, type_id, square in pieces:
        index = square.rank * 9 + square.file
        assert board[index] is None, (square, board[index], type_id)
        board[index] = Piece(owner, type_id, type_id)
    return replace(
        state,
        position=replace(
            state.position, board=tuple(board), side_to_move=side
        ),
    )


def _targets(state, compiled, source):
    """All public legal destinations from source, without pattern filtering."""
    return {
        action.to_square
        for action in legal_actions(state, compiled)
        if isinstance(action, SemanticBoardMove) and action.from_square == source
    }


def _ruleset_with_pieces(pieces, *, repetition_policy="draw", mutual_fixture=False):
    ruleset = build_xiangqi_diagnostic_ruleset()
    rows = [[None] * 9 for _ in range(10)]
    for owner, type_id, square in pieces:
        rows[square.rank][square.file] = Piece(owner, type_id, type_id)
    actions = ruleset.semantic_actions
    if mutual_fixture:
        # This generic synthetic fixture has no General moves and omits the
        # own-anchor-safety invariant. It is not a legal Xiangqi position or
        # a WXF behavior fixture.
        actions = tuple(
            replace(action, invariants=())
            for action in actions
            if action.type_ids == ("R",)
        )
    return replace(
        ruleset,
        initial_position=tuple(tuple(row) for row in rows),
        repetition_limit=3,
        repetition_policy=repetition_policy,
        semantic_actions=actions,
        metadata={
            "diagnostic_scope": (
                "synthetic mutual-check policy test"
                if mutual_fixture else "single-sided check cycle test"
            )
        },
    )


@pytest.fixture(scope="module")
def product():
    ruleset = build_xiangqi_diagnostic_ruleset()
    compiled = compile_ruleset_for_execution(ruleset)
    return ruleset, compiled, SemanticEngine(compiled)


def test_initial_layout_and_public_product_are_standard_single_ply(product):
    ruleset, compiled, _engine = product
    shape = BoardShape(9, 10)
    state = initial_state(compiled)
    assert compiled.board_shape == shape
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.native_executable
    with pytest.raises(NativeUnsupportedRuleError, match="square zone guards"):
        build_semantic_compile_payload(compiled)
    assert ruleset.capture_disposition == "remove_from_game"
    assert ruleset.stalemate_result == "loss"
    assert not ruleset.promotion_allowed and not ruleset.promotion_forced
    assert all(not piece_type.is_promotable for piece_type in ruleset.piece_types)
    assert all(not any(mask) for masks in ruleset.drop_allowed.values() for mask in masks)

    counts = {owner: Counter() for owner in (0, 1)}
    coordinates = {owner: {} for owner in (0, 1)}
    for square, piece in enumerate(state.position.board):
        if piece is not None:
            counts[piece.owner][piece.base_type_id] += 1
            coordinates[piece.owner].setdefault(piece.base_type_id, set()).add(
                (square % 9, square // 9)
            )
    expected = Counter({"G": 1, "A": 2, "E": 2, "H": 2, "R": 2, "C": 2, "S": 5})
    assert counts == {0: expected, 1: expected}
    assert sum(map(sum, (counter.values() for counter in counts.values()))) == 32
    assert coordinates[0] == {
        "R": {(0, 0), (8, 0)},
        "H": {(1, 0), (7, 0)},
        "E": {(2, 0), (6, 0)},
        "A": {(3, 0), (5, 0)},
        "G": {(4, 0)},
        "C": {(1, 2), (7, 2)},
        "S": {(0, 3), (2, 3), (4, 3), (6, 3), (8, 3)},
    }
    assert coordinates[1] == {
        type_id: {(8 - file, 9 - rank) for file, rank in squares}
        for type_id, squares in coordinates[0].items()
    }
    assert state.position.board[0 * 9 + 4] == Piece(0, "G", "G")
    assert state.position.board[9 * 9 + 4] == Piece(1, "G", "G")
    assert state.position.board[2 * 9 + 1] == Piece(0, "C", "C")
    assert state.position.board[7 * 9 + 7] == Piece(1, "C", "C")
    assert state.position.board[3 * 9 + 8] == Piece(0, "S", "S")
    assert state.position.board[6 * 9 + 0] == Piece(1, "S", "S")

    serialized = ruleset_to_dict(ruleset)
    restored = ruleset_from_dict(serialized)
    assert ruleset_to_dict(restored) == serialized
    assert compute_fingerprint(restored) == compute_fingerprint(ruleset)
    initial_actions = legal_actions(state, compiled)
    assert len(initial_actions) == 44
    assert all(isinstance(action, SemanticBoardMove) for action in initial_actions)
    assert {action.actor_type_id for action in initial_actions} == {
        "A", "C", "E", "G", "H", "R", "S"
    }
    soldier_move = next(
        action for action in initial_actions
        if action.from_square == Square(0, 3) and action.to_square == Square(0, 4)
    )
    moved = apply_action(state, soldier_move, compiled)
    assert moved.position.board[4 * 9] == Piece(0, "S", "S")
    assert moved.position.side_to_move == 1


def test_generals_and_advisors_are_one_step_and_confined_to_each_palace(product):
    _ruleset, compiled, _engine = product
    for side, own_g, enemy_g, source, inside, outside, diagonal in (
        (0, Square(3, 1), Square(8, 9), Square(3, 1), Square(4, 1), Square(2, 1), Square(4, 2)),
        (1, Square(5, 8), Square(0, 0), Square(5, 8), Square(4, 8), Square(6, 8), Square(4, 7)),
    ):
        state = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g)],
            side=side,
        )
        assert inside in _targets(state, compiled, source)
        assert outside not in _targets(state, compiled, source)
        assert diagonal not in _targets(state, compiled, source)
        legal_step = next(
            action for action in legal_actions(state, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.from_square == source and action.to_square == inside
        )
        assert apply_action(state, legal_step, compiled).position.board[
            inside.rank * 9 + inside.file
        ] == Piece(side, "G", "G")
        for invalid in (outside, diagonal):
            with pytest.raises(IllegalActionError, match="not a legal semantic action"):
                apply_action(state, replace(legal_step, to_square=invalid), compiled)

    advisors = (
        (0, Square(4, 0), Square(8, 9), Square(3, 0), Square(4, 1), Square(2, 1)),
        (1, Square(4, 9), Square(0, 0), Square(5, 9), Square(4, 8), Square(6, 8)),
    )
    for side, own_g, enemy_g, source, inside, outside in advisors:
        state = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g), (side, "A", source)],
            side=side,
        )
        assert inside in _targets(state, compiled, source)
        assert outside not in _targets(state, compiled, source)


def test_elephant_eye_and_river_boundary_for_both_sides(product):
    _ruleset, compiled, _engine = product
    cases = (
        (0, Square(4, 0), Square(8, 9), Square(2, 0), Square(4, 2), Square(3, 1), Square(2, 4), Square(4, 6)),
        (1, Square(4, 9), Square(0, 0), Square(6, 9), Square(4, 7), Square(5, 8), Square(6, 5), Square(4, 3)),
    )
    for side, own_g, enemy_g, source, target, eye, river_source, river_target in cases:
        clear = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g), (side, "E", source)],
            side=side,
        )
        assert target in _targets(clear, compiled, source)

        eye_blocked = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "E", source), (1 - side, "S", eye),
            ],
            side=side,
        )
        assert target not in _targets(eye_blocked, compiled, source)

        river_cross = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "E", river_source),
            ],
            side=side,
        )
        assert river_target not in _targets(river_cross, compiled, river_source)


def test_horse_leg_blocks_the_matching_l_move_for_both_sides(product):
    _ruleset, compiled, _engine = product
    for side, own_g, enemy_g, source, target, leg in (
        (0, Square(4, 0), Square(8, 9), Square(4, 4), Square(6, 5), Square(5, 4)),
        (1, Square(4, 9), Square(0, 0), Square(4, 5), Square(6, 4), Square(5, 5)),
    ):
        clear = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g), (side, "H", source)],
            side=side,
        )
        assert target in _targets(clear, compiled, source)
        blocked = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "H", source), (1 - side, "S", leg),
            ],
            side=side,
        )
        assert target not in _targets(blocked, compiled, source)


def test_chariot_requires_clear_path_and_captures_without_hand_transfer(product):
    ruleset, compiled, engine = product
    assert ruleset.capture_disposition == "remove_from_game"
    compiled_capture_dispositions = {
        effect.disposition
        for pattern in compiled.ir.patterns
        for effect in pattern.effects
        if effect.kind == "remove"
    }
    assert compiled_capture_dispositions == {ruleset.capture_disposition}
    cases = (
        (
            0, Square(4, 0), Square(4, 9), Square(0, 4), Square(0, 7),
            Square(0, 6), Square(0, 8), 0, Square(4, 4),
        ),
        (
            1, Square(4, 9), Square(4, 0), Square(8, 5), Square(8, 2),
            Square(8, 3), Square(8, 1), 1, Square(4, 5),
        ),
    )
    for (
        side, own_g, enemy_g, source, target, blocker, successor_rook,
        screen_owner, screen_square,
    ) in cases:
        clear = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "R", source), (screen_owner, "S", screen_square),
            ],
            side=side,
        )
        assert target in _targets(clear, compiled, source)
        occupied = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "R", source), (side, "S", blocker),
                (screen_owner, "S", screen_square),
            ],
            side=side,
        )
        assert target not in _targets(occupied, compiled, source)
        capturable = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "R", source), (1 - side, "S", target),
                (1 - side, "R", successor_rook),
                (screen_owner, "S", screen_square),
            ],
            side=side,
        )
        assert not engine.in_check(capturable.position, 0)
        assert not engine.in_check(capturable.position, 1)
        for owner, palace_general in (
            (0, Square(4, 0)), (1, Square(4, 9)),
        ):
            owned = [
                piece for piece in capturable.position.board
                if piece is not None and piece.owner == owner
            ]
            inventory = Counter(piece.base_type_id for piece in owned)
            assert inventory["G"] == 1
            assert inventory["R"] <= 2
            assert inventory["S"] <= 5
            assert capturable.position.board[
                palace_general.rank * 9 + palace_general.file
            ] == Piece(owner, "G", "G")
        capture = next(
            action for action in legal_actions(capturable, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.from_square == source and action.to_square == target
        )
        assert capture.actor_type_id == "R"
        after = apply_action(capturable, capture, compiled)
        assert after.position.board[target.rank * 9 + target.file] == Piece(side, "R", "R")
        assert after.position.board[source.rank * 9 + source.file] is None
        assert after.ply_count == capturable.ply_count + 1
        assert sum(
            piece == Piece(side, "R", "R") for piece in after.position.board
        ) == 1
        assert after.position.side_to_move == 1 - side
        assert not any(
            piece == Piece(1 - side, "S", "S")
            for piece in after.position.board
        )
        assert after.position.hands == capturable.position.hands

        opponent_turn_parent = replace(
            capturable,
            position=replace(capturable.position, side_to_move=1 - side),
        )
        assert not any(
            isinstance(action, SemanticBoardMove)
            and action.from_square == successor_rook
            and action.to_square == target
            for action in legal_actions(opponent_turn_parent, compiled)
        )
        successor_capture = next(
            action for action in legal_actions(after, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.actor_type_id == "R"
            and action.from_square == successor_rook
            and action.to_square == target
        )
        assert (
            successor_capture.actor_type_id,
            successor_capture.from_square,
            successor_capture.to_square,
        ) == ("R", successor_rook, target)


def test_cannon_all_public_actions_require_exactly_one_screen_to_capture(product):
    _ruleset, compiled, _engine = product
    for side, own_g, enemy_g, source, one_screen, two_screen, target, quiet_target in (
        (0, Square(4, 0), Square(8, 9), Square(0, 4), Square(0, 5), (Square(0, 5), Square(0, 6)), Square(0, 7), Square(0, 7)),
        (1, Square(4, 9), Square(0, 0), Square(8, 5), Square(8, 4), (Square(8, 4), Square(8, 3)), Square(8, 2), Square(8, 2)),
    ):
        quiet_clear = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g), (side, "C", source)],
            side=side,
        )
        assert quiet_target in _targets(quiet_clear, compiled, source)

        no_screen = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "C", source), (1 - side, "S", target),
            ],
            side=side,
        )
        assert target not in _targets(no_screen, compiled, source)

        one = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "C", source), (side, "S", one_screen),
                (1 - side, "S", target),
            ],
            side=side,
        )
        assert target in _targets(one, compiled, source)
        capture = next(
            action for action in legal_actions(one, compiled)
            if isinstance(action, SemanticBoardMove)
            and action.from_square == source and action.to_square == target
        )
        after = apply_action(one, capture, compiled)
        assert after.position.board[target.rank * 9 + target.file] == Piece(side, "C", "C")
        assert after.position.side_to_move == 1 - side
        assert not any(
            piece == Piece(1 - side, "S", "S")
            for piece in after.position.board
        )
        assert after.position.hands == one.position.hands

        two = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "C", source), (side, "S", two_screen[0]),
                (1 - side, "S", two_screen[1]), (1 - side, "S", target),
            ],
            side=side,
        )
        assert target not in _targets(two, compiled, source)

        quiet_after_screen = _state(
            compiled,
            [
                (side, "G", own_g), (1 - side, "G", enemy_g),
                (side, "C", source), (1 - side, "S", one_screen),
            ],
            side=side,
        )
        assert quiet_target not in _targets(quiet_after_screen, compiled, source)


def test_soldier_forward_and_post_river_lateral_moves_for_both_sides(product):
    _ruleset, compiled, _engine = product
    for side, own_g, enemy_g, before, before_forward, before_sideways, after, after_forward, after_sideways, backward in (
        (0, Square(4, 0), Square(8, 9), Square(4, 3), Square(4, 4), Square(5, 3), Square(4, 5), Square(4, 6), Square(5, 5), Square(4, 4)),
        (1, Square(4, 9), Square(0, 0), Square(4, 6), Square(4, 5), Square(5, 6), Square(4, 4), Square(4, 3), Square(5, 4), Square(4, 5)),
    ):
        early = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g), (side, "S", before)],
            side=side,
        )
        targets = _targets(early, compiled, before)
        assert before_forward in targets
        assert before_sideways not in targets

        crossed = _state(
            compiled,
            [(side, "G", own_g), (1 - side, "G", enemy_g), (side, "S", after)],
            side=side,
        )
        targets = _targets(crossed, compiled, after)
        assert after_forward in targets
        assert after_sideways in targets
        assert backward not in targets


def test_facing_generals_screens_and_self_check_use_full_legal_actions(product):
    _ruleset, compiled, engine = product
    facing = _state(
        compiled,
        [(0, "G", Square(4, 0)), (1, "G", Square(4, 9))],
    )
    assert engine.in_check(facing.position, 0)
    assert engine.in_check(facing.position, 1)
    assert Square(4, 9) not in _targets(facing, compiled, Square(4, 0))
    screen = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
            (0, "S", Square(4, 5)),
        ],
        side=0,
    )
    assert not engine.in_check(screen.position, 0)
    screen_moves = _targets(screen, compiled, Square(4, 5))
    assert Square(5, 5) not in screen_moves

    two_screens = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
            (0, "S", Square(4, 5)), (0, "S", Square(4, 7)),
        ],
        side=0,
    )
    safe_shift = next(
        action for action in legal_actions(two_screens, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(4, 5) and action.to_square == Square(5, 5)
    )
    shifted = apply_action(two_screens, safe_shift, compiled)
    assert not engine.in_check(shifted.position, 0)
    illegal_last_screen = replace(safe_shift, to_square=Square(5, 5))
    with pytest.raises(IllegalActionError, match="not a legal semantic action"):
        apply_action(screen, illegal_last_screen, compiled)

    non_anchor = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(8, 9)),
            (1, "S", Square(4, 9)),
        ],
    )
    target_index = 9 * 9 + 4
    assert not engine.is_square_attacked(non_anchor.position, target_index, 0)
    assert Square(4, 9) not in _targets(non_anchor, compiled, Square(4, 0))


def test_no_legal_move_is_a_loss_without_needing_a_game(product):
    _ruleset, compiled, _engine = product
    pieces = [(0, "S", Square(file, rank)) for rank in range(10) for file in range(9)]
    pieces = [entry for entry in pieces if entry[2] != Square(3, 0) and entry[2] != Square(8, 0)]
    pieces.extend(((0, "G", Square(3, 0)), (1, "G", Square(8, 0))))
    state = _state(compiled, pieces, side=0)
    assert not legal_actions(state, compiled)
    state = replace(
        state,
        repetition_counts=((position_key(state.position, compiled), 1),),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.STALEMATE
    assert result.winner == 1


def test_checkmate_and_adjacent_stalemate_use_check_state(product):
    _ruleset, compiled, engine = product
    parent = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (0, "S", Square(4, 1)),
            (1, "G", Square(4, 9)),
            (1, "R", Square(3, 1)), (1, "R", Square(3, 2)),
            (1, "S", Square(5, 1)), (1, "H", Square(3, 3)),
        ],
        side=1,
    )
    assert not engine.in_check(parent.position, 0)
    assert not engine.in_check(parent.position, 1)
    checking_capture = next(
        action for action in legal_actions(parent, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(3, 1)
        and action.to_square == Square(4, 1)
    )
    checkmate = apply_action(parent, checking_capture, compiled)
    assert engine.in_check(checkmate.position, 0)
    assert not engine.in_check(checkmate.position, 1)
    assert legal_actions(checkmate, compiled) == []
    result = terminal_result(checkmate, compiled)
    assert result.status is TerminalStatus.CHECKMATE
    assert result.winner == 1

    stalemate = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
            (1, "H", Square(4, 4)), (1, "R", Square(3, 1)),
            (1, "S", Square(5, 1)), (1, "H", Square(3, 3)),
        ],
        side=0,
    )
    assert not engine.in_check(stalemate.position, 0)
    assert not engine.in_check(stalemate.position, 1)
    assert legal_actions(stalemate, compiled) == []
    result = terminal_result(stalemate, compiled)
    assert result.status is TerminalStatus.STALEMATE
    assert result.winner == 1

    piece_limits = {
        "G": 1, "A": 2, "E": 2, "H": 2, "R": 2, "C": 2, "S": 5,
    }
    for state in (parent, checkmate, stalemate):
        for owner, palace_ranks in ((0, range(3)), (1, range(7, 10))):
            owned = [
                (index, piece)
                for index, piece in enumerate(state.position.board)
                if piece is not None and piece.owner == owner
            ]
            inventory = Counter(piece.base_type_id for _index, piece in owned)
            assert inventory["G"] == 1
            assert all(
                inventory[tid] <= limit
                for tid, limit in piece_limits.items()
            )
            general_index = next(
                index for index, piece in owned if piece.base_type_id == "G"
            )
            assert general_index // 9 in palace_ranks
            assert 3 <= general_index % 9 <= 5


def test_xiangqi_checkmate_transition_runtime_push_pop_roundtrip(product):
    _ruleset, compiled, engine = product
    parent = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (0, "S", Square(4, 1)),
            (1, "G", Square(4, 9)),
            (1, "R", Square(3, 1)), (1, "R", Square(3, 2)),
            (1, "S", Square(5, 1)), (1, "H", Square(3, 3)),
        ],
        side=1,
    )
    key = repetition_identity_key(parent.position, compiled)
    counts = ((key, 1),)
    history = (HistoryRecord(key, -1, "", False),)
    parent = replace(
        parent,
        repetition_counts=counts,
        history=history,
        terminal_status=engine.terminal_result(
            parent.position, parent.ply_count, counts, history
        ),
    )
    assert parent.terminal_status.status is TerminalStatus.ONGOING
    public_actions = frozenset(legal_actions(parent, compiled))
    action = next(
        candidate
        for candidate in public_actions
        if isinstance(candidate, SemanticBoardMove)
        and candidate.from_square == Square(3, 1)
        and candidate.to_square == Square(4, 1)
    )
    runtime = SearchPathRuntime.from_state(parent, compiled)
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == public_actions
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        before_actions,
    )

    public_child = apply_action(parent, action, compiled)
    assert public_child.terminal_status.status is TerminalStatus.CHECKMATE
    assert public_child.terminal_status.winner == 1
    assert legal_actions(public_child, compiled) == []
    runtime.push(action)
    assert runtime.position == public_child.position
    assert runtime.terminal_status == public_child.terminal_status
    assert runtime.terminal_status.status is TerminalStatus.CHECKMATE
    assert runtime.terminal_status.winner == 1
    assert frozenset(runtime.legal_actions()) == frozenset(
        legal_actions(public_child, compiled)
    ) == frozenset()
    runtime.pop()
    runtime.assert_balanced()
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        frozenset(runtime.legal_actions()),
    )
    assert after == before


def test_xiangqi_stalemate_loss_transition_runtime_push_pop_roundtrip(product):
    _ruleset, compiled, engine = product
    parent = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
            (1, "H", Square(4, 4)), (1, "R", Square(2, 1)),
            (1, "S", Square(5, 1)), (1, "H", Square(3, 3)),
        ],
        side=1,
    )
    key = repetition_identity_key(parent.position, compiled)
    counts = ((key, 1),)
    history = (HistoryRecord(key, -1, "", False),)
    parent = replace(
        parent,
        repetition_counts=counts,
        history=history,
        terminal_status=engine.terminal_result(
            parent.position, parent.ply_count, counts, history
        ),
    )
    assert parent.terminal_status.status is TerminalStatus.ONGOING
    assert not engine.in_check(parent.position, 0)
    assert not engine.in_check(parent.position, 1)

    public_actions = frozenset(legal_actions(parent, compiled))
    action = next(
        candidate
        for candidate in public_actions
        if isinstance(candidate, SemanticBoardMove)
        and candidate.from_square == Square(2, 1)
        and candidate.to_square == Square(3, 1)
    )
    runtime = SearchPathRuntime.from_state(parent, compiled)
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == public_actions
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        before_actions,
    )

    public_child = apply_action(parent, action, compiled)
    assert public_child.position.side_to_move == 0
    assert not engine.in_check(public_child.position, 0)
    assert not engine.in_check(public_child.position, 1)
    assert legal_actions(public_child, compiled) == []
    assert public_child.terminal_status.status is TerminalStatus.STALEMATE
    assert public_child.terminal_status.winner == 1

    runtime.push(action)
    assert runtime.position == public_child.position
    assert runtime.terminal_status == public_child.terminal_status
    assert runtime.terminal_status.status is TerminalStatus.STALEMATE
    assert runtime.terminal_status.winner == 1
    assert frozenset(runtime.legal_actions()) == frozenset(
        legal_actions(public_child, compiled)
    ) == frozenset()
    runtime.pop()
    runtime.assert_balanced()
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        frozenset(runtime.legal_actions()),
    )
    assert after == before


def test_ranged_attacks_never_expose_general_capture_and_preserve_anchors(product):
    _ruleset, compiled, engine = product
    cases = (
        (
            "R", Square(4, 5), Square(8, 5),
            [
                (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
                (0, "R", Square(4, 5)),
                (1, "S", Square(4, 7)), (1, "S", Square(8, 5)),
            ],
        ),
        (
            "C", Square(4, 2), Square(0, 2),
            [
                (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
                (0, "C", Square(4, 2)),
                (1, "S", Square(4, 4)), (1, "S", Square(4, 6)),
                (1, "S", Square(2, 2)), (1, "S", Square(0, 2)),
            ],
        ),
    )
    piece_limits = {
        "G": 1, "A": 2, "E": 2, "H": 2, "R": 2, "C": 2, "S": 5,
    }
    facing_pattern = next(
        pattern for pattern in compiled.ir.patterns
        if pattern.name == "general_facing_capture"
    )

    for mover_type, source, ordinary_target, pieces in cases:
        state = _state(compiled, pieces, side=0)
        assert not engine.in_check(state.position, 0)
        assert not engine.in_check(state.position, 1)
        for owner, palace_ranks in ((0, range(3)), (1, range(7, 10))):
            owned = [
                (index, piece)
                for index, piece in enumerate(state.position.board)
                if piece is not None and piece.owner == owner
            ]
            inventory = Counter(piece.base_type_id for _index, piece in owned)
            assert inventory["G"] == 1
            assert all(
                inventory[tid] <= limit
                for tid, limit in piece_limits.items()
            )
            general_index = next(
                index for index, piece in owned if piece.base_type_id == "G"
            )
            assert general_index // 9 in palace_ranks
            assert 3 <= general_index % 9 <= 5

        actions = legal_actions(state, compiled)
        enemy_general_square = Square(4, 9)
        assert not any(
            isinstance(action, SemanticBoardMove)
            and action.to_square == enemy_general_square
            for action in actions
        )
        assert not any(
            action.pattern_id == facing_pattern.pattern_id
            for action in actions
        )

        ordinary_capture = next(
            action for action in actions
            if isinstance(action, SemanticBoardMove)
            and action.actor_type_id == mover_type
            and action.from_square == source
            and action.to_square == ordinary_target
        )
        captured = apply_action(state, ordinary_capture, compiled)
        assert captured.position.board[
            ordinary_target.rank * 9 + ordinary_target.file
        ] == Piece(0, mover_type, mover_type)

        for action in actions:
            successor = apply_action(state, action, compiled)
            assert all(
                sum(
                    piece is not None
                    and piece.owner == owner
                    and piece.base_type_id == "G"
                    for piece in successor.position.board
                ) == 1
                for owner in (0, 1)
            )


def test_xiangqi_ordinary_capture_push_pop_restores_full_semantic_state(product):
    _ruleset, compiled, engine = product
    state = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
            (0, "R", Square(4, 5)),
            (1, "S", Square(4, 7)), (1, "S", Square(8, 5)),
        ],
    )
    key = repetition_identity_key(state.position, compiled)
    counts = ((key, 1),)
    history = (HistoryRecord(key, -1, "", False),)
    state = replace(
        state,
        repetition_counts=counts,
        history=history,
        terminal_status=engine.terminal_result(
            state.position, 0, counts, history
        ),
    )

    public_actions = frozenset(legal_actions(state, compiled))
    runtime = SearchPathRuntime.from_state(state, compiled)
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == public_actions
    capture = next(
        action for action in public_actions
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(4, 5)
        and action.to_square == Square(8, 5)
    )
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        before_actions,
    )

    runtime.push(capture)
    assert runtime.position.board[4 * 9 + 5] is None
    assert runtime.position.board[5 * 9 + 8] == Piece(0, "R", "R")
    assert runtime.position.hands == state.position.hands
    assert runtime.ply_count == state.ply_count + 1
    runtime.pop()
    runtime.assert_balanced()

    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        frozenset(runtime.legal_actions()),
    )
    assert after == before
    assert runtime.position == state.position
    assert runtime.ply_count == state.ply_count
    assert runtime.terminal_status == state.terminal_status
    assert len(runtime.history) == len(state.history)
    assert runtime.repetition_counts == dict(state.repetition_counts)


def test_rectangular_transition_identity_and_repetition_cycle(product):
    _ruleset, compiled, engine = product
    state = _state(
        compiled,
        [
            (0, "G", Square(4, 0)), (1, "G", Square(5, 9)),
            (0, "R", Square(0, 4)), (1, "R", Square(8, 5)),
        ],
    )
    initial_key = repetition_identity_key(state.position, compiled)
    initial_counts = ((initial_key, 1),)
    state = replace(
        state,
        repetition_counts=initial_counts,
        history=(HistoryRecord(initial_key, -1, "", False),),
        terminal_status=engine.terminal_result(
            state.position, 0, initial_counts
        ),
    )
    alternate_side = replace(
        state.position,
        side_to_move=1,
    )
    assert repetition_identity_key(alternate_side, compiled) != initial_key

    cycle = (
        (Square(0, 4), Square(0, 5)),
        (Square(8, 5), Square(8, 4)),
        (Square(0, 5), Square(0, 4)),
        (Square(8, 4), Square(8, 5)),
    )
    for expected_count in (2, 3):
        for source, target in cycle:
            action = next(
                action for action in legal_actions(state, compiled)
                if isinstance(action, SemanticBoardMove)
                and action.from_square == source
                and action.to_square == target
            )
            state = apply_action(state, action, compiled)
        assert repetition_identity_key(state.position, compiled) == initial_key
        assert dict(state.repetition_counts)[initial_key] == expected_count
        assert state.position.board_shape == BoardShape(9, 10)
    assert state.terminal_status.status is TerminalStatus.ONGOING


def test_public_rectangular_unilateral_repeated_check_loses():
    ruleset = _ruleset_with_pieces(
        [
            (0, "G", Square(4, 0)), (1, "G", Square(4, 9)),
            (0, "S", Square(4, 3)), (0, "R", Square(5, 5)),
        ],
        repetition_policy="continuous_check_loss",
    )
    compiled = compile_ruleset_for_execution(ruleset)
    state = initial_state(compiled)
    initial_key = repetition_identity_key(state.position, compiled)
    cycle = (
        (Square(5, 5), Square(4, 5)),
        (Square(4, 9), Square(5, 9)),
        (Square(4, 5), Square(5, 5)),
        (Square(5, 9), Square(4, 9)),
    )
    for expected_count in (2, 3):
        for source, target in cycle:
            action = next(
                action for action in legal_actions(state, compiled)
                if isinstance(action, SemanticBoardMove)
                and action.from_square == source
                and action.to_square == target
            )
            state = apply_action(state, action, compiled)
            assert state.history[-1].gave_check is (state.history[-1].actor == 0)
        assert repetition_identity_key(state.position, compiled) == initial_key
        assert dict(state.repetition_counts)[initial_key] == expected_count
    assert state.terminal_status.status is TerminalStatus.PERPETUAL_CHECK
    assert state.terminal_status.winner == 1


def test_synthetic_rectangular_mutual_repeated_check_draw_only():
    ruleset = _ruleset_with_pieces(
        [
            (0, "G", Square(0, 0)), (1, "G", Square(4, 1)),
            (0, "R", Square(2, 0)), (1, "R", Square(4, 0)),
        ],
        repetition_policy="continuous_check_loss",
        mutual_fixture=True,
    )
    compiled = compile_ruleset_for_execution(ruleset)
    state = initial_state(compiled)
    engine = SemanticEngine(compiled)
    assert not engine.in_check(state.position, 0)
    assert not engine.in_check(state.position, 1)
    prefix = next(
        action for action in legal_actions(state, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.from_square == Square(2, 0)
        and action.to_square == Square(2, 1)
    )
    state = apply_action(state, prefix, compiled)
    assert state.history[-1].gave_check
    assert engine.in_check(state.position, 0)
    assert engine.in_check(state.position, 1)
    cycle_key = repetition_identity_key(state.position, compiled)
    cycle = (
        (Square(4, 0), Square(3, 0)),
        (Square(2, 1), Square(3, 1)),
        (Square(3, 0), Square(4, 0)),
        (Square(3, 1), Square(2, 1)),
    )
    for expected_count in (2, 3):
        for source, target in cycle:
            action = next(
                action for action in legal_actions(state, compiled)
                if isinstance(action, SemanticBoardMove)
                and action.from_square == source
                and action.to_square == target
            )
            state = apply_action(state, action, compiled)
            assert state.history[-1].gave_check
        assert repetition_identity_key(state.position, compiled) == cycle_key
        assert dict(state.repetition_counts)[cycle_key] == expected_count
    assert state.terminal_status.status is TerminalStatus.REPETITION
