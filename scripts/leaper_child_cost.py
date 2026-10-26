"""Frozen 144-slot original-Player cost study; no games or automatic refill."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import time

from generic_chess.ai.limits import SearchLimits
from scripts.leaper_pvs_quality_pilot import CallerDeadline, make_player, make_session, provider_metrics, metric_delta
from scripts.research_record import write_record, record_value
from scripts.verify_leaper_pvs_quality_pilot import load, full_digest
from tools.local_agent.common import read_json
from tools.local_agent.session import record_work

_import_wall, _import_cpu = time.perf_counter(), time.process_time()
from scripts.leaper_child_candidate import candidate_arm, metrics, BASE_RUNTIME, ChildRuntime
CANDIDATE_IMPORT_WALL = time.perf_counter() - _import_wall
CANDIDATE_IMPORT_CPU = time.process_time() - _import_cpu

TIME_FIELDS = frozenset({'elapsed_seconds', 'time_to_first_legal_action',
    'time_to_first_completed_iteration', 'ordering_seconds',
    'legal_generation_seconds', 'evaluation_seconds'})


def stamp():
    return datetime.now(timezone.utc).isoformat()


def comparable_decision(raw):
    return {k: v for k, v in raw.items() if k not in TIME_FIELDS}


def comparable_native(raw):
    return {g: {k: v for k, v in values.items() if not k.endswith('seconds')}
            for g, values in raw.items()}


def admission(plan, tick):
    flags = read_json(Path('.local_agent/rollout.json'))
    if any(flags.get(k) for k in ('stopped', 'user_paused', 'research_stopped', 'stop_requested')):
        return 'scoped_stop'
    if time.perf_counter() - tick + plan['inflight_reserve_seconds'] >= plan['batch_seconds']:
        return 'batch_dispatch_reserve'
    remaining = (datetime.fromisoformat(plan['whole_deadline']) - datetime.now(timezone.utc)).total_seconds()
    if remaining <= plan['delivery_reserve_seconds'] + plan['inflight_reserve_seconds']:
        return 'whole_delivery_reserve'
    return None


def slot_call(c, session, slot, output, seconds):
    root = session.to_record()
    limits = SearchLimits(max_depth=slot['depth'], max_nodes=500000,
                          max_time_seconds=seconds, quiescence_max_depth=4,
                          quiescence_hard_max_depth=8)
    on = slot['candidate']
    search = importlib.import_module('generic_chess.ai.alphabeta.search')
    assert search.SearchPathRuntime is BASE_RUNTIME
    began = stamp(); tick, cpu = time.perf_counter(), time.process_time()
    token = CallerDeadline(tick + seconds)  # Includes real factory/constructor overhead.
    decision = None; error = None; before = None
    try:
        def call():
            nonlocal before
            ct = time.perf_counter(); player = make_player(c, False)
            ctor = time.perf_counter() - ct
            before = provider_metrics(player)
            runtime_factory = search.SearchPathRuntime.__name__
            qt = time.perf_counter()
            d = player.choose_action(session, limits, cancel_token=token)
            return player, d, ctor, time.perf_counter() - qt, runtime_factory
        if on:
            with candidate_arm(True):
                player, decision, ctor, choose, runtime_factory = call()
        else:
            player, decision, ctor, choose, runtime_factory = call()
    except BaseException as exc:
        error = exc
    ended = stamp(); elapsed, cpu_elapsed = time.perf_counter() - tick, time.process_time() - cpu
    row = dict(slot, status='RAISED' if error else 'RETURNED', started_at=began,
               ended_at=ended, target_seconds=elapsed, target_cpu_seconds=cpu_elapsed,
               caller_deadline_observed=token.observed, limits=record_value(limits),
               full_root_record_sha256=full_digest(root),
               candidate_metrics=metrics() if on else {'runtime_count': 0, 'attempts': 0,
                   'successes': 0, 'fallbacks': 0, 'certification_seconds': 0.0},
               factory_restored=search.SearchPathRuntime is BASE_RUNTIME)
    if error:
        row.update(error_type=type(error).__name__, error=str(error))
    else:
        row.update(decision=record_value(decision), constructor_seconds=ctor,
                   outer_choose_seconds=choose, runtime_factory_seen=runtime_factory,
                   native_provider_present=before['present'],
                   provider_delta=metric_delta(before, provider_metrics(player)),
                   complete=decision.completed_depth == slot['depth'],
                   time_eligible=elapsed <= seconds)
    # Preserve exact actual return before assertions and replay.
    write_record(output / 'returns' / (slot['slot_id'] + '.json'), row)
    record_work(began, ended, 'research', str(output / 'returns' / (slot['slot_id'] + '.json')))
    if error:
        raise error
    assert row['factory_restored'] and session.to_record() == root
    assert decision.action in session.legal_actions() and decision.runtime_depth_balanced is True
    assert decision.pvs_null_window_searches == 0 and decision.pvs_researches == 0
    assert row['native_provider_present'] and decision.native_legality_fallbacks == 0
    assert decision.native_legality_operational_failures == 0
    if on:
        assert row['runtime_factory_seen'] == 'ChildRuntime'
        assert row['candidate_metrics']['runtime_count'] == 1
        assert row['candidate_metrics']['successes'] > 0
    else:
        assert row['runtime_factory_seen'] == 'SearchPathRuntime'
    return row


def run(inputs, plan_path, qualification, output):
    assert not output.exists(), 'closed or partial output is never refilled'
    plan = load(plan_path); q = load(qualification / 'qualification.json')
    binding = load(qualification / 'input-binding.json')
    assert q['status'] == 'PASSED' and q['selected_transitions'] == 2115
    assert binding['candidate_sha256'] == hashlib.sha256(Path('scripts/leaper_child_candidate.py').read_bytes()).hexdigest()
    assert hashlib.sha256(inputs.read_bytes()).hexdigest() == plan['input_sha256']
    for f, h in plan['sources'].items():
        assert hashlib.sha256(Path(f).read_bytes()).hexdigest() == h, f
    roots = {r['id']: r for r in load(inputs)['rows'] if r['prefix_length'] == 2}
    assert list(roots) == plan['root_ids'] and len(plan['slots']) == 144
    output.mkdir(parents=True); (output / 'returns').mkdir()
    write_record(output / 'execution-plan.json', plan)
    write_record(output / 'executed-source.json', {f: Path(f).read_bytes().decode('utf-8')
                                                 for f in plan['sources']})
    write_record(output / 'initial-process-cost.json', {
        'candidate_import_wall_seconds': CANDIDATE_IMPORT_WALL,
        'candidate_import_cpu_seconds': CANDIDATE_IMPORT_CPU,
        'derivation': {k: v for k, v in ChildRuntime._push_impl.research_derivation.items()
                       if k != 'original_code_filename'},
        'charge_rule': 'Charge once to candidate sum, allocate across depth strata by fixed planned slot counts.'})
    tick = time.perf_counter(); began = stamp(); slots = []; pairs = {}; halt = None
    for slot in plan['slots']:
        halt = halt or admission(plan, tick)
        if halt:
            slots.append(dict(slot, status='NOT_RUN', reason=halt))
        else:
            setup_start = time.perf_counter()
            try:
                c, s = make_session(roots[slot['case_id']])
                setup = time.perf_counter() - setup_start
                # Recheck after compilation/replay, before any Player dispatch.
                cause = admission(plan, tick)
                if cause:
                    halt = cause; slots.append(dict(slot, status='NOT_RUN', reason=halt))
                    continue
                row = slot_call(c, s, slot, output, plan['call_seconds'])
                slots.append(dict(slot, status='RETURNED', setup_seconds=setup,
                                  complete=row['complete'], time_eligible=row['time_eligible']))
                key = (slot['case_id'], slot['depth'], slot['repetition'])
                pairs.setdefault(key, []).append(row)
                if len(pairs[key]) == 2 and all(x['complete'] for x in pairs[key]):
                    a, b = pairs[key]
                    assert comparable_decision(a['decision']) == comparable_decision(b['decision']), 'complete work/decision mismatch'
                    assert comparable_native(a['provider_delta']) == comparable_native(b['provider_delta']), 'complete Native work mismatch'
            except Exception as exc:
                halt = 'execution_or_contract_failure'
                if not slots or slots[-1]['slot_id'] != slot['slot_id']:
                    slots.append(dict(slot, status='FAILED', error_type=type(exc).__name__, error=str(exc)))
                write_record(output / 'failure.json', {'slot': slot, 'error_type': type(exc).__name__,
                                                       'error': str(exc)})
        write_record(output / 'progress.json', {'started_at': began, 'slots': slots,
                                               'halt': halt, 'elapsed_seconds': time.perf_counter() - tick})
    result = {'started_at': began, 'ended_at': stamp(), 'slots': slots,
              'halt': halt, 'outer_seconds': time.perf_counter() - tick,
              'planned': 144, 'returned': sum(s['status'] == 'RETURNED' for s in slots),
              'new_games': 0, 'new_solver_calls': 0}
    write_record(output / 'batch.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--qualification', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    r = run(a.inputs, a.plan, a.qualification, a.output)
    print({k: r[k] for k in ('returned', 'planned', 'halt', 'outer_seconds')})
