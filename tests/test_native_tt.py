"""Phase 2C-1: repetition-safe native transposition table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native import _module
from generic_chess.native.adapter import pack_native_search_position
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.reference import reference_fixed_depth_minimax
from generic_chess.native.search import native_fixed_depth_search

from native_test_helpers import generated_compiled, requires_native


def _setup(compiled):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = _module().create_search_engine(rules.capsule, eval_tables.capsule, 4)
    return evaluator, rules, eval_tables, engine


@requires_native
def test_tt_info_memory_bounds():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = _module().create_search_engine(rules.capsule, eval_tables.capsule, 4)
    info = _module().search_engine_tt_info(engine)
    assert info["requested_bytes"] == 4 * 1024 * 1024
    assert info["allocated_bytes"] <= info["requested_bytes"]
    assert info["bucket_count"] >= 1
    assert info["entry_size"] == 64
    assert info["entry_capacity"] == info["bucket_count"] * 4
    # Invalid sizes rejected.
    import pytest

    for bad in (-1, 1025):
        with pytest.raises(ValueError):
            _module().create_search_engine(rules.capsule, eval_tables.capsule, bad)


@requires_native
def test_tt_off_vs_on_fixed_depth_equal():
    compiled = generated_compiled(size=4)
    _evaluator, rules, eval_tables, engine = _setup(compiled)
    from generic_chess.session.session import GameSession
    from generic_chess.native.adapter import to_python_action

    session = GameSession(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    for depth in (1, 2, 3):
        cold = native_fixed_depth_search(compiled, rules, eval_tables, session, depth)
        hot = _module().engine_fixed_depth_search(engine, pos, depth)
        assert hot["score"] == cold.score
        hot_action = (
            to_python_action(rules, hot["best_action"])
            if hot["best_action"] is not None
            else None
        )
        assert hot_action == cold.action


@requires_native
def test_warm_search_reuses_tt():
    compiled = generated_compiled(size=4)
    _evaluator, rules, _eval_tables, engine = _setup(compiled)
    from generic_chess.session.session import GameSession

    session = GameSession(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    for depth in (2, 3):
        cold = _module().engine_fixed_depth_search(engine, pos, depth)
        _module().search_engine_clear_tt(engine)
        _module().engine_fixed_depth_search(engine, pos, depth)  # warm-up
        warm = _module().engine_fixed_depth_search(engine, pos, depth)
        assert warm["score"] == cold["score"]
        assert warm["best_action"] == cold["best_action"]
        assert warm["tt_hits"] > 0
        assert warm["nodes"] <= cold["nodes"]


@requires_native
def test_mate_normalization_across_plies():
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.session.session import GameSession

    from test_ai_match import _mate_ruleset

    compiled = compile_ruleset(_mate_ruleset())
    _evaluator, rules, _eval_tables, engine = _setup(compiled)
    session = GameSession(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    # Depth 2 cold vs depth 3 warm must both report the mate-in-1 score.
    d2 = _module().engine_fixed_depth_search(engine, pos, 2)
    d3 = _module().engine_fixed_depth_search(engine, pos, 3)
    assert d2["score"] == MATE_SCORE - 1
    assert d3["score"] == MATE_SCORE - 1
    assert d2["best_action"] == d3["best_action"]


@requires_native
def test_history_isolation_prevents_tt_pollution():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    evaluator, rules, _eval_tables, engine = _setup(compiled)
    sessions = {ply: _session_at_ply(compiled, ply) for ply in (3, 11)}
    pos3 = pack_native_search_position(compiled, rules, sessions[3])
    pos11 = pack_native_search_position(compiled, rules, sessions[11])
    # Same board, different history: TT keys must isolate.
    for ply, pos, session in ((3, pos3, sessions[3]), (11, pos11, sessions[11])):
        _module().search_engine_clear_tt(engine)
        cold = _module().engine_fixed_depth_search(engine, pos, 2)
        _module().engine_fixed_depth_search(engine, pos, 2)  # warm
        warm = _module().engine_fixed_depth_search(engine, pos, 2)
        ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, 2)
        assert cold["score"] == warm["score"] == ref[0]
        assert cold["best_action"] == warm["best_action"]
