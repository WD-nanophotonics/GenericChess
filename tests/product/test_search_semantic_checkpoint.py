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
