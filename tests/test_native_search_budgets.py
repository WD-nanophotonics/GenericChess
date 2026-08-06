"""Phase 2C-3: node and time budget semantics."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.session.session import GameSession

from native_test_helpers import generated_compiled, requires_native


def _engine_and_session(size=6, seed=11):
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules

    compiled = generated_compiled(size=size, seed=seed)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 8)
    return compiled, engine, GameSession(compiled)


@requires_native
def test_max_nodes_zero_is_fallback():
    _compiled, engine, session = _engine_and_session(size=4)
    result = engine.search(
        session, SearchLimits(max_depth=3, max_nodes=0, quiescence_max_depth=0)
    )
    assert result.termination_reason == "node_limit"
    assert result.completed_depth == 0
    assert result.used_fallback is True
    assert result.nodes <= 1


@requires_native
def test_max_nodes_one_is_deterministic():
    _compiled, engine, session = _engine_and_session(size=4)
    results = []
    for _ in range(2):
        results.append(
            engine.search(
                session,
                SearchLimits(max_depth=3, max_nodes=1, quiescence_max_depth=0),
            )
        )
    assert results[0].nodes == results[1].nodes == 1
    assert results[0].used_fallback is True
    assert results[0].action == results[1].action


@requires_native
def test_node_budget_never_exceeded():
    _compiled, engine, session = _engine_and_session(size=6)
    for budget in (10, 50, 200):
        result = engine.search(
            session,
            SearchLimits(max_depth=8, max_nodes=budget, quiescence_max_depth=0),
        )
        assert result.nodes <= budget
        if result.completed_depth > 0:
            assert result.used_fallback is False
        else:
            assert result.used_fallback is True


@requires_native
def test_negative_node_budget_rejected():
    _compiled, engine, session = _engine_and_session(size=4)
    with pytest.raises(ValueError):
        engine.search(
            session,
            SearchLimits(max_depth=3, max_nodes=-1, quiescence_max_depth=0),
        )


@requires_native
def test_time_zero_is_immediate_fallback():
    _compiled, engine, session = _engine_and_session(size=6)
    result = engine.search(
        session,
        SearchLimits(
            max_depth=8, max_time_seconds=0.0, quiescence_max_depth=0
        ),
    )
    assert result.termination_reason == "time_limit"
    assert result.used_fallback is True
    assert result.completed_depth == 0


@requires_native
def test_finite_time_budget_eventually_aborts():
    _compiled, engine, session = _engine_and_session(size=8, seed=3)
    result = engine.search(
        session,
        SearchLimits(
            max_depth=16, max_time_seconds=0.02, quiescence_max_depth=0
        ),
    )
    # The search must not run away; abort with the real budget reason.
    assert result.termination_reason in ("time_limit", "completed_depth")
    assert result.elapsed_seconds < 5.0


@requires_native
def test_invalid_time_values_rejected():
    _compiled, engine, session = _engine_and_session(size=4)
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            engine.search(
                session,
                SearchLimits(
                    max_depth=2, max_time_seconds=bad, quiescence_max_depth=0
                ),
            )
