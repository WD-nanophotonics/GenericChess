"""Finite saved-state qualification. No Player, new game or solver calls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time

from generic_chess.core.identity import position_identity_key
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts.leaper_child_candidate import ChildRuntime, selected_child
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.research_record import record_value, write_record
from scripts.verify_leaper_pvs_quality_pilot import load, original_return, full_digest
from tools.local_agent.common import read_json
from tools.local_agent.session import record_work


def stamp():
    return datetime.now(timezone.utc).isoformat()


def state_snapshot(r):
    return (r.position, r.ply_count, r.terminal_status, tuple(r.history),
            r.runtime_hash, r.search_key(), r.repetition_counts,
            {h: tuple((v.identity, v.count) for v in b) for h, b in r._occurrences.items()},
            r.depth, r._history_context, r._no_progress_context)


def make_runtime(cls, c, s):
    return cls.from_state(s.state, c, history_witnesses=s._search_witnesses)


def paired_transition(c, s, action):
    a, b = make_runtime(SearchPathRuntime, c, s), make_runtime(ChildRuntime, c, s)
    left, right = a.legal_actions(), b.legal_actions()
    assert left == right == s.legal_actions(), 'parent ordered frontier'
    before_a, before_b = state_snapshot(a), state_snapshot(b)
    assert before_a == before_b
    a.push(action); b.push(action)
    assert state_snapshot(a) == state_snapshot(b), 'full child runtime differs'
    child_frontier = a.legal_actions()
    assert child_frontier == b.legal_actions(), 'child ordered frontier differs'
    child_position, terminal, ply = a.position, a.terminal_status, a.ply_count
    child_count = a.occurrence_count()
    a.pop(); b.pop()
    assert state_snapshot(a) == before_a and state_snapshot(b) == before_b
    a.assert_balanced(); b.assert_balanced()
    assert b.child_successes == 1 and b.child_fallbacks == 0, 'certified state did not take fast path'
    return {'child': child_position, 'terminal': terminal, 'ply': ply,
            'count': child_count, 'hits': b.child_successes,
            'parent_legal_count': len(left), 'child_legal_count': len(child_frontier)}


class InjectedAbort(BaseException):
    pass


def effect_boundary(c, s, action):
    r = make_runtime(ChildRuntime, c, s); r.legal_actions()
    semantic, binding = r._bindings[action]
    expected = []; observed = []
    generic = r.child_engine._transition(r.position, semantic, binding,
                                        checkpoint=lambda: expected.append('effect'))
    fast = selected_child(r, r.child_engine, r.position, semantic, binding,
                          checkpoint=lambda: observed.append('effect'))
    assert fast == generic and expected == observed
    for failure in range(1, len(expected) + 1):
        for candidate in (False, True):
            calls = []
            def fail():
                calls.append('effect')
                if len(calls) == failure:
                    raise InjectedAbort()
            try:
                if candidate:
                    selected_child(r, r.child_engine, r.position, semantic, binding, checkpoint=fail)
                else:
                    r.child_engine._transition(r.position, semantic, binding, checkpoint=fail)
            except InjectedAbort:
                assert len(calls) == failure
            else:
                raise AssertionError('abort swallowed')
    return {'effects': len(expected), 'abort_boundaries': len(expected),
            'full_action': record_value(action)}


def qualify(inputs, pilot, output, deadline):
    assert not output.exists(), 'new qualification output required'
    output.mkdir(parents=True)
    start = stamp(); tick = time.perf_counter()
    roots = {x['id']: x for x in load(inputs)['rows'] if x['prefix_length'] == 2}
    assert len(roots) == 12
    report = {'started_at': start, 'status': 'ACTIVE', 'root_frontiers': [],
              'saved_games': [], 'effect_boundaries': [], 'selected_transitions': 0,
              'new_Player_calls': 0, 'new_games': 0, 'failures': []}
    write_record(output / 'executed-source.json', {
        f: Path(f).read_bytes().decode('utf-8') for f in (
            'scripts/leaper_child_candidate.py', 'scripts/validate_leaper_child.py')})
    write_record(output / 'input-binding.json', {
        'inputs': str(inputs), 'input_sha256': hashlib.sha256(Path(inputs).read_bytes()).hexdigest(),
        'games_sha256': hashlib.sha256((pilot / 'games.json.gz').read_bytes()).hexdigest(),
        'candidate_sha256': hashlib.sha256(Path('scripts/leaper_child_candidate.py').read_bytes()).hexdigest(),
        'root_ids': list(roots)})
    def check():
        flags = read_json(Path('.local_agent/rollout.json'))
        assert not any(flags.get(k) for k in ('user_paused', 'stopped', 'research_stopped', 'stop_requested'))
        assert datetime.now(timezone.utc) < datetime.fromisoformat(deadline)
    try:
        for root in roots.values():
            check(); c, s = make_session(root)
            actions = s.legal_actions()
            for action in actions:
                paired_transition(c, s, action)
            report['root_frontiers'].append({'id': root['id'], 'actions': len(actions), 'all_passed': True})
            report['effect_boundaries'].append({'id': root['id'], 'kind': 'root',
                                                 **effect_boundary(c, s, actions[0])})
            write_record(output / 'progress.json', report)
        captures = set()
        for game in load(pilot / 'games.json'):
            root = roots[game['case_id']]; c, s = make_session(root)
            checks = []
            for query in game['queries']:
                check()
                raw = original_return(pilot, query['query_id'])
                assert raw['decision'] == query['decision']
                assert raw['record_before_sha256'] == full_digest(s.to_record())
                matches = [a for a in s.legal_actions() if record_value(a) == raw['decision']['action']]
                assert len(matches) == 1
                action = matches[0]
                r = paired_transition(c, s, action)
                size = c.board_size
                target = action.to_square.rank * size + action.to_square.file
                if s.state.position.board[target] is not None and game['case_id'] not in captures:
                    captures.add(game['case_id'])
                    report['effect_boundaries'].append({'id': game['case_id'], 'kind': 'saved_capture',
                                                        **effect_boundary(c, s, action)})
                s.submit(action)
                assert (r['child'], r['terminal'], r['ply']) == (
                    s.state.position, s.state.terminal_status, s.state.ply_count)
                assert r['count'] == dict(s.state.repetition_counts)[position_identity_key(s.state.position, c)]
                checks.append({'query_id': query['query_id'], 'full_record_sha256': raw['record_before_sha256'],
                               'selected_fast_hits': r['hits'], 'exact_child_frontier_history_undo': True})
                report['selected_transitions'] += 1
            assert record_value(s.to_record()) == game['final_record']
            assert record_value(s.state.terminal_status) == game['Core_terminal']
            entry = {'game_id': game['game_id'], 'case_id': game['case_id'], 'checks': checks,
                     'final_Core_terminal': record_value(s.state.terminal_status)}
            # Preserve completed validation per game, never refill old queries.
            write_record(output / (str(game['game_id']) + '.json'), entry)
            report['saved_games'].append({'game_id': game['game_id'], 'checks': len(checks)})
            write_record(output / 'progress.json', report)
        assert report['selected_transitions'] == 2115 and len(report['saved_games']) == 24
        report['status'] = 'PASSED'
    except BaseException as exc:
        report['status'] = 'FAILED'
        report['failures'].append({'error_type': type(exc).__name__, 'error': str(exc)})
        raise
    finally:
        report['ended_at'] = stamp(); report['outer_seconds'] = time.perf_counter() - tick
        write_record(output / 'qualification.json', report)
        record_work(start, report['ended_at'], 'validation', str(output / 'qualification.json'))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--pilot', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--deadline', required=True)
    args = p.parse_args()
    r = qualify(args.inputs, args.pilot, args.output, args.deadline)
    print({k: r[k] for k in ('status', 'selected_transitions', 'outer_seconds')})
