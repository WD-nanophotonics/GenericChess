"""GameRecord replay: full reconstruction and rejection of bad records."""

import json

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.record import GameRecord
from generic_chess.session.session import GameSession, SessionRecordError
from generic_chess.session.serialization import deserialize_game_record

from conftest import board_move, king_type, make_compiled, make_ruleset, sq, T


def _generated_pair(seed_a=42, seed_b=43):
    a = GameSession(generate_game(GeneratorConfig(seed=seed_a)).compiled_ruleset)
    b = GameSession(generate_game(GeneratorConfig(seed=seed_b)).compiled_ruleset)
    return a, b


def test_normal_record_replays_identically():
    session, _ = _generated_pair()
    for _ in range(6):
        session.submit(session.legal_actions()[0])
    record = session.to_record()
    rebuilt = GameSession.replay(session.compiled, record)
    assert rebuilt.state == session.state
    assert rebuilt.history == session.history
    assert rebuilt.result == session.result
    assert position_key(rebuilt.state.position, rebuilt.compiled) == position_key(
        session.state.position, session.compiled
    )


def test_record_with_capture_and_drop_replays():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    filler = T("F", LeapAtom((1, 0)))
    compiled = make_compiled(
        8,
        [king_type(), rook, filler],
        lines=[
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRf.....",
        ],
    )
    session = GameSession(compiled)
    session.submit(board_move(1, 0, 2, 0))  # capture -> hand
    session.submit(board_move(7, 7, 6, 7))  # P1 king move
    session.submit(DropMove("F", sq(3, 3)))  # drop
    rebuilt = GameSession.replay(compiled, session.to_record())
    assert rebuilt.state == session.state
    assert rebuilt.history == session.history
    assert [type(a).__name__ for a in rebuilt.to_record().actions] == [
        "BoardMove",
        "BoardMove",
        "DropMove",
    ]


def test_record_with_promotion_and_resignation_replays():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, -1)))
    compiled = make_compiled(
        8,
        [king_type(), pawn, gold],
        auto_promotion=True,
        lines=[
            ".......k",
            "....P...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    session = GameSession(compiled)
    session.submit(BoardMove(sq(4, 6), sq(4, 7), "G"))  # forced promotion
    session.resign()
    rebuilt = GameSession.replay(compiled, session.to_record())
    assert rebuilt.state == session.state
    assert rebuilt.result == session.result
    assert rebuilt.result.resigned_by == 1
    promoted = [p for p in rebuilt.state.position.board if p is not None and p.promoted]
    assert len(promoted) == 1
    assert promoted[0].current_type_id == "G"
    assert promoted[0].base_type_id == "P"


def test_empty_record_replays_as_initial():
    session, _ = _generated_pair()
    record = session.to_record()
    rebuilt = GameSession.replay(session.compiled, record)
    assert rebuilt.state == session.state
    assert rebuilt.result.status.value == "ongoing"


def test_fingerprint_mismatch_rejected():
    session_a, session_b = _generated_pair()
    record = session_a.to_record()
    with pytest.raises(SessionRecordError):
        GameSession.replay(session_b.compiled, record)


def test_schema_version_rejected():
    session, _ = _generated_pair()
    record = GameRecord(
        schema_version=2,
        ruleset_fingerprint=session.compiled.ruleset_fingerprint,
        actions=(),
        resigned_by=None,
    )
    with pytest.raises(SessionRecordError):
        GameSession.replay(session.compiled, record)


def test_illegal_action_in_record_rejected():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    compiled = make_compiled(
        8,
        [king_type(), pawn, gold],
        auto_promotion=True,
        lines=[
            ".......k",
            "....P...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    session = GameSession(compiled)
    bad = GameRecord(
        schema_version=1,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        actions=(BoardMove(sq(4, 6), sq(4, 5)),),  # backward pawn move
        resigned_by=None,
    )
    with pytest.raises(SessionRecordError):
        GameSession.replay(compiled, bad)


def test_extra_action_after_terminal_rejected():
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
    session.submit(board_move(1, 4, 0, 4))  # mate
    assert session.result.status.value == "checkmate"
    record = session.to_record()
    record = GameRecord(
        schema_version=1,
        ruleset_fingerprint=record.ruleset_fingerprint,
        actions=record.actions + (board_move(0, 4, 0, 3),),
        resigned_by=None,
    )
    with pytest.raises(SessionRecordError):
        GameSession.replay(compiled, record)


def test_wrong_resigned_by_rejected():
    session, _ = _generated_pair()
    session.submit(session.legal_actions()[0])  # player 1 to move now
    record = session.to_record()
    bad = GameRecord(
        schema_version=1,
        ruleset_fingerprint=record.ruleset_fingerprint,
        actions=record.actions,
        resigned_by=0,  # wrong: player 1 is the side to move
    )
    with pytest.raises(SessionRecordError):
        GameSession.replay(session.compiled, bad)


def test_resignation_after_terminal_in_record_rejected():
    session, _ = _generated_pair()
    # Build a record whose actions end in a terminal position.
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
    s = GameSession(compiled)
    s.submit(board_move(1, 4, 0, 4))
    record = s.to_record()
    bad = GameRecord(
        schema_version=1,
        ruleset_fingerprint=record.ruleset_fingerprint,
        actions=record.actions,
        resigned_by=1,  # resignation after checkmate is invalid
    )
    with pytest.raises(SessionRecordError):
        GameSession.replay(compiled, bad)


def test_malformed_json_raises_session_record_error():
    with pytest.raises(SessionRecordError):
        deserialize_game_record("{not json")


def test_deserializer_rejects_bad_kind():
    session, _ = _generated_pair()
    data = {
        "schema_version": 1,
        "ruleset_fingerprint": session.compiled.ruleset_fingerprint,
        "actions": [{"kind": "teleport", "from": [0, 0], "to": [1, 1]}],
        "resigned_by": None,
    }
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_deserializer_rejects_bool_coordinates():
    session, _ = _generated_pair()
    data = {
        "schema_version": 1,
        "ruleset_fingerprint": session.compiled.ruleset_fingerprint,
        "actions": [{"kind": "board", "from": [0, True], "to": [1, 1]}],
        "resigned_by": None,
    }
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))
