"""Phase 2C differential gate: TT on/off fixed depth, iterative equivalence,
history isolation and fuzz."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import _module
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.native.reference import (
    canonical_pack,
    reference_fixed_depth_minimax,
)
from generic_chess.native.search import native_fixed_depth_search

from native_test_helpers import requires_native


def _compare_fixed(compiled, session, depth, engine, pos, label):
    """TT-off fixed depth vs reference vs TT-on engine."""
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, depth)
    off = native_fixed_depth_search(compiled, rules, eval_tables, session, depth)
    on = _module().engine_fixed_depth_search(engine, pos, depth)
    from generic_chess.native.adapter import to_python_action

    on_action = (
        to_python_action(rules, on["best_action"])
        if on["best_action"] is not None
        else None
    )
    assert off.score == ref[0], f"{label} d{depth} tt-off score"
    assert on["score"] == ref[0], f"{label} d{depth} tt-on score"
    assert off.action == ref[2], f"{label} d{depth} tt-off canonical"
    assert on_action == ref[2], f"{label} d{depth} tt-on canonical"
    if ref[1]:
        packed = canonical_pack(compiled, session.state, on_action)
        assert packed == min(
            canonical_pack(compiled, session.state, a) for a in ref[1]
        )


@requires_native
def test_corpus_phase2c_differential():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )
    from generic_chess.native.adapter import pack_native_search_position

    import json

    corpus = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "tests"
            / "fixtures"
            / "native_correctness_corpus_v1.json"
        ).read_text(encoding="utf-8")
    )["fixtures"]
    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    for fixture in corpus:
        compiled, session = build_session(
            specs[fixture["ruleset_fixture_id"]],
            tuple(fixture["action_prefix"]),
        )
        config = EvaluationConfig()
        profile = build_ruleset_profile(compiled, config)
        rules = compile_native_rules(compiled)
        eval_tables = compile_native_evaluation(rules, profile, config)
        engine = NativeSearchEngine(compiled, rules, eval_tables, 4)
        pos = pack_native_search_position(compiled, rules, session)
        for depth in (1, 2, 3):
            _compare_fixed(
                compiled, session, depth, engine._capsule, pos,
                fixture["fixture_id"],
            )


@requires_native
def test_history_isolation_iterative():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 4)
    for ply in (3, 11):
        session = _session_at_ply(compiled, ply)
        result = engine.search(
            session, SearchLimits(max_depth=2, quiescence_max_depth=0)
        )
        ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, 2)
        assert result.score == ref[0], f"ply {ply}"
        assert result.action == ref[2], f"ply {ply}"


@requires_native
def test_iterative_equals_fixed_after_warm():
    from generic_chess.native.adapter import pack_native_search_position

    from native_test_helpers import generated_compiled
    from generic_chess.session.session import GameSession

    compiled = generated_compiled(size=4)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 4)
    session = GameSession(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    for depth in (1, 2, 3):
        # Warm the engine TT with the fixed-depth search first.
        _module().engine_fixed_depth_search(engine._capsule, pos, depth)
        iterative = engine.search(
            session, SearchLimits(max_depth=depth, quiescence_max_depth=0)
        )
        fixed = native_fixed_depth_search(
            compiled, rules, eval_tables, session, depth
        )
        assert iterative.score == fixed.score
        assert iterative.action == fixed.action
