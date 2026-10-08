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
    monkeypatch.setattr(search_module.time, 'monotonic', lambda: next(ticks))
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
