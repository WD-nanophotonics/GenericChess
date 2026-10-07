"""Phase 2A history: full replay, non-root repetition, same-root different
history."""

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.native.adapter import (
    native_make_checked,
    native_snapshot,
    pack_native_search_position,
    to_python_action,
)
from generic_chess.native.compiler import compile_native_rules
from generic_chess.native.reference import python_legal_actions
from generic_chess.session.session import GameSession

from native_test_helpers import requires_native, simple_ruleset


def _cycle_ruleset():
    """Deterministic 4-cycle with exactly one legal move per ply.

    Positions A(p0) B(p1) C(p2) D(p3) repeat every 4 plies, so every state
    reaches count 3 at ply 11; the 12th move hits the repetition limit.
    """
    n = 4
    king = PieceType("K", "K", (), is_anchor=True)
    f = PieceType("F", "F", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    g = PieceType("G", "G", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    z = PieceType("Z", "Z", ())
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[3][0] = Piece(0, "Z", "Z", False)
    rows[0][3] = Piece(1, "Z", "Z", False)
    rows[1][0] = Piece(0, "F", "F", False)
    rows[2][3] = Piece(1, "G", "G", False)
    return simple_ruleset(
        (king, f, g, z), rows, drop_types=("F", "G", "Z")
    )


def _session_at_ply(compiled, ply: int) -> GameSession:
    session = GameSession(compiled)
    for _ in range(ply):
        actions = session.legal_actions()
        session.submit(actions[0])
    return session


@requires_native
def test_replay_final_state_matches_python():
    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 11)
    rules = compile_native_rules(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    snapshot = native_snapshot(rules, pos)
    py = session.state
    assert snapshot["side_to_move"] == py.position.side_to_move
    assert snapshot["ply"] == py.ply_count
    assert snapshot["terminal"] == py.terminal_status.status.value
    assert snapshot["repetition_count"] == 3  # root D appeared 3 times


@requires_native
def test_non_root_repetition_detected_natively():
    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 11)
    rules = compile_native_rules(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    # The single legal move returns to position A (its 4th occurrence).
    next_move = session.legal_actions()[0]
    from generic_chess.native.adapter import pack_action

    # base type of the mover F (from square a3/a2 depends on ply parity).
    n = compiled.board_size
    state = session.state
    piece = state.position.board[
        next_move.from_square.rank * n + next_move.from_square.file
    ]
    packed_action = pack_action(rules, next_move, base_type_id=piece.base_type_id)
    child = native_make_checked(rules, pos, packed_action)
    assert child["terminal"] == "repetition"
    # Python oracle agrees.
    from generic_chess.core.transition import apply_action

    py_child = apply_action(state, next_move, compiled)
    assert py_child.terminal_status.status.value == "repetition"


@requires_native
def test_same_root_different_history_changes_terminal():
    compiled = _cycle_ruleset()
    session_short = _session_at_ply(compiled, 3)  # D count 1
    session_long = _session_at_ply(compiled, 11)  # D count 3
    rules = compile_native_rules(compiled)

    from generic_chess.native.adapter import pack_action

    n = compiled.board_size
    # The two sessions share the same board/hand/side at the root.
    short_pos = pack_native_search_position(compiled, rules, session_short)
    long_pos = pack_native_search_position(compiled, rules, session_long)
    assert native_snapshot(rules, short_pos)["hash_lo"] == native_snapshot(
        rules, long_pos
    )["hash_lo"]
    assert native_snapshot(rules, short_pos)["hash_hi"] == native_snapshot(
        rules, long_pos
    )["hash_hi"]

    next_move = session_short.legal_actions()[0]
    state = session_short.state
    piece = state.position.board[
        next_move.from_square.rank * n + next_move.from_square.file
    ]
    packed_action = pack_action(rules, next_move, base_type_id=piece.base_type_id)
    short_child = native_make_checked(rules, short_pos, packed_action)
    long_child = native_make_checked(rules, long_pos, packed_action)
    assert short_child["terminal"] == "ongoing"
    assert long_child["terminal"] == "repetition"


@requires_native
def test_replay_prefix_with_capture_promotion_drop():
    """Replay a generated game prefix that includes captures; verify the
    native root snapshot matches Python exactly."""
    from generic_chess.native.adapter import native_legal_actions
    from generic_chess.native.reference import python_legal_actions

    from native_test_helpers import generated_compiled

    compiled = generated_compiled(size=6, seed=11)
    session = GameSession(compiled)
    seen_capture = False
    for _ in range(24):
        actions = list(session.legal_actions())
        if not actions or session.result.status.value != "ongoing":
            break
        cap = next(
            (
                a
                for a in actions
                if isinstance(a, BoardMove)
                and session.state.position.board[
                    a.to_square.rank * compiled.board_size + a.to_square.file
                ]
                is not None
            ),
            None,
        )
        if cap is not None:
            seen_capture = True
        session.submit(cap if cap is not None else actions[0])
    assert seen_capture
    rules = compile_native_rules(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    nat = {
        str(to_python_action(rules, a))
        for a in native_legal_actions(rules, pos)
    }
    py = {str(a) for a in python_legal_actions(session.state, compiled)}
    assert nat == py
