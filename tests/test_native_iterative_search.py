"""Phase 2C-2: iterative deepening semantics (equivalence, publishing,
fallback, PV)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
