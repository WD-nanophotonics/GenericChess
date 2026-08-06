"""Phase 2C-3: native atomic cancellation + Python callback bridge."""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.session.session import GameSession

from native_test_helpers import generated_compiled, requires_native


def test_cancellation_callback_semantics():
    token = CancellationToken()
    calls = []
    unregister = token.register_callback(lambda: calls.append("a"))
    token.cancel()
    token.cancel()  # idempotent
    assert calls == ["a"]
    # Already-cancelled registration fires immediately.
    token.register_callback(lambda: calls.append("b"))
    assert calls == ["a", "b"]
    unregister()
    unregister()  # idempotent
    # A raising callback must not block others.
    token2 = CancellationToken()
    calls2 = []

    def boom():
        raise RuntimeError("boom")

    token2.register_callback(boom)
    token2.register_callback(lambda: calls2.append("ok"))
    token2.cancel()
    assert calls2 == ["ok"]


def test_multiple_callbacks_and_immediate_invoke():
    token = CancellationToken()
    seen = []
    token.register_callback(lambda: seen.append(1))
    token.register_callback(lambda: seen.append(2))
    token.cancel()
    assert sorted(seen) == [1, 2]


@requires_native
def test_pre_cancelled_search_returns_immediately():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules

    compiled = generated_compiled(size=6)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 8)
    session = GameSession(compiled)
    token = CancellationToken()
    token.cancel()
    result = engine.search(
        session,
        SearchLimits(max_depth=8, quiescence_max_depth=0),
        cancel_token=token,
    )
    assert result.termination_reason == "cancelled"
    assert result.completed_depth == 0
    assert result.used_fallback is True


@requires_native
def test_mid_search_cancellation_unwinds_and_restores_root():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.native.adapter import native_snapshot, pack_native_search_position
    from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules

    # TT-off 16x16 search runs for many seconds, giving cancellation a large
    # deterministic window (see the phase2c benchmark for timings).
    compiled = generated_compiled(size=16, seed=5)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 0)
    session = GameSession(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    before = native_snapshot(rules, pos)

    token = CancellationToken()
    outcome = {}

    def worker():
        outcome["result"] = engine.search(
            session,
            SearchLimits(max_depth=7, quiescence_max_depth=0),
            cancel_token=token,
        )

    thread = threading.Thread(target=worker)
    thread.start()
    time.sleep(0.02)
    token.cancel()
    thread.join(timeout=20)
    assert not thread.is_alive(), "search thread did not finish"
    result = outcome["result"]
    assert result.termination_reason == "cancelled"
    assert result.completed_depth >= 1  # some complete iteration published
    assert result.used_fallback is False
    after = native_snapshot(rules, pos)
    assert after == before
