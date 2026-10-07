"""Phase 2A: move generation must never silently truncate (>4096 actions)."""

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.native.adapter import (
    native_legal_actions,
    pack_native_position,
    to_python_action,
)
from generic_chess.native.compiler import compile_native_rules
from generic_chess.native.reference import canonical_action_set, python_legal_actions
from generic_chess.session.session import GameSession

from native_test_helpers import make_state, requires_native, simple_ruleset


def _drop_heavy_ruleset():
    """16x16 ruleset whose hand makes the legal action count exceed 4096."""
    n = 16
    king = PieceType("K", "K", (LeapAtom((1, 0)),), is_anchor=True)
    drop_types = tuple(
        PieceType(f"T{i}", f"T{i}", (LeapAtom((0, 1)),))
        for i in range(17)
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    return simple_ruleset(
        (king,) + drop_types,
        rows,
        drop_types=tuple(f"T{i}" for i in range(17)),
        drop_mask_all=True,
        board_size=n,
    )


@requires_native
def test_legal_actions_exceed_4096_and_match_python():
    compiled = _drop_heavy_ruleset()
    n = compiled.board_size
    board = [None] * (n * n)
    board[0] = Piece(0, "K", "K", False)
    board[n * n - 1] = Piece(1, "K", "K", False)
    hand = Hands(tuple((f"T{i}", 250) for i in range(17)))
    position = Position(
        tuple(board),
        (hand, Hands.empty()),
        0,
        compiled.ruleset_fingerprint,
    )
    state = make_state(compiled, position)
    py_actions = python_legal_actions(state, compiled)
    assert len(py_actions) > 4096, len(py_actions)

    rules = compile_native_rules(compiled)
    pos = pack_native_position(compiled, rules, state)
    native_actions = [to_python_action(rules, a) for a in native_legal_actions(rules, pos)]
    assert len(native_actions) == len(py_actions)
    assert set(canonical_action_set(native_actions)) == set(
        canonical_action_set(py_actions)
    )


@requires_native
def test_python_session_still_works_after_large_generation():
    """Sanity: a GameSession over the same ruleset is unaffected."""
    compiled = _drop_heavy_ruleset()
    session = GameSession(compiled)
    assert session.legal_actions()
