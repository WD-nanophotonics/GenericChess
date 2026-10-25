"""Frozen unchanged-controller root paid-cost diagnostic, no policy."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time, traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_iteration_choice_observer import IterationChoiceObserver
from scripts.leaper_certified_choice_timing import label
from scripts.leaper_ordinary_qorder_study import metrics, delta
from scripts.pure_leaper_search_study import append
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session
from scripts.leaper_root_cost_observer import RootCostObserver


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tuning(arm):
    assert arm in ('baseline', 'aspiration50')
    return SearchTuning(use_pvs=True, use_aspiration=arm == 'aspiration50',
                        use_ordered_qsearch_in_check=False)


def run(directory):
    d = Path(directory)
    plan = L.load(d / 'plan.json')
    assert session.status()['id'] == plan['session_id']
    assert sha(d / 'inputs.json') == plan['inputs_sha256']
    for p, expected in plan['sources'].items():
        assert sha(p) == expected, p
    assert not (d / 'receipt.json').exists()
    assert not (d / 'queries.jsonl').exists()
    data = L.load(d / 'inputs.json')
    cases = {c['key']: c for c in data['cases']}
    started = stamp()
    clock = time.perf_counter()
    count = 0
    status = 'FAILED'

    class Cancel:
        last = 0.0
        flag = False
        def is_cancelled(self):
            now = time.perf_counter()
            if now - self.last >= .25:
                self.last = now
                self.flag = session.stopped() or now - clock >= plan['batch_seconds']
            return self.flag

    cancel = Cancel()
    try:
        for slot in plan['slots']:
            assert not cancel.is_cancelled(), 'role/batch stop'
            if count == 4:
                saved=[json.loads(x) for x in (d/'queries.jsonl').read_text().splitlines()]
                fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','runtime_pushes','runtime_pops']
                for a,b in zip(saved[::2],saved[1::2]):
                    assert all(a['decision'][k]==b['decision'][k] for k in fields)
                    assert a['provider_delta']==b['provider_delta']
                    assert a['decision']['completed_depth']==4
                write_json(d/'qualification-assessment.json',dict(passed=True,pairs=2,fields=fields))
            case = cases[slot['case']]
            compiled = L.compile_rule(L.ruleset_from_dict(case['rule']))
            state = replay(compiled, case['record'])
            before = L.record_value(state.to_record())
            began = stamp()
            tick = time.perf_counter()
            player = AlphaBetaPlayer(compiled, use_disk_cache=False,
                use_ordering=True, tuning=tuning('baseline'),
                use_native_semantic_availability=True, use_native_semantic_check=True)
            setup = time.perf_counter() - tick
            service_before = metrics(player)
            observer = IterationChoiceObserver(tick)
            limits = SearchLimits(max_depth=slot['depth'], max_nodes=200000,
                                  max_time_seconds=30)
            token = cancel
            if slot.get('cancel'):
                class PollCancel:
                    calls = 0
                    def is_cancelled(self):
                        self.calls += 1
                        return self.calls >= 100 or cancel.is_cancelled()
                token = PollCancel()
            root_observer = RootCostObserver(tick) if slot['observed'] else None
            if root_observer:
                root_observer.__enter__()
            try:
                decision = player.choose_action(state, limits, cancel_token=token,
                                                progress_callback=observer)
            finally:
                if root_observer:
                    root_observer.__exit__(None,None,None)
            ended = stamp()
            row = dict(slot=slot, started_at=began, ended_at=ended,
                seconds=time.perf_counter()-tick, setup_seconds=setup,
                before_record=before, state_sha256=L.state_sha(state.state),
                limits=L.record_value(limits), decision=L.record_value(decision),
                profile=L.record_value(player.evaluation_profile),
                tuning=L.record_value(player._tuning), use_ordering=player._use_ordering,
                provider_present=service_before['provider'],
                provider_delta=delta(service_before, metrics(player)),
                iterations=observer.events,
                final_label=label(case, L.record_value(decision.action)),
                root_observer=root_observer.result() if root_observer else None)
            for event in row['iterations']:
                event['label'] = label(case, event['action'])
            append(d / 'queries.jsonl', row)
            count += 1
            if ended > began:
                session.record_work(began, ended, 'research',
                    f'{d.as_posix()}/queries.jsonl unchanged-controller root-cost query {count}; literal root child windows/time/counters')
            assert before == L.record_value(state.to_record())
            assert decision.runtime_pushes == decision.runtime_pops
            pvstate = replay(compiled, before)
            for action in decision.principal_variation:
                assert action in pvstate.legal_actions()
                pvstate.submit(action)
            assert decision.action in state.legal_actions()
            print('ROOT-COST', count, slot, decision.completed_depth,
                  decision.score, round(row['seconds'], 4),
                  decision.aspiration_researches, row['final_label'], flush=True)
        status = 'CLOSED'
    except BaseException:
        write_json(d / 'failure.json', dict(at=stamp(), queries=count,
                   error=traceback.format_exc(),root_observer=root_observer.result() if 'root_observer' in locals() and root_observer else None))
        raise
    finally:
        write_json(d / 'receipt.json', dict(status=status, queries=count,
            started_at=started, ended_at=stamp(), seconds=time.perf_counter()-clock,
            plan_sha256=sha(d / 'plan.json')))


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    run(p.parse_args().directory)
