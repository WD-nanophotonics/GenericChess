"""Phase 2A hardening: hash identity, capacity, immutability, long roundtrip."""

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.native import _module, native_version
from generic_chess.native.adapter import (
    native_long_make_unmake_roundtrip,
    native_snapshot,
    pack_native_position,
)
from generic_chess.native.compiler import (
    GC_MAX_PLY,
    NativeUnsupportedRuleError,
    compile_native_rules,
)
from generic_chess.session.session import GameSession

from native_test_helpers import (
    generated_compiled,
    make_state,
    requires_native,
    simple_ruleset,
)


@requires_native
def test_native_version_is_050():
    assert native_version() == "0.5.0"
    caps = _module().native_capabilities()
    assert caps["native_schema"] == "native-0.5.0"
    assert caps["hash_includes_base_type"] is True
    assert caps["repetition_context_hash"] is True
    assert caps["transposition_table"] is True
    assert caps["iterative_deepening"] is True
    assert caps["node_budget"] is True
    assert caps["monotonic_time_budget"] is True
    assert caps["native_cancellation"] is True
    assert caps["native_qsearch"] is False


def _promoted_identity_ruleset():
    n = 4
    king = PieceType(
        "K", "K", (), is_anchor=True
    )
    a = PieceType(
        "A", "A", (LeapAtom((0, 1)),),
        is_promotable=True, promotion_target_ids=("X",),
    )
    b = PieceType(
        "B", "B", (LeapAtom((0, 1)),),
        is_promotable=True, promotion_target_ids=("X",),
    )
    x = PieceType("X", "X", (LeapAtom((1, 0)),))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][1] = Piece(0, "A", "A", False)
    return simple_ruleset(
        (king, a, b, x),
        rows,
        drop_types=("A", "B", "X"),
        promotion_allowed={"A": ((), ()), "B": ((), ())},
        promotion_forced={"A": ((), ()), "B": ((), ())},
    )


@requires_native
def test_hash_distinguishes_base_type_with_same_current():
    compiled = _promoted_identity_ruleset()
    rules = compile_native_rules(compiled)
    n = 4

    def build(base: str):
        board = [None] * (n * n)
        board[0] = Piece(0, "K", "K", False)
        board[n * n - 1] = Piece(1, "K", "K", False)
        board[1 * n + 1] = Piece(0, base, "X", True)
        return Position(
            tuple(board),
            (Hands.empty(), Hands.empty()),
            0,
            compiled.ruleset_fingerprint,
        )

    state_a = make_state(compiled, build("A"))
    state_b = make_state(compiled, build("B"))
    snap_a = native_snapshot(rules, pack_native_position(compiled, rules, state_a))
    snap_b = native_snapshot(rules, pack_native_position(compiled, rules, state_b))
    assert (snap_a["hash_lo"], snap_a["hash_hi"]) != (
        snap_b["hash_lo"],
        snap_b["hash_hi"],
    )
    assert position_key(state_a.position, compiled) != position_key(
        state_b.position, compiled
    )


@requires_native
def test_long_replay_make_unmake_restores_initial():
    compiled = generated_compiled(size=6, seed=42)
    session = GameSession(compiled)
    for _ in range(40):
        actions = session.legal_actions()
        if not actions or session.result.status.value != "ongoing":
            break
        actions_list = list(actions)
        session.submit(actions_list[len(session.history) % len(actions_list)])
    assert len(session.history) >= 30
    rules = compile_native_rules(compiled)
    result = native_long_make_unmake_roundtrip(compiled, rules, session)
    assert result["steps"] == len(session.history)
    assert result["hash_verified"] == 1
    assert result["state_restored"] == 1
    assert result["ok"] == 1


@requires_native
def test_hand_count_never_clamped():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    n = 4
    board = [None] * (n * n)
    board[0] = Piece(0, "K", "K", False)
    board[n * n - 1] = Piece(1, "K", "K", False)
    # Find a non-anchor type to stuff into the hand.
    non_anchor = next(
        pt.type_id for pt in compiled.piece_types if not pt.is_anchor
    )
    hand = Hands(((non_anchor, 70),))
    position = Position(
        tuple(board),
        (hand, Hands.empty()),
        0,
        compiled.ruleset_fingerprint,
    )
    state = make_state(compiled, position)
    # 70 is below GC_MAX_HAND (256): pack must succeed and drops must exist.
    pos = pack_native_position(compiled, rules, state)
    snapshot = native_snapshot(rules, pos)
    assert snapshot["hands"][0][
        rules.type_map[non_anchor]
    ] == 70


@requires_native
def test_type_map_and_ids_are_immutable():
    compiled = generated_compiled()
    rules = compile_native_rules(compiled)
    with pytest.raises(TypeError):
        rules.type_map["NOPE"] = 99
    with pytest.raises(AttributeError):
        rules.type_ids.append("NOPE")
    from types import MappingProxyType

    assert isinstance(rules.type_map, MappingProxyType)
    assert isinstance(rules.type_ids, tuple)


def test_max_ply_capacity_validated():
    n = 4
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "P", "P", False)
    compiled = simple_ruleset(
        (
            PieceType("K", "K", (), is_anchor=True),
            PieceType("P", "P", (LeapAtom((0, 1)),)),
        ),
        rows,
        drop_types=("P",),
        max_ply=GC_MAX_PLY + 10,
    )
    with pytest.raises(NativeUnsupportedRuleError) as exc:
        compile_native_rules(compiled)
    assert str(GC_MAX_PLY) in str(exc.value)
    assert compiled.ruleset_fingerprint in str(exc.value)
