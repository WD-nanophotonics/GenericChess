"""Phase 2B: fixed-depth native search API semantics (depth 0, terminal,
mate distance, PV, root restore, resignation)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.keys import position_key
from generic_chess.core.terminal import _terminal_from_parts
from generic_chess.native.adapter import native_snapshot, pack_native_search_position
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.search import (
    native_fixed_depth_search,
    native_fixed_depth_search_state,
)
from generic_chess.session.session import GameSession

from native_test_helpers import (
    generated_compiled,
    make_state,
    requires_native,
    simple_ruleset,
)


def _profile(compiled):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    return profile, evaluator


def _mate_ruleset_compiled():
    from test_ai_match import _mate_ruleset
    from generic_chess.rules.compiler import compile_ruleset

    return compile_ruleset(_mate_ruleset())


def _delayed_loss_state(compiled):
    """Black to move and in check; black can delay but is mated at ply 2."""
    n = compiled.board_size
    board = [None] * (n * n)
    for base, owner, f, r in (
        ("K", 0, 2, 5),
        ("R", 0, 5, 0),
        ("R", 0, 0, 0),
        ("K", 1, 0, 7),
    ):
        board[r * n + f] = Piece(owner, base, base, False)
    pos = Position(
        tuple(board),
        (Hands.empty(), Hands.empty()),
        1,
        compiled.ruleset_fingerprint,
    )
    key = position_key(pos, compiled)
    counts = ((key, 1),)
    status = _terminal_from_parts(pos, 0, counts, compiled)
    return GameState(pos, 0, counts, status)


@requires_native
def _search(compiled, rules, eval_tables, session, depth):
    return native_fixed_depth_search(
        compiled, rules, eval_tables, session, depth
    )


@requires_native
def test_depth_zero_returns_static_eval_without_action():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    profile, evaluator = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    result = _search(compiled, rules, eval_tables, session, 0)
    assert result.action is None
    assert result.completed_depth == 0
    assert result.nodes == 1
    assert result.score == evaluator.evaluate(session.state)


@requires_native
def test_terminal_root_returns_no_action():
    compiled = _mate_ruleset_compiled()
    rules = compile_native_rules(compiled)
    profile, _ = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    # Play the known mating move -> terminal checkmate root.
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square

    session = GameSession(compiled)
    session.submit(BoardMove(Square(1, 4), Square(0, 4)))
    assert session.result.status.value == "checkmate"
    result = _search(compiled, rules, eval_tables, session, 3)
    assert result.action is None
    assert result.termination_reason == "terminal"
    assert result.completed_depth == 0


@requires_native
def test_mate_in_one_and_quicker_mate_preference():
    compiled = _mate_ruleset_compiled()
    rules = compile_native_rules(compiled)
    profile, _ = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    for depth in (1, 2):
        result = _search(compiled, rules, eval_tables, session, depth)
        assert result.score == MATE_SCORE - 1
        assert result.action is not None
        # PV starts with the best action and replays legally (enforced by the
        # wrapper), so the mate-in-1 line is preferred at depth 2 too.
        assert result.principal_variation[0] == result.action
        assert len(result.principal_variation) <= depth


@requires_native
def test_delayed_loss_scores_mate_distance():
    compiled = _mate_ruleset_compiled()
    rules = compile_native_rules(compiled)
    profile, _ = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    state = _delayed_loss_state(compiled)
    result = native_fixed_depth_search_state(
        compiled, rules, eval_tables, state, 2
    )
    assert result.score == -(MATE_SCORE - 2)
    assert result.action is not None


@requires_native
def test_search_restores_root_position():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    profile, _ = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    before = native_snapshot(rules, pos)
    _search(compiled, rules, eval_tables, session, 3)
    after = native_snapshot(rules, pos)
    assert after == before


@requires_native
def test_resignation_session_is_not_searched():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    profile, _ = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    session.resign()
    result = _search(compiled, rules, eval_tables, session, 2)
    assert result.action is None
    assert result.termination_reason == "terminal"
    assert result.nodes == 0


@requires_native
def test_pv_length_bounded_and_starts_with_best():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    profile, _ = _profile(compiled)
    eval_tables = compile_native_evaluation(rules, profile, EvaluationConfig())
    session = GameSession(compiled)
    for depth in (1, 2, 3):
        result = _search(compiled, rules, eval_tables, session, depth)
        if result.action is not None:
            assert result.principal_variation
            assert result.principal_variation[0] == result.action
        assert len(result.principal_variation) <= depth
