"""Phase 2C-2: iterative deepening semantics (equivalence, publishing,
fallback, PV)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.search import native_fixed_depth_search
from generic_chess.session.session import GameSession

from generic_chess.ai.limits import SearchLimits
from native_test_helpers import generated_compiled, requires_native


def _engine(compiled, tt_mb=8):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, tt_mb)
    return engine


@requires_native
def test_iterative_equals_fixed_depth_without_budget():
    compiled = generated_compiled(size=4)
    engine = _engine(compiled)
    session = GameSession(compiled)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    for depth in (1, 2, 3):
        iterative = engine.search(
            session, SearchLimits(max_depth=depth, quiescence_max_depth=0)
        )
        fixed = native_fixed_depth_search(
            compiled, rules, eval_tables, session, depth
        )
        assert iterative.score == fixed.score
        assert iterative.action == fixed.action
        assert iterative.termination_reason == "completed_depth"
        assert iterative.completed_depth == depth
        if iterative.action is not None:
            assert iterative.principal_variation
            assert iterative.principal_variation[0] == iterative.action
            assert len(iterative.principal_variation) <= depth


@requires_native
def test_iterative_depth_zero_is_score_only_not_move_selection():
    from generic_chess.native.search import native_fixed_depth_search

    compiled = generated_compiled(size=4)
    engine = _engine(compiled, tt_mb=0)
    session = GameSession(compiled)
    before = session.to_record()
    static = native_fixed_depth_search(
        compiled, engine._native_rules, engine._evaluation, session, depth=0
    )

    result = engine.search(
        session, SearchLimits(max_depth=0, quiescence_max_depth=0)
    )

    assert result.action is None
    assert result.score == static.score
    assert result.principal_variation == ()
    assert result.completed_depth == 0
    assert result.termination_reason == "completed_depth"
    assert result.used_fallback is False
    assert result.nodes == 1
    assert result.qnodes == 0
    assert session.to_record() == before


@requires_native
@pytest.mark.parametrize(
    "control, expected_reason",
    [("nodes", "node_limit"), ("time", "time_limit"), ("cancel", "cancelled")],
)
def test_iterative_depth_zero_honors_abort_controls(control, expected_reason):
    from generic_chess.ai.cancellation import CancellationToken

    compiled = generated_compiled(size=4)
    engine = _engine(compiled, tt_mb=0)
    session = GameSession(compiled)
    token = None
    if control == "nodes":
        limits = SearchLimits(
            max_depth=0, max_nodes=0, quiescence_max_depth=0
        )
    elif control == "time":
        limits = SearchLimits(
            max_depth=0, max_time_seconds=0.0, quiescence_max_depth=0
        )
    else:
        limits = SearchLimits(max_depth=0, quiescence_max_depth=0)
        token = CancellationToken()
        token.cancel()

    result = engine.search(session, limits, cancel_token=token)

    assert result.action is None
    assert result.principal_variation == ()
    assert result.completed_depth == 0
    assert result.termination_reason == expected_reason
    assert result.used_fallback is False
    assert result.nodes == 1  # mandatory root visit precedes abort polling


@requires_native
def test_iterative_terminal_root():
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    from generic_chess.rules.compiler import compile_ruleset

    from test_ai_match import _mate_ruleset

    compiled = compile_ruleset(_mate_ruleset())
    engine = _engine(compiled)
    session = GameSession(compiled)
    session.submit(BoardMove(Square(1, 4), Square(0, 4)))
    result = engine.search(
        session, SearchLimits(max_depth=3, quiescence_max_depth=0)
    )
    assert result.action is None
    assert result.completed_depth == 0
    assert result.termination_reason == "terminal_position"
    assert result.nodes == 1

    zero_depth = engine.search(
        session,
        SearchLimits(
            max_depth=0,
            max_nodes=0,
            max_time_seconds=0.0,
            quiescence_max_depth=0,
        ),
    )
    assert zero_depth.action is None
    assert zero_depth.principal_variation == ()
    assert zero_depth.score == result.score
    assert zero_depth.completed_depth == 0
    assert zero_depth.termination_reason == "terminal_position"
    assert zero_depth.used_fallback is False
    assert zero_depth.nodes == 1


@requires_native
@pytest.mark.parametrize("kind", ["RESIGNATION", "WIN", "LOSS", "RESTART", "NO_CONTEST"])
@pytest.mark.parametrize("owner", [0, 1])
def test_iterative_session_level_terminal_matches_core(kind, owner):
    from test_finished_session_search import finish, rules
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.evaluation.config import MATE_SCORE
    from generic_chess.rules.compiler import compile_ruleset

    compiled = compile_ruleset(rules(kind, owner))
    session = GameSession(compiled)
    finish(session, kind, owner)
    engine = _engine(compiled, tt_mb=0)

    for current in (session, GameSession.replay(compiled, session.to_record())):
        native = engine.search(
            current, SearchLimits(max_depth=2, quiescence_max_depth=0)
        )
        core = AlphaBetaPlayer(compiled).choose_action(
            current, SearchLimits(max_depth=2, quiescence_max_depth=0)
        )
        result = current.result
        side_to_move = current.state.position.side_to_move
        expected = (0 if result.winner is None else
                    MATE_SCORE if result.winner == side_to_move else -MATE_SCORE)

        assert native.action is None
        assert native.principal_variation == ()
        assert native.score == core.score == expected
        assert native.completed_depth == native.nodes == native.qnodes == 0
        assert native.termination_reason == "terminal_position"


@requires_native
def test_iterative_fallback_when_depth_one_incomplete():
    compiled = generated_compiled(size=4)
    engine = _engine(compiled)
    session = GameSession(compiled)
    result = engine.search(
        session,
        SearchLimits(max_depth=3, max_nodes=1, quiescence_max_depth=0),
    )
    assert result.completed_depth == 0
    assert result.used_fallback is True
    assert result.score == 0
    assert result.principal_variation == ()
    assert result.termination_reason == "node_limit"
    assert result.action in session.legal_actions()


@requires_native
def test_iterative_rejects_unsupported_qsearch_limits():
    compiled = generated_compiled(size=4)
    engine = _engine(compiled)
    session = GameSession(compiled)
    import pytest

    with pytest.raises(ValueError):
        engine.search(
            session,
            SearchLimits(max_depth=2, quiescence_max_depth=1),
        )
