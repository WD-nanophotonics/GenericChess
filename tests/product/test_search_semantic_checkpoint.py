"""Semantic work observes live budgets without losing abort precedence."""
import pytest

from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits


class Cancel:
    def __init__(self):
        self.cancelled = False
        self.polls = 0

    def is_cancelled(self):
        self.polls += 1
        return self.cancelled


def context(stats, budget):
    return search._Context(None, None, None, stats, budget, SearchTuning(),
                           True, True, 0, 0, None)


def test_semantic_checkpoint_keeps_live_deadline_and_abort_precedence(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(search.time, 'monotonic', lambda: clock[0])
    token = Cancel()
    stats = SearchStatistics(nodes=5, qnodes=5)
    budget = search._Budget(SearchLimits(max_nodes=10, max_time_seconds=5), token)
    ctx = context(stats, budget)
    clock[0] = 6
    token.cancelled = True
    with pytest.raises(search.SearchAborted, match='^node_limit$'):
        ctx.checkpoint()
    assert token.polls == 0
    stats.qnodes = 4
    with pytest.raises(search.SearchAborted, match='^cancelled$'):
        ctx.checkpoint()
    token.cancelled = False
    with pytest.raises(search.SearchAborted, match='^time_limit$'):
        ctx.checkpoint()
    # Iteration scheduling may change the budget after callback creation.
    budget._deadline = 7
    ctx.checkpoint()
    assert token.polls == 3


def test_each_semantic_poll_checks_cancellation_without_waiting_for_a_new_node():
    token = Cancel()
    ctx = context(SearchStatistics(nodes=1),
                  search._Budget(SearchLimits(max_nodes=100), token))
    for _ in range(20):
        ctx.checkpoint()
    token.cancelled = True
    with pytest.raises(search.SearchAborted, match='^cancelled$'):
        ctx.checkpoint()
    assert token.polls == 21


@pytest.mark.parametrize("cancelled", [False, True])
def test_root_history_import_is_charged_before_search_and_keeps_legal_fallback(monkeypatch, cancelled):
    from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from generic_chess.ai.evaluation import EvaluationConfig, EvaluationProfileCache, Evaluator
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.core.search_runtime import SearchPathRuntime

    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    session = GameSession(compiled)
    cfg = EvaluationConfig()
    profile = EvaluationProfileCache(use_disk=False).get_or_build(compiled, cfg)[0]
    evaluator = Evaluator(compiled, profile, cfg)
    initial = session.state
    clock = [0.0]
    original = SearchPathRuntime.from_state

    def costly_import(*args, **kwargs):
        result = original(*args, **kwargs)
        clock[0] += 2.0  # simulated history-import cost, no wall-clock sleep
        return result

    monkeypatch.setattr(search.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(SearchPathRuntime, "from_state", costly_import)
    token = Cancel()
    token.cancelled = cancelled
    stats = SearchStatistics()
    action, score, pv, reason = search.run_root_search(
        initial, compiled, evaluator, TranspositionTable(256),
        SearchLimits(max_depth=2, max_nodes=20, max_time_seconds=1,
                     quiescence_max_depth=0, quiescence_hard_max_depth=0),
        token, stats, use_tt=True, use_ordering=True,
        _history_witnesses=session._search_witnesses,
    )
    assert reason == ("cancelled" if cancelled else "time_limit")
    assert stats.nodes == stats.qnodes == stats.completed_depth == 0
    assert action in session.legal_actions()
    assert pv == () and session.state == initial
