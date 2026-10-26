"""Research consumer controls; no added Player or game calls."""
from datetime import datetime, timedelta, timezone

from scripts import leaper_pvs_quality_pilot as pilot
from scripts import verify_leaper_pvs_quality_pilot as reader
import pytest


def plan():
    return {'inflight_reserve_seconds': 5, 'delivery_reserve_seconds': 720,
            'whole_deadline_utc': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}


def test_caller_deadline_stays_observed(monkeypatch):
    token = pilot.CallerDeadline(10)
    monkeypatch.setattr(pilot.time, 'perf_counter', lambda: 9)
    assert not token.is_cancelled()
    monkeypatch.setattr(pilot.time, 'perf_counter', lambda: 10)
    assert token.is_cancelled()
    monkeypatch.setattr(pilot.time, 'perf_counter', lambda: 8)
    assert token.is_cancelled()


def test_batch_dispatch_reserves_inflight_not_just_elapsed(monkeypatch):
    monkeypatch.setattr(pilot, 'read_json', lambda path: {})
    monkeypatch.setattr(pilot.time, 'perf_counter', lambda: 86)
    assert pilot.admission(plan(), 0, 90, 3) == 'batch_dispatch_reserve'
    monkeypatch.setattr(pilot.time, 'perf_counter', lambda: 84)
    assert pilot.admission(plan(), 0, 90, 3) is None


def test_whole_delivery_and_stop_take_precedence(monkeypatch):
    monkeypatch.setattr(pilot, 'read_json', lambda path: {})
    p = plan()
    p['whole_deadline_utc'] = (datetime.now(timezone.utc) + timedelta(seconds=724)).isoformat()
    assert pilot.admission(p, pilot.time.perf_counter(), 2700, 1) == 'whole_chain_delivery_reserve'
    monkeypatch.setattr(pilot, 'read_json', lambda path: {'user_paused': True})
    assert pilot.admission(p, pilot.time.perf_counter(), 2700, 1) == 'scoped_stop'


def test_actual_metric_delta_retains_partial_calls():
    before = {'availability': {'calls': 10, 'queries': 9}, 'check': {'calls': 4}}
    after = {'availability': {'calls': 12, 'queries': 10, 'declines': 1},
             'check': {'calls': 6, 'queries': 1}}
    assert pilot.metric_delta(before, after) == {
        'availability': {'calls': 2, 'queries': 1, 'declines': 1},
        'check': {'calls': 2, 'queries': 1}}


def test_unknown_outcome_keeps_fixed_denominator():
    result = reader.fixed_bounds([1, 0.5, None, 0], 4)
    assert result['missing'] == 1
    assert result['mean_bounds'] == [0.375, 0.625]
    with pytest.raises(AssertionError):
        reader.fixed_bounds([1, 0.5, 0], 4)
    with pytest.raises(AssertionError):
        reader.fixed_bounds([float('nan')], 1)


def test_points_uses_on_seat_and_real_terminal():
    assert reader.points({'status': 'UNFINISHED'}) is None
    game = {'status': 'TERMINAL', 'on_seat': 1,
            'Core_terminal': {'winner': 0, 'status': 'checkmate'}}
    assert reader.points(game) == 0
    game['on_seat'] = 0
    assert reader.points(game) == 1
    game['Core_terminal'] = {'winner': None, 'status': 'ongoing'}
    with pytest.raises(AssertionError):
        reader.points(game)


def test_replay_action_binds_semantic_identity_not_coordinates():
    from generic_chess.core.actions import SemanticBoardMove
    from generic_chess.core.coordinates import Square
    from scripts.research_record import record_value
    a = SemanticBoardMove('pattern-a', 'geometry', 'A', Square(0, 0), Square(1, 1))
    b = SemanticBoardMove('pattern-b', 'geometry', 'A', Square(0, 0), Square(1, 1))
    class Session:
        def legal_actions(self):
            return [a, b]
    assert reader.action(record_value(b), Session()) == b
    incomplete = record_value(b)
    del incomplete['pattern_id']
    with pytest.raises(AssertionError):
        reader.action(incomplete, Session())


def test_archived_original_is_byte_checked(tmp_path):
    import gzip
    import json
    import hashlib
    raw = b'{"query_id":"g0000","score":1}\n'
    entry = {'original_utf8': raw.decode(), 'sha256': hashlib.sha256(raw).hexdigest()}
    (tmp_path / 'returns.json.gz').write_bytes(gzip.compress(json.dumps({'g0000': entry}).encode()))
    assert reader.original_return(tmp_path, 'g0000')['score'] == 1
    reader._RETURN_ARCHIVES.pop(str(tmp_path.resolve()))
    entry['original_utf8'] = '{"query_id":"g0000","score":2}\n'
    (tmp_path / 'returns.json.gz').write_bytes(gzip.compress(json.dumps({'g0000': entry}).encode()))
    with pytest.raises(AssertionError, match='raw byte hash'):
        reader.original_return(tmp_path, 'g0000')
