"""Search generation cost includes cached-boundary/root and qsearch requests."""
from types import SimpleNamespace

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import SearchAborted, _runtime_legal_actions
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from ai_fixtures import build_4x4_rooks
from rule_semantics_ir_fixtures import cannon_ruleset


@pytest.mark.parametrize('semantic', [False, True])
@pytest.mark.parametrize('qdepth', [0, 2])
@pytest.mark.parametrize('root_scan', [False, True])
def test_actual_generation_duration_survives_coarse_budget_clock(
        monkeypatch, semantic, qdepth, root_scan):
    compiled = (compile_ruleset_for_execution(cannon_ruleset())
                if semantic else build_4x4_rooks())
    clock = [0.0]
    original = SearchPathRuntime.legal_actions

    def measured(self, *args, **kwargs):
        # Runtime push validation can read an already cached legal list. Charge
        # only actual generation, independently of the search's timing helper.
        miss = self._legal_cache is None
        try:
            return original(self, *args, **kwargs)
        finally:
            if miss:
                clock[0] += .125

    monkeypatch.setattr(SearchPathRuntime, 'legal_actions', measured)
    monkeypatch.setattr('generic_chess.ai.alphabeta.search.time.monotonic', lambda: 0)
    monkeypatch.setattr('generic_chess.ai.alphabeta.search.time.perf_counter',
                        lambda: clock[0])
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=root_scan))
    session = GameSession(compiled)
    decision = player.choose_action(session, SearchLimits(max_depth=2,
        max_nodes=8192, quiescence_max_depth=qdepth, quiescence_hard_max_depth=4))
    assert clock[0] > 0
    assert decision.legal_generation_seconds == pytest.approx(clock[0])
    assert decision.legal_generation_calls > 0
    assert decision.action in session.legal_actions()


def test_cancelled_generation_attempt_keeps_cost(monkeypatch):
    clock = [0.0]

    class Runtime:
        def legal_actions(self, checkpoint):
            clock[0] += .25
            raise SearchAborted('cancelled')

    monkeypatch.setattr('generic_chess.ai.alphabeta.search.time.perf_counter',
                        lambda: clock[0])
    ctx = SimpleNamespace(runtime=Runtime(), stats=SearchStatistics())
    with pytest.raises(SearchAborted, match='cancelled'):
        _runtime_legal_actions(ctx, None)
    assert ctx.stats.legal_generation_calls == 1
    assert ctx.stats.legal_generation_seconds == .25
    assert ctx.stats.legal_actions_generated == 0
