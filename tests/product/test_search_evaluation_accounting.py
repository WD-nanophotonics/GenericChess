"""Cost counters match actual evaluator work across public search paths."""
import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from ai_fixtures import build_4x4_rooks
from rule_semantics_ir_fixtures import cannon_ruleset


@pytest.mark.parametrize('semantic', [False, True])
@pytest.mark.parametrize('qdepth', [0, 2])
@pytest.mark.parametrize('root_scan', [False, True])
def test_public_cost_counters_equal_actual_calls_and_elapsed_evaluator_time(
        monkeypatch, semantic, qdepth, root_scan):
    compiled = (compile_ruleset_for_execution(cannon_ruleset())
                if semantic else build_4x4_rooks())
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    clock = [0.0]
    monkeypatch.setattr('generic_chess.ai.alphabeta.search.time.monotonic',
                        lambda: clock[0])
    monkeypatch.setattr('generic_chess.ai.alphabeta.search.time.perf_counter',
                        lambda: clock[0])

    class Counted(Evaluator):
        def __init__(self):
            super().__init__(compiled, profile, config)
            self.calls = 0

        def evaluate(self, state):
            self.calls += 1
            clock[0] += .125
            return super().evaluate(state)

    counted = Counted()
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        evaluator_override=counted, tuning=SearchTuning(use_root_tactical=root_scan))
    session = GameSession(compiled)
    decision = player.choose_action(session, SearchLimits(max_depth=2,
        max_nodes=8192, quiescence_max_depth=qdepth, quiescence_hard_max_depth=4))
    assert counted.calls > 0
    assert decision.evaluation_calls == counted.calls
    assert decision.evaluation_seconds == pytest.approx(counted.calls * .125)
    assert decision.action in session.legal_actions()
