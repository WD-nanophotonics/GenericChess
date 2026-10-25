"""Bounded actual-path timing observation; wrappers never change returned values."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import time
import traceback

from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player, metrics, delta
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core import search_runtime
from tools.local_agent import session
from tools.local_agent.common import write_json


def stamp():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def observation():
    totals = {}
    positions = []
    originals = []

    def install(owner, name, label, capture=False):
        original = getattr(owner, name)
        originals.append((owner, name, original))
        totals[label] = dict(calls=0, nanoseconds=0, raised=0)

        @wraps(original)
        def wrapped(*args, **kwargs):
            if capture and len(positions) < 128:
                # Keep immutable Position, never RuntimeSearchState or its owner.
                positions.append(args[1].position)
            began = time.perf_counter_ns()
            try:
                return original(*args, **kwargs)
            except BaseException:
                totals[label]['raised'] += 1
                raise
            finally:
                elapsed = time.perf_counter_ns() - began
                totals[label]['calls'] += 1
                totals[label]['nanoseconds'] += elapsed
        setattr(owner, name, wrapped)

    install(search_runtime, '_semantic_component_diff_hash', 'semantic_diff_hash')
    install(Evaluator, 'evaluate', 'evaluate', capture=True)
    install(NativeSemanticLegalityProvider, '_state_only_payload', 'native_payload')
    try:
        yield totals, positions
    finally:
        for owner, name, original in reversed(originals):
            setattr(owner, name, original)


def run(directory):
    d = Path(directory)
    plan = L.load(d / 'profile-plan.json')
    data = L.load(d / 'profile-inputs.json')
    assert session.status()['id'] == plan['session_id']
    assert not (d / 'profile-queries.jsonl').exists()
    start = stamp()
    tick = time.perf_counter()
    count = 0
    status = 'FAILED'

    class Cancel:
        last = 0.0
        flag = False
        def is_cancelled(self):
            now = time.perf_counter()
            if now - self.last >= .25:
                self.last = now
                self.flag = session.stopped() or now - tick >= plan['limits']['batch_seconds']
            return self.flag

    cancel = Cancel()
    try:
        for index, case in enumerate(data['cases']):
            rows = []
            arms = plan['variants'] if index % 2 == 0 else list(reversed(plan['variants']))
            for arm in arms:
                if cancel.is_cancelled():
                    status = 'STOPPED_UNKNOWN'
                    return
                began = stamp()
                qt = time.perf_counter()
                cpu = time.process_time()
                c = L.compile_rule(L.ruleset_from_dict(case['rule']))
                s = replay(c, case['record'])
                p = player(c, 'baseline')
                before = L.record_value(s.to_record())
                met = metrics(p)
                limits = SearchLimits(**{k: plan['limits'][k] for k in
                    ['max_depth', 'max_nodes', 'max_time_seconds']})
                setup = time.perf_counter() - qt
                totals, positions = {}, []
                if arm == 'timed_wrappers':
                    with observation() as (totals, positions):
                        decision = p.choose_action(s, limits, cancel_token=cancel)
                else:
                    decision = p.choose_action(s, limits, cancel_token=cancel)
                ended = stamp()
                row = dict(case=case['key'], arm=arm, started_at=began, ended_at=ended,
                    seconds=time.perf_counter() - qt, cpu_seconds=time.process_time() - cpu,
                    setup_seconds=setup, before_record=before,
                    decision=L.record_value(decision), limits=L.record_value(limits),
                    actual_profile=L.record_value(p.evaluation_profile),
                    actual_config=L.record_value(p._config), tuning=L.record_value(p._tuning),
                    provider_present=met['provider'], provider_delta=delta(met, metrics(p)),
                    timed_paths=totals, actual_leaf_positions=L.record_value(positions))
                append(d / 'profile-queries.jsonl', row)
                count += 1
                rows.append(row)
                if ended > began:
                    session.record_work(began, ended, 'research',
                        f'{d.as_posix()}/profile-queries.jsonl new actual-path query{count}; '
                        'observer timing perturbation retained, actual leaf positions only')
                assert L.record_value(s.to_record()) == before
                assert decision.runtime_pushes == decision.runtime_pops
                for action in decision.principal_variation:
                    assert action in s.legal_actions()
                    s.submit(action)
                print('KERNEL-PROFILE', count, case['key'], arm,
                    decision.completed_depth, round(row['seconds'], 4), flush=True)
            keys = ['action', 'score', 'principal_variation', 'nodes', 'qnodes',
                    'completed_depth', 'termination_reason', 'tt_hits', 'tt_cutoffs']
            complete = all(r['decision']['termination_reason'] == 'completed_depth' for r in rows)
            differing = [k for k in keys if rows[0]['decision'].get(k) != rows[1]['decision'].get(k)]
            append(d / 'profile-pairs.jsonl', dict(case=case['key'], complete=complete,
                differing_fields=differing, scope='Timing includes perturbation; no production-fraction claim'))
            if complete:
                assert not differing, differing
        status = 'CLOSED'
    except BaseException:
        write_json(d / 'profile-failure.json', dict(at=stamp(), queries=count,
            traceback=traceback.format_exc()))
        raise
    finally:
        write_json(d / 'profile-receipt.json', dict(status=status, started_at=start,
            ended_at=stamp(), seconds=time.perf_counter() - tick, queries=count,
            input_sha256=hashlib.sha256((d / 'profile-inputs.json').read_bytes()).hexdigest(),
            missing='Unreturned slots remain NOT_RUN/UNKNOWN; no refill'))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    run(parser.parse_args().directory)
