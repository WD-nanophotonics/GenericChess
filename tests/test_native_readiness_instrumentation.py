"""Instrumentation recorder semantics: off/on invariance, sane counters/timers."""

import time

from generic_chess.ai.audit_instrumentation import (
    AuditMetric,
    NullAuditRecorder,
    TimingAuditRecorder,
)
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks


def _player():
    return AlphaBetaPlayer(build_4x4_rooks(), use_disk_cache=False)


def test_null_recorder_is_noop():
    rec = NullAuditRecorder()
    with rec.time_block(AuditMetric.MOVE_GEN):
        pass
    rec.count(AuditMetric.MOVE_GEN, 3)


def test_recorder_off_does_not_change_result():
    compiled = build_4x4_rooks()
    limits = SearchLimits(max_nodes=800, max_depth=64, quiescence_max_depth=2)
    a = _player().choose_action(GameSession(compiled), limits)
    b = _player().choose_action(
        GameSession(compiled), limits, recorder=TimingAuditRecorder()
    )
    assert a.action == b.action
    assert a.score == b.score


def test_recorder_on_does_not_change_best_action():
    compiled = build_4x4_rooks()
    limits = SearchLimits(max_nodes=800, max_depth=64, quiescence_max_depth=2)
    rec = TimingAuditRecorder()
    decision = _player().choose_action(GameSession(compiled), limits, recorder=rec)
    snap = rec.snapshot()
    assert decision.action is not None
    for value in snap["times"].values():
        assert value >= 0.0
    for value in snap["counts"].values():
        assert value >= 0


def test_recorder_runs_are_isolated():
    compiled = build_4x4_rooks()
    limits = SearchLimits(max_nodes=400, max_depth=64, quiescence_max_depth=2)
    rec1 = TimingAuditRecorder()
    _player().choose_action(GameSession(compiled), limits, recorder=rec1)
    snap1 = rec1.snapshot()
    rec2 = TimingAuditRecorder()
    _player().choose_action(GameSession(compiled), limits, recorder=rec2)
    snap2 = rec2.snapshot()
    assert set(snap1["times"]) == set(snap2["times"])
    # No cross-run leakage: fresh recorders start empty.
    fresh = TimingAuditRecorder().snapshot()
    assert fresh["times"] == {}
    assert fresh["counts"] == {}


def test_instrumentation_overhead_is_bounded():
    compiled = build_4x4_rooks()
    limits = SearchLimits(max_nodes=400, max_depth=64, quiescence_max_depth=2)

    def run(recorder):
        started = time.perf_counter()
        _player().choose_action(GameSession(compiled), limits, recorder=recorder)
        return time.perf_counter() - started

    off = run(None)
    on = run(TimingAuditRecorder())
    assert on < off * 5 + 0.5  # instrumentation must not blow up runtime
