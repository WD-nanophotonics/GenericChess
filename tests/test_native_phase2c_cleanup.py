"""Phase 2C-0: boundary cleanup tests (hand=256, trusted-make propagation,
depth limits, terminal root nodes, canonical tie-break)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.native.adapter import (
    native_legal_actions,
    native_make_checked,
    native_make_unmake_roundtrip,
    pack_native_position,
    to_python_action,
)
from generic_chess.native.compiler import GC_MAX_PLY, compile_native_rules
from generic_chess.native.search import native_fixed_depth_search

from native_test_helpers import make_state, requires_native, simple_ruleset


def _hand256_ruleset():
    n = 4
    king = PieceType("K", "K", (), is_anchor=True)
    t = PieceType("T", "T", (LeapAtom((1, 0)),))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "T", "T", False)  # initial legal move for validation
    return simple_ruleset(
        (king, t), rows, drop_types=("T",), drop_mask_all=True
    )


def _position_with_hand(compiled, hand_count, extra_pieces=()):
    n = compiled.board_size
    board = [None] * (n * n)
    for base, owner, f, r in (
        ("K", 0, 0, 0),
        ("K", 1, n - 1, n - 1),
        *extra_pieces,
    ):
        board[r * n + f] = Piece(owner, base, base, False)
    hand = Hands((("T", hand_count),))
    return Position(
        tuple(board),
        (hand, Hands.empty()),
        0,
        compiled.ruleset_fingerprint,
    )


@requires_native
def test_drop_at_max_hand_works_and_roundtrips():
    compiled = _hand256_ruleset()
    rules = compile_native_rules(compiled)
    state = make_state(compiled, _position_with_hand(compiled, 256))
    pos = pack_native_position(compiled, rules, state)
    drops = [
        a for a in native_legal_actions(rules, pos)
        if to_python_action(rules, a).__class__.__name__ == "DropMove"
    ]
    assert drops
    child = native_make_checked(rules, pos, drops[0])
    n = compiled.board_size
    assert child["hands"][0][rules.type_map["T"]] == 255
    check = native_make_unmake_roundtrip(rules, pos, drops[0])
    assert check["make_ok"] == 1
    assert check["hash_after_make_ok"] == 1
    assert check["hash_restored_ok"] == 1
    assert check["state_restored"] == 1


@requires_native
def test_capture_overflow_at_max_hand_reports_error():
    compiled = _hand256_ruleset()
    rules = compile_native_rules(compiled)
    # White piece at a2 can capture the black T at b2; white hand T=256 makes
    # that capture overflow (256 -> 257), which must be an explicit error.
    state = make_state(
        compiled,
        _position_with_hand(
            compiled, 256, extra_pieces=(("T", 1, 1, 1), ("T", 0, 0, 1))
        ),
    )
    pos = pack_native_position(compiled, rules, state)
    with pytest.raises(RuntimeError) as exc:
        native_legal_actions(rules, pos)
    fields = exc.value.args[0] if exc.value.args else {}
    assert fields.get("reason") == "hand_overflow"
    assert "fingerprint" in fields


@requires_native
def test_fixed_depth_rejects_out_of_range_depths():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.native.compiler import compile_native_evaluation
    from generic_chess.session.session import GameSession

    from native_test_helpers import generated_compiled

    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    for bad in (-1, GC_MAX_PLY + 1, 2**31 - 1):
        with pytest.raises(ValueError):
            native_fixed_depth_search(compiled, rules, eval_tables, session, bad)


@requires_native
def test_terminal_root_counts_one_node():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    from generic_chess.native.compiler import compile_native_evaluation
    from generic_chess.session.session import GameSession

    from test_ai_match import _mate_ruleset
    from generic_chess.rules.compiler import compile_ruleset

    compiled = compile_ruleset(_mate_ruleset())
    rules = compile_native_rules(compiled)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    session.submit(BoardMove(Square(1, 4), Square(0, 4)))
    result = native_fixed_depth_search(compiled, rules, eval_tables, session, 3)
    assert result.nodes == 1
    assert result.action is None
    assert result.completed_depth == 0
    assert result.termination_reason == "terminal"


@requires_native
def test_canonical_tie_break_matches_min_packed():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.native.compiler import compile_native_evaluation
    from generic_chess.native.reference import (
        canonical_pack,
        reference_fixed_depth_minimax,
    )
    from generic_chess.session.session import GameSession

    from native_test_helpers import generated_compiled

    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    eval_tables = compile_native_evaluation(rules, profile, config)
    session = GameSession(compiled)
    for depth in (1, 2, 3):
        _score, actions, canonical, _pv, _ = reference_fixed_depth_minimax(
            session.state, compiled, evaluator, depth
        )
        result = native_fixed_depth_search(
            compiled, rules, eval_tables, session, depth
        )
        if actions:
            packed = canonical_pack(compiled, session.state, result.action)
            assert packed == min(
                canonical_pack(compiled, session.state, a) for a in actions
            )
            assert result.action == canonical
