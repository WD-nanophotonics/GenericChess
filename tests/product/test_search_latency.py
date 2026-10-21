"""Public first-completion latency remains first across iterative deepening."""
from itertools import count

import pytest

import generic_chess.ai.alphabeta.player as player_module
import generic_chess.ai.alphabeta.search as search_module
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from ai_fixtures import build_4x4_rooks


def test_first_completion_latency_is_not_overwritten_by_later_depth(monkeypatch):
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False))
    stats = SearchStatistics()
    ticks = count(100)
    # Deterministic increasing clock; no wall deadline is used in this test.
    monkeypatch.setattr(search_module.time, 'perf_counter', lambda: next(ticks))
    monkeypatch.setattr(player_module, 'SearchStatistics', lambda: stats)
    reports = []
    decision = player.choose_action(session, SearchLimits(
        max_depth=2, max_nodes=4096, quiescence_max_depth=0),
        progress_callback=lambda depth, nodes, qnodes: reports.append(
            (depth, stats.time_to_first_completed_iteration)))
    assert [depth for depth, _ in reports] == [1, 2]
    first = reports[0][1]
    assert first is not None and first > 0
    assert reports[1][1] == decision.time_to_first_completed_iteration == first
    assert decision.elapsed_seconds > first


@pytest.mark.parametrize('root_scan', [False, True])
def test_public_first_iteration_node_abort_retains_cause_and_legal_fallback(root_scan):
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    before = session.state
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=root_scan))
    decision = player.choose_action(session, SearchLimits(
        max_depth=2, max_nodes=1, quiescence_max_depth=0))
    assert decision.termination_reason == 'node_limit'
    assert decision.root_scan_used_fallback and decision.completed_depth == 0
    assert decision.time_to_first_completed_iteration is None
    assert decision.action in session.legal_actions()
    assert session.state == before


def test_terminal_decision_elapsed_uses_high_resolution_clock(monkeypatch):
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    session.resign()
    player = AlphaBetaPlayer(compiled, use_disk_cache=False)
    ticks = iter((12.0, 12.0025))
    # The coarse monotonic clock must not be used for sub-millisecond caller
    # telemetry; perf_counter is monotonic and high resolution on Windows.
    monkeypatch.setattr(player_module.time, 'monotonic', lambda: 900.0)
    monkeypatch.setattr(player_module.time, 'perf_counter', lambda: next(ticks))
    decision = player.choose_action(session, SearchLimits())
    assert decision.elapsed_seconds == pytest.approx(0.0025)


def test_search_deadline_uses_high_resolution_monotonic_clock(monkeypatch):
    ticks = iter((5.0, 5.004))
    monkeypatch.setattr(search_module.time, 'monotonic', lambda: 0.0)
    monkeypatch.setattr(search_module.time, 'perf_counter', lambda: next(ticks))
    budget = search_module._Budget(SearchLimits(max_time_seconds=0.003), None)
    with pytest.raises(search_module.SearchAborted, match='time_limit'):
        budget.check_iteration(SearchStatistics())
