"""Frozen original-Player OFF/ON pilot; no product patch or automatic refill."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value, write_record
from tools.local_agent.common import read_json
from tools.local_agent.session import record_work


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(record_value(value), sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def load(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


class CallerDeadline:
    """Same cooperative caller-clock token for both policies; no worker."""

    def __init__(self, deadline):
        self.deadline = deadline
        self.observed = False

    def is_cancelled(self):
        self.observed = self.observed or time.perf_counter() >= self.deadline
        return self.observed


def provider_metrics(player):
    p = player.native_legality_provider
    return {'present': p is not None,
            'availability': p.availability_metrics if p else {},
            'check': p.check_metrics if p else {}}


def metric_delta(before, after):
    return {group: {k: v - before[group].get(k, 0)
                    for k, v in after[group].items()}
            for group in ('availability', 'check')}


def make_player(compiled, on):
    return AlphaBetaPlayer(
        compiled, use_disk_cache=False, tuning=SearchTuning(use_pvs=on),
        use_native_semantic_legality=True,
        use_native_semantic_availability=True, use_native_semantic_check=True)


def make_session(row):
    rules = ruleset_from_dict(row['RuleSet'])
    assert compute_fingerprint(rules) == row['fingerprint']
    c = compile_legacy_ruleset_for_semantic_execution(rules)
    s = GameSession.replay(c, deserialize_game_record(json.dumps(row['record'])))
    assert not s.state.terminal_status.is_terminal
    return c, s


def admission(plan, tick, batch_seconds, call_seconds):
    flags = read_json(Path('.local_agent/rollout.json'))
    if any(flags.get(k, False) for k in ('user_paused', 'stopped',
                                        'research_stopped', 'stop_requested')):
        return 'scoped_stop'
    # In-flight reserve is explicit; never dispatch right up to the cap.
    reserve = max(plan['inflight_reserve_seconds'], call_seconds + 1)
    if time.perf_counter() - tick + reserve >= batch_seconds:
        return 'batch_dispatch_reserve'
    remaining = (datetime.fromisoformat(plan['whole_deadline_utc']) -
                 datetime.now(timezone.utc)).total_seconds()
    if remaining <= plan['delivery_reserve_seconds'] + reserve:
        return 'whole_chain_delivery_reserve'
    return None


def choose(player, session, limits, qid, output):
    before = session.to_record()
    metrics = provider_metrics(player)
    begin = stamp()
    t0, cpu = time.perf_counter(), time.process_time()
    token = CallerDeadline(t0 + limits.max_time_seconds)
    try:
        decision = player.choose_action(session, limits, cancel_token=token)
    except BaseException as exc:
        end = stamp()
        write_record(output / 'returns' / (qid + '.json'), {
            'query_id': qid, 'status': 'RAISED', 'started_at': begin,
            'ended_at': end, 'error_type': type(exc).__name__, 'error': str(exc),
            'outer_seconds': time.perf_counter() - t0,
            'cpu_seconds': time.process_time() - cpu})
        record_work(begin, end, 'research', str(output / 'returns' / (qid + '.json')))
        raise
    end = stamp()
    wall, cpu = time.perf_counter() - t0, time.process_time() - cpu
    row = {'query_id': qid, 'status': 'RETURNED', 'started_at': begin,
           'ended_at': end, 'outer_seconds': wall, 'cpu_seconds': cpu,
           'caller_deadline_observed': token.observed,
           'limits': record_value(limits), 'decision': record_value(decision),
           'record_before_sha256': digest(before),
           'provider_present': metrics['present'],
           'provider_delta': metric_delta(metrics, provider_metrics(player)),
           'timing_eligible': wall <= limits.max_time_seconds * 1.1}
    # Original return precedes root/action/PV validation and ledger bookkeeping.
    write_record(output / 'returns' / (qid + '.json'), row)
    record_work(begin, end, 'research', str(output / 'returns' / (qid + '.json')))
    assert session.to_record() == before, 'query mutated full root'
    assert decision.action is not None and decision.action in session.legal_actions()
    pv = GameSession.replay(player.compiled, before)
    for action in decision.principal_variation:
        pv.submit(action)
    assert decision.runtime_depth_balanced is True
    assert metrics['present'], 'requested Native provider unavailable'
    assert decision.native_legality_fallbacks == 0
    assert decision.native_legality_operational_failures == 0
    assert row['provider_delta']['availability'].get('declines', 0) == 0
    return row, decision.action


def run(inputs, plan_path, output):
    assert not output.exists(), 'no refill/resume into frozen output'
    plan = load(plan_path)
    assert hashlib.sha256(Path(inputs).read_bytes()).hexdigest() == plan['input_sha256']
    for f, h in plan['sources'].items():
        assert hashlib.sha256(Path(f).read_bytes()).hexdigest() == h, f
    rows = [r for r in load(inputs)['rows'] if r['prefix_length'] == 2]
    assert [r['id'] for r in rows] == plan['root_ids'] and len(rows) == 12
    output.mkdir(parents=True)
    (output / 'returns').mkdir()
    write_record(output / 'executed-source.json', {
        'driver': Path(__file__).read_text(encoding='utf-8'),
        'plan_sha256': hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
        'input_sha256': plan['input_sha256'],
        'product_sources': {f: Path(f).read_bytes().decode('utf-8')
                            for f in plan['sources'] if f.startswith('generic_chess/')}})
    started = stamp()
    qualification, games, halt = [], [], None
    tick = time.perf_counter()
    for i, root in enumerate(rows):
        pair = []
        for on in ((False, True) if i % 2 == 0 else (True, False)):
            slot = {'slot': len(qualification), 'case_id': root['id'], 'on': on}
            halt = halt or admission(plan, tick, 90, 3)
            if halt:
                slot.update(status='NOT_RUN', reason=halt)
            else:
                try:
                    c, s = make_session(root)
                    player = make_player(c, on)
                    row, _ = choose(player, s, SearchLimits(
                        max_depth=3, max_nodes=50000, max_time_seconds=3,
                        quiescence_max_depth=4, quiescence_hard_max_depth=8),
                        f'q{len(qualification):02d}', output)
                    slot.update(status='RETURNED', query_id=row['query_id'],
                                decision=row['decision'])
                    pair.append(slot)
                    assert row['decision']['completed_depth'] == 3, 'incomplete qualification'
                except Exception as exc:
                    slot.update(status='FAILED', error_type=type(exc).__name__, error=str(exc))
                    halt = 'qualification_failure'
            qualification.append(slot)
            write_record(output / 'qualification.json', qualification)
        if len(pair) == 2 and pair[0]['decision']['score'] != pair[1]['decision']['score']:
            halt = 'complete_depth_score_mismatch'
            write_record(output / 'qualification-mismatch.json', pair)
    qualification_end = stamp()
    game_tick = time.perf_counter()
    for ri, root in enumerate(rows):
        for on_seat in ((0, 1) if ri % 2 == 0 else (1, 0)):
            game = {'game_id': len(games), 'case_id': root['id'],
                    'family': root['family'], 'fingerprint': root['fingerprint'],
                    'on_seat': on_seat, 'initial_record': root['record'],
                    'status': 'NOT_STARTED', 'queries': []}
            halt = halt or admission(plan, game_tick, 2700, 1)
            if halt:
                game['reason'] = halt
            else:
                game_start = time.perf_counter()
                try:
                    c, s = make_session(root)
                    constructors = {}
                    players = {}
                    for seat in (0, 1):
                        t = time.perf_counter()
                        players[seat] = make_player(c, seat == on_seat)
                        constructors[str(seat)] = time.perf_counter() - t
                    game.update(status='RUNNING', constructor_seconds=constructors,
                                setup_seconds=time.perf_counter() - game_start,
                                started_at=stamp())
                    while not s.state.terminal_status.is_terminal:
                        halt = admission(plan, game_tick, 2700, 1)
                        if halt:
                            break
                        assert len(game['queries']) < 94, 'caller94turn cap before Core terminal'
                        seat = s.state.position.side_to_move
                        qid = 'g' + str(sum(len(g['queries']) for g in games) +
                                       len(game['queries'])).zfill(4)
                        row, action = choose(players[seat], s, SearchLimits(
                            max_depth=64, max_nodes=500000, max_time_seconds=1,
                            quiescence_max_depth=4, quiescence_hard_max_depth=8),
                            qid, output)
                        row.update(seat=seat, on=seat == on_seat,
                                   ply_before=s.state.ply_count)
                        s.submit(action)
                        row['record_after_sha256'] = digest(s.to_record())
                        game['queries'].append(row)
                        write_record(output / f'game-{len(games):02d}-queries.json', game['queries'])
                        write_record(output / 'progress.json', {
                            'at': stamp(), 'completed_games': len(games),
                            'game_id': len(games), 'case_id': root['id'],
                            'turns': len(game['queries']),
                            'seconds': time.perf_counter() - game_tick,
                            'Core_status': record_value(s.state.terminal_status)})
                    game.update(status='TERMINAL' if s.state.terminal_status.is_terminal else 'UNFINISHED',
                                reason=halt, final_record=record_value(s.to_record()),
                                Core_terminal=record_value(s.state.terminal_status),
                                Session_result=record_value(s.result), ended_at=stamp(),
                                outer_seconds=time.perf_counter() - game_start,
                                timing_eligible=all(q['timing_eligible'] for q in game['queries']))
                except Exception as exc:
                    game.update(status='FAILED', error_type=type(exc).__name__, error=str(exc))
                    halt = 'game_or_recorder_failure'
            games.append(game)
            write_record(output / f'game-{game["game_id"]:02d}.json', game)
            write_record(output / 'games.json', games)
    summary = {'started_at': started, 'qualification_ended_at': qualification_end,
               'ended_at': stamp(), 'qualification_slots': len(qualification),
               'qualification_statuses': dict(Counter(x['status'] for x in qualification)),
               'game_statuses': dict(Counter(x['status'] for x in games)),
               'game_Player_returns': sum(len(g['queries']) for g in games),
               'game_batch_seconds': time.perf_counter() - game_tick, 'halt': halt,
               'new_solver': 0, 'product_changes': 0}
    write_record(output / 'summary.json', summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.plan, args.output)
