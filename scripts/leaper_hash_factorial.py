"""Frozen paired whole-query costs for opt-in certified semantic hashing.

No timing wrappers, extra tree probes, outcome labels or automatic plan refill.
"""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import json
import time
import traceback

from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player, metrics, delta
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from tools.local_agent import session
from tools.local_agent.common import write_json


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(directory):
    d = Path(directory)
    plan = L.load(d / 'factorial-plan.json')
    assert sha(d / 'cost-inputs.json') == plan['inputs_sha256']
    for path, digest in plan['sources'].items():
        assert sha(path) == digest, path
    assert session.status()['id'] == plan['session_id']
    assert not (d / 'factorial-queries.jsonl').exists()
    assert not (d / 'factorial-receipt.json').exists()
    inputs = L.load(d / 'cost-inputs.json')
    cases = {c['key']: c for c in inputs['cases']}
    started = stamp()
    tick = time.perf_counter()
    count = 0
    status = 'FAILED'
    current = None
    pair = []

    class Cancel:
        last = 0.0
        flag = False
        def is_cancelled(self):
            now = time.perf_counter()
            if now - self.last >= .25:
                self.last = now
                self.flag = session.stopped() or now - tick >= plan['batch_seconds']
            return self.flag
    cancel = Cancel()
    try:
        for slot in plan['slots']:
            current = slot
            if cancel.is_cancelled():
                status = 'STOPPED_UNKNOWN'
                break
            case = cases[slot['case']]
            began = stamp()
            qt = time.perf_counter()
            cpu = time.process_time()
            c = L.compile_rule(L.ruleset_from_dict(case['rule']))
            s = replay(c, case['record'])
            import_seconds = time.perf_counter() - qt
            before = L.record_value(s.to_record())
            p = player(c, 'baseline')
            p._tuning = replace(p._tuning,
                use_plain_leaper_local_hash=slot['arm'] in ('local_hash', 'both'),
                use_cached_position_identity_hash=slot['arm'] in ('identity_cache', 'both'))
            setup_seconds = time.perf_counter() - qt
            met = metrics(p)
            limits = SearchLimits(**plan['limits'][slot['tier']])
            search_tick = time.perf_counter()
            decision = p.choose_action(s, limits, cancel_token=cancel)
            returned = stamp()
            query_seconds = time.perf_counter() - qt
            search_seconds = time.perf_counter() - search_tick
            cpu_seconds = time.process_time() - cpu
            row = dict(id=count, slot=slot, started_at=began, ended_at=returned,
                seconds=query_seconds, cpu_seconds=cpu_seconds,
                import_seconds=import_seconds, setup_seconds=setup_seconds,
                search_seconds=search_seconds, decision=L.record_value(decision),
                before_record=before, state_sha256=L.state_sha(s.state),
                limits=L.record_value(limits), profile=L.record_value(p.evaluation_profile),
                tuning=L.record_value(p._tuning), config=L.record_value(p._config),
                use_ordering=p._use_ordering, provider_present=met['provider'],
                provider_delta=delta(met, metrics(p)),
                admitted_pairs=len(_plain_leaper_hash_patterns(c) or ()),
                board_shape=[c.board_shape.width, c.board_shape.height])
            # Exact return saved BEFORE validation. Every frozen slot is single-use.
            append(d / 'factorial-queries.jsonl', row)
            count += 1
            if began < returned:
                session.record_work(began, returned, 'research',
                    f'{d.as_posix()}/factorial-queries.jsonl frozen whole-query slot{count}; '
                    'includes actual setup/search; full input and service evidence')
            else:
                append(d / 'factorial-ledger-skips.jsonl', dict(query_id=count-1,
                    started_at=began, ended_at=returned, perf_seconds=query_seconds,
                    reason='UTC clock yielded no positive interval; no effective-time credit'))
            assert before == L.record_value(s.to_record())
            assert decision.runtime_pushes == decision.runtime_pops
            if decision.choice_kind != 'TERMINAL':
                assert decision.runtime_depth_balanced
            pv = replay(c, before)
            for a in decision.principal_variation:
                assert a in pv.legal_actions()
                pv.submit(a)
            assert decision.choice_kind in ('DECLARATION', 'TERMINAL') or decision.action in s.legal_actions()
            if decision.choice_kind != 'TERMINAL':
                assert decision.runtime_position_identity_hash_cached == (slot['arm'] in ('identity_cache', 'both'))
            pair.append(row)
            if len(pair) == 2:
                matched = all(x['decision']['termination_reason'] not in ('time_limit', 'cancelled') for x in pair)
                names = ['action', 'score', 'principal_variation', 'nodes', 'qnodes',
                         'completed_depth', 'termination_reason', 'tt_hits', 'tt_cutoffs',
                         'runtime_pushes', 'runtime_pops']
                differences = [n for n in names if pair[0]['decision'][n] != pair[1]['decision'][n]]
                append(d / 'factorial-pairs.jsonl', dict(case=slot['case'], repeat=slot['repeat'],
                    matched_resource=matched, different_fields=differences,
                    provider_equal=pair[0]['provider_delta'] == pair[1]['provider_delta']))
                if matched:
                    assert not differences, differences
                    assert pair[0]['provider_delta'] == pair[1]['provider_delta']
                pair = []
            print('HASH-FACTORIAL', count, '/', len(plan['slots']), slot['case'],
                slot['arm'], decision.completed_depth, decision.termination_reason,
                round(query_seconds, 4), flush=True)
        else:
            status = 'CLOSED'
    except BaseException:
        write_json(d / 'factorial-failure.json', dict(at=stamp(), queries=count,
            slot=current, traceback=traceback.format_exc()))
        raise
    finally:
        write_json(d / 'factorial-receipt.json', dict(status=status, queries=count,
            started_at=started, ended_at=stamp(), seconds=time.perf_counter() - tick,
            plan_sha256=sha(d / 'factorial-plan.json'), missing='NOT_RUN/UNKNOWN, never refilled'))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    run(parser.parse_args().directory)
