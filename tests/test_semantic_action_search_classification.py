"""F24B parity tests for legacy and lossless semantic public actions."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]

from generic_chess.ai.alphabeta.ordering import MoveOrderer, StagedMovePicker
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.search import _runtime_noisy_actions
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.actions import (
    BoardMove,
    DropMove,
    SemanticBoardMove,
    SemanticDropMove,
    action_drop_base_type_id,
    action_is_board,
    action_is_drop,
    action_promotion_target_id,
    action_source_square,
    action_target_square,
)
from generic_chess.core.coordinates import Square
from generic_chess.core.attacks import is_in_check
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks, build_promotion
from conftest import make_state


def _semantic_board(action, *, promotion=None):
    return SemanticBoardMove(
        pattern_id="f24b-pattern",
        geometry_id="f24b-geometry",
        actor_type_id="R" if isinstance(action, BoardMove) else action.actor_type_id,
        from_square=action.from_square,
        to_square=action.to_square,
        promotion_target_id=action.promotion_target_id if promotion is None else promotion,
    )


def _semantic_drop(action):
    return SemanticDropMove(
        pattern_id="f24b-drop-pattern",
        geometry_id="f24b-drop-geometry",
        base_type_id=action.base_type_id,
        to_square=action.to_square,
    )


def _classify(compiled, state, action, child):
    stats = SearchStatistics()
    noisy = classify_noisy(state, [(action, child)], compiled, stats)
    return noisy, stats


def checking_child_is_check(compiled, child):
    return semantic_engine_for(compiled).in_check(child.position, 1)


def test_public_action_shape_helpers_preserve_semantic_identity_and_fields():
    board = SemanticBoardMove("p", "g", "R", Square(0, 0), Square(1, 0), "G")
    drop = SemanticDropMove("p", "g", "P", Square(1, 1))
    assert action_is_board(board) is True
    assert action_is_drop(board) is False
    assert action_source_square(board) == Square(0, 0)
    assert action_target_square(board) == Square(1, 0)
    assert action_promotion_target_id(board) == "G"
    assert action_is_drop(drop) is True
    assert action_is_board(drop) is False
    assert action_source_square(drop) is None
    assert action_target_square(drop) == Square(1, 1)
    assert action_drop_base_type_id(drop) == "P"
    assert board.pattern_id == "p" and board.geometry_id == "g"


def test_qsearch_legacy_semantic_board_capture_promotion_and_quiet_parity():
    compiled = build_4x4_rooks()
    capture_state = make_state(compiled, ["...K", "....", ".r..", "..R."])
    capture = BoardMove(Square(2, 0), Square(1, 1))
    quiet = BoardMove(Square(2, 0), Square(2, 1))
    for legacy, semantic, expected, counter in (
        (capture, _semantic_board(capture), True, "capture_qactions"),
        (quiet, _semantic_board(quiet), False, None),
    ):
        for action in (legacy, semantic):
            noisy, stats = _classify(compiled, capture_state, action, capture_state)
            assert (noisy == [action]) is expected
            if counter:
                assert getattr(stats, counter) == 1
            else:
                assert stats.capture_qactions == 0
            if noisy:
                assert noisy[0] is action

    promotion_compiled = build_promotion()
    promotion_state = GameSession(promotion_compiled).state
    promotion = BoardMove(Square(4, 6), Square(4, 7), "G")
    for action in (promotion, _semantic_board(promotion)):
        noisy, stats = _classify(promotion_compiled, promotion_state, action, promotion_state)
        assert noisy == [action]
        assert noisy[0] is action
        assert stats.promotion_qactions == 1

    capture_promotion_state = make_state(
        promotion_compiled,
        ["....p..k", "....P...", "........", "........", "........", "........", "........", "K......."],
    )
    for action in (promotion, _semantic_board(promotion)):
        noisy, stats = _classify(
            promotion_compiled, capture_promotion_state, action, capture_promotion_state
        )
        assert noisy == [action]
        assert noisy[0] is action
        assert stats.promotion_qactions == 1
        assert stats.capture_qactions == 0


def test_qsearch_legacy_semantic_check_and_drop_diagnostics_parity():
    compiled = build_4x4_rooks()
    check_state = make_state(compiled, ["..k.", "....", "R...", "K..."])
    checking_pair = next(
        (action, child)
        for action, child in legal_successors(check_state, compiled)
        if isinstance(action, BoardMove)
        and action.promotion_target_id is None
        and is_in_check(child.position, 1, compiled)
    )
    legacy, child = checking_pair
    semantic = _semantic_board(legacy)
    for action in (legacy, semantic):
        noisy, stats = _classify(compiled, check_state, action, child)
        assert noisy == [action]
        assert noisy[0] is action
        assert stats.checking_move_qactions == 1
        assert stats.checking_drop_qactions == 0

    checking_drop_state = make_state(
        compiled, ["...k", "....", "....", "K..."], hands=([("R", 1)], ())
    )
    checking_drop, checking_child = next(
        (action, child)
        for action, child in legal_successors(checking_drop_state, compiled)
        if isinstance(action, DropMove)
        and child.terminal_status.status is TerminalStatus.ONGOING
        and is_in_check(child.position, 1, compiled)
    )
    for action in (checking_drop, _semantic_drop(checking_drop)):
        noisy, stats = _classify(compiled, checking_drop_state, action, checking_child)
        assert noisy == [action]
        assert noisy[0] is action
        assert stats.checking_drop_qactions == 1
        assert stats.checking_move_qactions == 0

    nonchecking_state = make_state(
        compiled, ["...K", "....", "r...", "kr.."], hands=([("R", 2)], ())
    )
    nonchecking_drop, nonchecking_child = next(
        (action, child)
        for action, child in legal_successors(nonchecking_state, compiled)
        if isinstance(action, DropMove)
    )
    for action in (nonchecking_drop, _semantic_drop(nonchecking_drop)):
        noisy, stats = _classify(compiled, nonchecking_state, action, nonchecking_child)
        assert noisy == []
        assert stats.nonchecking_drop_excluded == 1

    terminal_child = replace(
        check_state,
        terminal_status=TerminalResult(TerminalStatus.STALEMATE),
    )
    terminal_action = BoardMove(Square(2, 2), Square(1, 3))
    for action in (terminal_action, _semantic_board(terminal_action)):
        noisy, stats = _classify(compiled, check_state, action, terminal_child)
        assert noisy == [action]
        assert noisy[0] is action
        assert stats.capture_qactions == 0
        assert stats.promotion_qactions == 0


def test_full_and_staged_ordering_put_semantic_variants_in_same_tactical_stages():
    compiled = build_promotion()
    state = make_state(
        compiled,
        [".......k", "....P...", "....p...", "........", "........", "........", "........", "K......."],
    )
    capture = BoardMove(Square(4, 6), Square(4, 5))
    promotion = BoardMove(Square(4, 6), Square(4, 7), "G")
    quiet = BoardMove(Square(5, 6), Square(5, 5))
    actions = [
        quiet,
        _semantic_board(promotion),
        capture,
        _semantic_board(capture),
        promotion,
    ]
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, EvaluationConfig()), EvaluationConfig())
    orderer = MoveOrderer()
    ordered = orderer.order(state, actions, evaluator, 1, None, None, SearchTuning())
    assert set(ordered[:2]) == {capture, _semantic_board(capture)}
    assert set(ordered[2:4]) == {promotion, _semantic_board(promotion)}
    assert ordered[4] is quiet

    stats = SearchStatistics()
    picker = StagedMovePicker(
        state, actions, evaluator, 1, None, None, orderer, SearchTuning(), stats
    )
    staged = list(picker)
    assert set(staged[:2]) == {capture, _semantic_board(capture)}
    assert set(staged[2:4]) == {promotion, _semantic_board(promotion)}
    assert staged[4] is quiet
    assert stats.move_picker_yielded_by_stage == {
        "good_capture": 2,
        "promotion": 2,
        "quiet": 1,
    }


def test_standard_shogi_semantic_capture_promotion_and_drop_cases():
    from scripts import audit_f23v_minimal_analytic_evaluator_r1 as f23v

    compiled = f23v._compile("SHOGI_LIKE", 3)
    capture_state = f23v._state(
        compiled,
        {"rows": [".pK", "kP.", "..R"], "hands": ((), ()), "side_to_move": 0},
    )
    capture, capture_child = next(
        (action, child)
        for action, child in legal_successors(capture_state, compiled)
        if isinstance(action, SemanticBoardMove)
        and capture_state.position.board[action.to_square.rank * 3 + action.to_square.file] is not None
        and capture_state.position.board[action.to_square.rank * 3 + action.to_square.file].owner == 1
    )
    noisy, stats = _classify(compiled, capture_state, capture, capture_child)
    assert noisy == [capture]
    assert noisy[0] is capture
    assert stats.capture_qactions == 1

    promotion_state = f23v._state(
        compiled,
        {"rows": ["K..", ".P.", "..k"], "hands": ((), ()), "side_to_move": 0},
    )
    promotion, promotion_child = next(
        (action, child)
        for action, child in legal_successors(promotion_state, compiled)
        if isinstance(action, SemanticBoardMove)
        and action.promotion_target_id is not None
    )
    noisy, stats = _classify(compiled, promotion_state, promotion, promotion_child)
    assert noisy == [promotion]
    assert noisy[0] is promotion
    assert stats.promotion_qactions == 1

    drop_state = f23v._state(
        compiled,
        {"rows": ["k.K", "R..", "..."], "hands": ((("P", 1),), ()), "side_to_move": 0},
    )
    checking_drop, checking_child = next(
        (action, child)
        for action, child in legal_successors(drop_state, compiled)
        if isinstance(action, SemanticDropMove)
        and checking_child_is_check(compiled, child)
        and child.terminal_status.status is TerminalStatus.ONGOING
    )
    noisy, stats = _classify(compiled, drop_state, checking_drop, checking_child)
    assert noisy == [checking_drop]
    assert noisy[0] is checking_drop
    assert stats.checking_drop_qactions == 1

    control_state = f23v._state(
        compiled,
        {"rows": ["..K", "k..", "..R"], "hands": ((("P", 1),), ()), "side_to_move": 0},
    )
    control_drop, control_child = next(
        (action, child)
        for action, child in legal_successors(control_state, compiled)
        if isinstance(action, SemanticDropMove)
        and child.terminal_status.status is TerminalStatus.ONGOING
        and not checking_child_is_check(compiled, child)
    )
    noisy, stats = _classify(compiled, control_state, control_drop, control_child)
    assert noisy == []
    assert stats.nonchecking_drop_excluded == 1

    runtime = SearchPathRuntime.from_state(capture_state, compiled)
    ctx = SimpleNamespace(
        runtime=runtime,
        compiled=compiled,
        stats=SearchStatistics(),
        checkpoint=lambda: None,
    )
    runtime_noisy = _runtime_noisy_actions(ctx, [capture])
    assert runtime_noisy == [capture]
    assert runtime_noisy[0] is capture
    assert ctx.stats.capture_qactions == 1
    runtime.assert_balanced()


def test_classification_patch_has_no_game_or_piece_specific_branches():
    paths = (
        "generic_chess/core/actions.py",
        "generic_chess/ai/alphabeta/quiescence.py",
        "generic_chess/ai/alphabeta/ordering.py",
        "generic_chess/ai/alphabeta/search.py",
    )
    forbidden = ("SHOGI", "CHESS", "XIANGQI", "JANGGI", '"P"', '"K"')
    for relative in paths:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden), relative
