"""Static analysis, values, mobility curves, symmetry, base/current semantics."""

import pytest

from generic_chess.ai.evaluation.analyzer import movement_signature
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE, MATE_THRESHOLD
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.mobility import mobility_density_curve
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.terminal import TerminalResult, TerminalStatus

from ai_fixtures import build_4x4_rooks, build_promotion, king, rook
from conftest import make_position, make_state


def _config():
    return EvaluationConfig()


def test_anchor_not_in_material():
    compiled = build_4x4_rooks()
    profile = build_ruleset_profile(compiled, _config())
    assert profile.board_value_by_type["K"] == 0
    assert profile.piece_profiles["K"].is_anchor
    assert profile.piece_profiles["K"].normalized_hand_value == 0


def test_type_name_invariance():
    config = _config()
    a = build_ruleset_profile(build_4x4_rooks(), config)
    compiled_b = None
    from generic_chess.core.pieces import PieceType, Piece
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.rules.schema import RuleSet

    n = 4
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][2] = Piece(0, "Z1", "Z1", False)
    rows[2][1] = Piece(1, "Z2", "Z2", False)
    z1 = PieceType("Z1", "Z1", (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))))
    z2 = PieceType("Z2", "Z2", (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))))
    mask = (True,) * 16
    ruleset = RuleSet(
        board_size=n,
        piece_types=(king(), z1, z2),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={"Z1": (mask, mask), "Z2": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
    )
    compiled_b = compile_ruleset(ruleset)
    b = build_ruleset_profile(compiled_b, config)
    assert b.piece_profiles["Z1"].raw_capability_score == b.piece_profiles["Z2"].raw_capability_score
    assert b.piece_profiles["Z1"].normalized_board_value == b.piece_profiles["Z2"].normalized_board_value
    assert movement_signature(z1.movement_atoms) == movement_signature(z2.movement_atoms)


def test_ray_leap_dominance():
    n = 8
    # Same empty-board target set along one file: ray vs a leap at every step.
    ray_atoms = (RayAtom((0, 1)),)
    leap_atoms = tuple(LeapAtom((0, j)) for j in range(1, 8))
    config = _config()
    ray_curve = mobility_density_curve(
        n, ray_atoms, (0.0, 0.5),
        fingerprint="fp", signature="s", version=config.evaluator_version, mc_samples=config.mc_samples,
    )
    leap_curve = mobility_density_curve(
        n, leap_atoms, (0.0, 0.5),
        fingerprint="fp", signature="s", version=config.evaluator_version, mc_samples=config.mc_samples,
    )
    assert ray_curve[0] == pytest.approx(leap_curve[0], abs=1e-3)  # empty board equal
    assert leap_curve[1] >= ray_curve[1]
    assert leap_curve[1] > ray_curve[1]  # strictly better under occupancy


def test_mirrored_position_evaluation_negates():
    compiled = build_4x4_rooks()
    profile = build_ruleset_profile(compiled, _config())
    evaluator = Evaluator(compiled, profile, _config())
    state_a = make_state(compiled, [
        "....",
        "....",
        "....",
        "K..R",
    ])
    # Rotate 180 + swap colors.
    def rotate_swap(pos, n):
        from generic_chess.core.coordinates import Square
        from generic_chess.core.pieces import Piece
        board = [None] * (n * n)
        for idx, piece in enumerate(pos.board):
            if piece is None:
                continue
            sq = Square(idx % n, idx // n)
            r = Square(n - 1 - sq.file, n - 1 - sq.rank)
            board[r.rank * n + r.file] = Piece(1 - piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted)
        return tuple(board)

    n = compiled.board_size
    board_b = rotate_swap(state_a.position, n)
    from generic_chess.core.position import Position, Hands

    pos_b = Position(board=board_b, hands=(Hands.empty(), Hands.empty()), side_to_move=0, ruleset_fingerprint=compiled.ruleset_fingerprint)
    from generic_chess.core.position import GameState
    from generic_chess.core.terminal import TerminalResult, TerminalStatus

    state_b = GameState(pos_b, 0, (("k", 1),), TerminalResult(TerminalStatus.ONGOING))
    assert evaluator.evaluate(state_a) == -evaluator.evaluate(state_b)


def test_promoted_uses_current_type_and_hand_uses_base():
    compiled = build_promotion()
    config = _config()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    assert profile.board_value_by_type["G"] > profile.board_value_by_type["P"]

    lines = [
        ".......k",
        "....P...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    base_state = make_state(compiled, lines)  # native P on the board
    promo_lines = [
        ".......k",
        "....G...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    promo_state = make_state(compiled, promo_lines, promoted={(4, 6): "P"})  # promoted: base P, current G
    assert evaluator.evaluate(promo_state) > evaluator.evaluate(base_state)

    # Hand material uses base type value.
    plain = [
        ".......k",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    no_hand = make_state(compiled, plain)
    with_hand = make_state(compiled, plain, hands=([("P", 1)], []))
    delta = evaluator.evaluate(with_hand) - evaluator.evaluate(no_hand)
    assert delta == profile.hand_value_by_base_type["P"]


def test_mate_score_beats_static():
    compiled = build_4x4_rooks()
    profile = build_ruleset_profile(compiled, _config())
    evaluator = Evaluator(compiled, profile, _config())
    state = make_state(compiled, [
        "....",
        "....",
        "....",
        "K..R",
    ])
    static = evaluator.evaluate(state)
    assert abs(static) < MATE_THRESHOLD
    mate = terminal_score(TerminalResult(TerminalStatus.CHECKMATE, 0), 0, 0)
    assert mate > static
    assert mate == MATE_SCORE
    later = terminal_score(TerminalResult(TerminalStatus.CHECKMATE, 0), 0, 3)
    assert later == MATE_SCORE - 3  # faster win scores higher
