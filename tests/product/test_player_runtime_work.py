"""Expose successful runtime work that q classification spends beyond searched nodes."""
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts import full_q_refresh_comparison as probe
import random


def prepared():
    generated = probe.generate_game(probe.GeneratorConfig(
        seed=2026102016, board_size=12, setup_preset='bilateral_random',
        allow_hybrid=True))
    base = probe.compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
    compiled = probe.SearchMetadataAdapter(ir=base.ir,
        _legacy_compiled=base._legacy_compiled, support=base.support)
    session = probe.GameSession(compiled)
    rng = random.Random(2026102016 + 31000)
    for _ in range(8):
        session.submit(rng.choice(sorted(session.legal_actions(), key=repr)))
    config = probe.EvaluationConfig()
    evaluator = probe.Evaluator(compiled,
        probe.build_ruleset_profile(compiled, config), config)
    return session, AlphaBetaPlayer(compiled, use_disk_cache=False,
        use_native_semantic_legality=False, evaluator_override=evaluator)


def observe(monkeypatch, token=None):
    counts = {'push': 0, 'pop': 0}
    old_push, old_pop = SearchPathRuntime.push, SearchPathRuntime.pop

    def push(self, *args, **kwargs):
        result = old_push(self, *args, **kwargs)
        counts['push'] += 1
        if token is not None:
            token.cancel()
        return result

    def pop(self, *args, **kwargs):
        result = old_pop(self, *args, **kwargs)
        counts['pop'] += 1
        return result

    monkeypatch.setattr(SearchPathRuntime, 'push', push)
    monkeypatch.setattr(SearchPathRuntime, 'pop', pop)
    return counts


def test_q_classification_reports_actual_successful_runtime_work(monkeypatch):
    session, player = prepared()
    before = session.state, session.to_record(), session._search_witnesses
    counts = observe(monkeypatch)
    decision = player.choose_action(session, SearchLimits(max_depth=6,
        max_nodes=1024, max_time_seconds=10, quiescence_max_depth=4,
        quiescence_hard_max_depth=8))
    assert decision.runtime_pushes == counts['push']
    assert decision.runtime_pops == counts['pop'] == counts['push']
    assert decision.runtime_depth_balanced is True
    # Many classified actions do not become a searched node. Keep both measures.
    assert decision.runtime_pushes > decision.nodes + decision.qnodes
    assert decision.nodes + decision.qnodes <= 1024
    assert decision.action in session.legal_actions()
    assert before == (session.state, session.to_record(), session._search_witnesses)


def test_cancelled_search_reports_balanced_completed_work(monkeypatch):
    session, player = prepared()
    before = session.state, session.to_record(), session._search_witnesses
    token = CancellationToken()
    counts = observe(monkeypatch, token)
    decision = player.choose_action(session, SearchLimits(max_depth=6,
        max_nodes=1024, max_time_seconds=10, quiescence_max_depth=4),
        cancel_token=token)
    assert decision.termination_reason == 'cancelled'
    assert decision.runtime_pushes == counts['push'] == 1
    assert decision.runtime_pops == counts['pop'] == 1
    assert decision.runtime_depth_balanced is True
    assert decision.action in session.legal_actions()
    assert before == (session.state, session.to_record(), session._search_witnesses)
