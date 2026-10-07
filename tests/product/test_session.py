"""GameSession behavior: submission, records, resignation, terminal mapping."""

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.result import SessionStatus, session_result_from_terminal
from generic_chess.session.session import GameSession, SessionFinishedError

from conftest import (
    board_move,
    king_type,
    make_compiled,
    make_ruleset,
    sq,
    T,
)


def _generated_session(seed=42):
    game = generate_game(GeneratorConfig(seed=seed))
    return GameSession(game.compiled_ruleset)


def test_initial_session_state():
    session = _generated_session()
    assert session.state.ply_count == 0
    assert session.history == ()
    assert session.result.status is SessionStatus.ONGOING
    assert session.result.winner is None
    assert session.compiled.ruleset_fingerprint == session.state.position.ruleset_fingerprint


def test_submit_legal_action_and_record_fields():
    session = _generated_session()
    actions = session.legal_actions()
    action = actions[0]
    before_key = position_key(session.state.position, session.compiled)
    new_state = session.submit(action)
    assert session.state is new_state
    assert session.state.ply_count == 1
    assert len(session.history) == 1
    rec = session.history[0]
    assert rec.ply == 1
    assert rec.player == 0
    assert rec.action == action
    assert rec.before_key == before_key
    assert rec.after_key == position_key(new_state.position, session.compiled)
    assert rec.after_key != rec.before_key


def test_history_order_and_players_alternate():
    session = _generated_session()
    for _ in range(4):
        session.submit(session.legal_actions()[0])
    assert [rec.player for rec in session.history] == [0, 1, 0, 1]
    assert [rec.ply for rec in session.history] == [1, 2, 3, 4]


def test_illegal_action_leaves_no_partial_update():
    session = _generated_session()
    actions = session.legal_actions()
    forged = BoardMove(sq(5, 5), sq(5, 6))  # move from an empty square
    assert forged not in actions
    before_state = session.state
    before_history = session.history
    before_result = session.result
    with pytest.raises(ValueError):
        session.submit(forged)
    assert session.state == before_state
    assert session.history == before_history
    assert session.result == before_result


def test_submit_after_terminal_rejected():
    rook = T("R", RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    compiled = make_compiled(
        8,
        [king_type(), rook],
        lines=[
            "........",  # rank 7
            "........",
            "........",
            ".R......",  # rank 4
            "........",
            "........",
            ".....R..",  # rank 1
            "k.K.....",  # rank 0
        ],
    )
    session = GameSession(compiled)
    session.submit(board_move(1, 4, 0, 4))  # mate in one
    assert session.result.status is SessionStatus.CHECKMATE
    assert session.result.winner == 0
    with pytest.raises(SessionFinishedError):
        session.submit(board_move(0, 4, 0, 3))


def test_terminal_status_mapping():
    cases = [
        (TerminalResult(TerminalStatus.ONGOING, None), SessionStatus.ONGOING, None),
        (TerminalResult(TerminalStatus.CHECKMATE, 1), SessionStatus.CHECKMATE, 1),
        (TerminalResult(TerminalStatus.STALEMATE, None), SessionStatus.STALEMATE, None),
        (TerminalResult(TerminalStatus.REPETITION, None), SessionStatus.REPETITION, None),
        (TerminalResult(TerminalStatus.MAX_PLY, None), SessionStatus.MAX_PLY, None),
    ]
    for terminal, status, winner in cases:
        result = session_result_from_terminal(terminal)
        assert result.status is status
        assert result.winner == winner
        assert result.resigned_by is None


def test_stalemate_reached_through_session():
    rook = T("R", RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    compiled = make_compiled(
        8,
        [king_type(), rook],
        lines=[
            "........",  # rank 7
            "........",
            "........",
            "........",
            "........",
            ".....R..",  # rank 2
            "........",
            "k.K.....",  # rank 0
        ],
    )
    session = GameSession(compiled)
    session.submit(board_move(5, 2, 5, 1))
    assert session.result.status is SessionStatus.STALEMATE
    assert session.result.winner is None


def _shuttle_session(repetition_limit, max_ply):
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    ruleset = make_ruleset(
        8,
        [king_type(), rook],
        lines=[
            ".......k",  # rank 7
            "........",
            "....r...",  # rank 5
            "........",
            "........",
            "...R....",  # rank 2
            "........",
            "K.......",  # rank 0
        ],
        repetition_limit=repetition_limit,
        max_ply=max_ply,
    )
    from generic_chess.rules.compiler import compile_ruleset

    return GameSession(compile_ruleset(ruleset))


def test_repetition_mapped_through_session():
    session = _shuttle_session(repetition_limit=4, max_ply=512)
    moves = [
        board_move(3, 2, 3, 3),
        board_move(4, 5, 4, 4),
        board_move(3, 3, 3, 2),
        board_move(4, 4, 4, 5),
    ]
    for _ in range(3):
        for move in moves:
            session.submit(move)
    assert session.result.status is SessionStatus.REPETITION
    assert session.result.winner is None


def test_max_ply_mapped_through_session():
    session = _shuttle_session(repetition_limit=1000, max_ply=8)
    moves = [
        board_move(3, 2, 3, 3),
        board_move(4, 5, 4, 4),
        board_move(3, 3, 3, 2),
        board_move(4, 4, 4, 5),
    ]
    for i in range(8):
        session.submit(moves[i % 4])
    assert session.result.status is SessionStatus.MAX_PLY


def test_resign_by_current_player():
    session = _generated_session()
    session.submit(session.legal_actions()[0])  # now player 1 to move
    result = session.resign()
    assert result.status is SessionStatus.RESIGNATION
    assert result.resigned_by == 1
    assert result.winner == 0
    assert session.to_record().resigned_by == 1


def test_resign_on_ongoing_initial_position():
    session = _generated_session()
    result = session.resign()
    assert result.resigned_by == 0
    assert result.winner == 1


def test_double_resign_rejected():
    session = _generated_session()
    session.resign()
    with pytest.raises(SessionFinishedError):
        session.resign()


def test_resign_after_terminal_rejected():
    rook = T("R", RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    compiled = make_compiled(
        8,
        [king_type(), rook],
        lines=[
            "........",
            "........",
            "........",
            ".R......",
            "........",
            "........",
            ".....R..",
            "k.K.....",
        ],
    )
    session = GameSession(compiled)
    session.submit(board_move(1, 4, 0, 4))
    assert session.result.status is SessionStatus.CHECKMATE
    with pytest.raises(SessionFinishedError):
        session.resign()


def test_history_is_readonly_tuple():
    session = _generated_session()
    session.submit(session.legal_actions()[0])
    assert isinstance(session.history, tuple)
    with pytest.raises(TypeError):
        session.history[0] = None  # type: ignore[index]
