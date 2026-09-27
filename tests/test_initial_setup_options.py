from dataclasses import replace

import pytest

from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleInitialSetupOption,
    compute_fingerprint,
    ruleset_to_dict,
)
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.serialization import (
    deserialize_game_record,
    serialize_game_record,
)
from generic_chess.session.session import GameSession, SessionRecordError

from conftest import board_move, king_type, make_ruleset, sq, T
from generic_chess.core.movement import RayAtom


def _ruleset_with_two_layouts():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    base = make_ruleset(
        5,
        [king_type(), rook],
        lines=["....k", ".....", "R....", ".....", "K...."],
    )
    alternate = make_ruleset(
        5,
        [king_type(), rook],
        lines=["....k", ".....", ".R...", ".....", "K...."],
    )
    alternate_c = make_ruleset(
        5,
        [king_type(), rook],
        lines=["....k", "R....", ".....", ".....", "K...."],
    )
    return replace(
        base,
        initial_setup_options=(
            RuleInitialSetupOption("rook-file-b", alternate.initial_position),
            RuleInitialSetupOption("rook-rank-d", alternate_c.initial_position),
        ),
    )


def test_absent_options_preserve_default_serialization_fingerprint_and_record():
    ruleset = make_ruleset(5, [king_type()])
    explicit_empty = replace(ruleset, initial_setup_options=())
    assert "initial_setup_options" not in ruleset_to_dict(ruleset)
    assert compute_fingerprint(ruleset) == compute_fingerprint(explicit_empty)
    compiled = compile_ruleset(ruleset)
    assert initial_state(compiled) == initial_state(compile_ruleset(explicit_empty))
    session = GameSession(compiled)
    assert session.to_record().schema_version == 1
    assert "initial_setup_key" not in serialize_game_record(session.to_record())


def test_two_layouts_are_selectable_stable_and_replayable():
    ruleset = _ruleset_with_two_layouts()
    reversed_ruleset = replace(
        ruleset,
        initial_setup_options=tuple(reversed(ruleset.initial_setup_options)),
    )
    assert compute_fingerprint(ruleset) == compute_fingerprint(reversed_ruleset)
    compiled = compile_ruleset(ruleset)
    reversed_compiled = compile_ruleset(reversed_ruleset)

    default_state = initial_state(compiled)
    alternate_state = initial_state(compiled, "rook-file-b")
    assert default_state.position != alternate_state.position
    assert initial_state(reversed_compiled, "rook-file-b").position == alternate_state.position

    for setup_key, rook_source, rook_target in (
        (None, sq(0, 2), sq(0, 3)),
        ("rook-file-b", sq(1, 2), sq(1, 3)),
        ("rook-rank-d", sq(0, 3), sq(1, 3)),
    ):
        session = GameSession(compiled, setup_key)
        action = board_move(
            rook_source.file, rook_source.rank, rook_target.file, rook_target.rank
        )
        session.submit(action)
        serialized = serialize_game_record(session.to_record())
        record = deserialize_game_record(serialized)
        if setup_key is None:
            # Default-start records retain their old schema and wire format.
            assert record.schema_version == 1
            assert record.initial_setup_key is None
        else:
            assert record.schema_version == 3
            assert record.initial_setup_key == setup_key
        replayed = GameSession.replay(compiled, record)
        assert replayed.state == session.state
        assert replayed.history == session.history
        assert reconstruct_history_provenance(replayed.state, compiled).status == "verified"


def test_unknown_and_duplicate_setup_keys_or_positions_fail_closed():
    ruleset = _ruleset_with_two_layouts()
    compiled = compile_ruleset(ruleset)
    with pytest.raises(ValueError, match="unknown initial setup key"):
        initial_state(compiled, "missing")

    duplicate_key = replace(
        ruleset,
        initial_setup_options=(
            ruleset.initial_setup_options[0],
            RuleInitialSetupOption("rook-file-b", ruleset.initial_position),
        ),
    )
    with pytest.raises(RuleValidationError, match="INITIAL_SETUP_KEY_DUPLICATE"):
        compile_ruleset(duplicate_key)

    duplicate_position = replace(
        ruleset,
        initial_setup_options=(
            RuleInitialSetupOption("same-board", ruleset.initial_position),
        ),
    )
    with pytest.raises(RuleValidationError, match="INITIAL_SETUP_POSITION_DUPLICATE"):
        compile_ruleset(duplicate_position)

    unsafe_board = [list(row) for row in ruleset.initial_position]
    source_rook = ruleset.initial_position[2][0]
    unsafe_board[2][0] = None
    unsafe_board[2][4] = source_rook
    unsafe_layout = replace(
        ruleset,
        initial_setup_options=(
            RuleInitialSetupOption(
                "rook-attacks-anchor", tuple(tuple(row) for row in unsafe_board)
            ),
        ),
    )
    with pytest.raises(RuleValidationError, match="INITIAL_ANCHOR_ATTACKED"):
        compile_ruleset(unsafe_layout)


def test_record_setup_key_is_checked_before_replay():
    ruleset = _ruleset_with_two_layouts()
    compiled = compile_ruleset(ruleset)
    session = GameSession(compiled, "rook-file-b")
    record = session.to_record()
    bad_record = replace(record, initial_setup_key="not-declared")
    with pytest.raises(SessionRecordError, match="unknown initial setup"):
        GameSession.replay(compiled, bad_record)


def test_semantic_ruleset_can_select_and_replay_an_alternate_start():
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    base = build_western_chess_ruleset()
    board = [list(row) for row in base.initial_position]
    knight = board[0][1]
    board[0][1] = None
    board[2][2] = knight
    option = RuleInitialSetupOption("knight-advanced", tuple(tuple(row) for row in board))
    ruleset = replace(base, initial_setup_options=(option,))
    compiled = compile_ruleset_for_execution(ruleset)
    session = GameSession(compiled, "knight-advanced")
    session.submit(session.legal_actions()[0])
    restored = GameSession.replay(
        compiled, deserialize_game_record(serialize_game_record(session.to_record()))
    )
    assert restored.state == session.state
    assert reconstruct_history_provenance(restored.state, compiled).status == "verified"


def test_rectangular_semantic_ruleset_can_select_an_alternate_start():
    from test_rectangular_public_semantic_execution import _toy_rectangular_ruleset

    base = _toy_rectangular_ruleset()
    board = [list(row) for row in base.initial_position]
    mover = board[0][2]
    board[0][2] = None
    board[0][3] = mover
    ruleset = replace(
        base,
        initial_setup_options=(
            RuleInitialSetupOption("mover-file-d", tuple(tuple(row) for row in board)),
        ),
    )
    compiled = compile_ruleset_for_execution(ruleset)
    session = GameSession(compiled, "mover-file-d")
    session.submit(session.legal_actions()[0])
    restored = GameSession.replay(
        compiled, deserialize_game_record(serialize_game_record(session.to_record()))
    )
    assert restored.state == session.state
    assert reconstruct_history_provenance(restored.state, compiled).status == "verified"
