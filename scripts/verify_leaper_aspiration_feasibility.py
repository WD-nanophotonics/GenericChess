"""Independent saved-record reader for existing aspiration50 feasibility."""
from pathlib import Path
from collections import defaultdict
import json, hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_certified_choice_timing import label
from generic_chess.ai.alphabeta.tuning import SearchTuning
from tools.local_agent.common import write_json


def verify(d, records=None):
    plan = L.load(d / 'plan.json')
    receipt = L.load(d / 'receipt.json')
    assert receipt['status'] == 'CLOSED'
    assert receipt['plan_sha256'] == hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()
    assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest() == plan['inputs_sha256']
    rows = records if records is not None else [json.loads(x) for x in (d/'queries.jsonl').read_text().splitlines()]
    cases = {c['key']: c for c in L.load(d/'inputs.json')['cases']}
    assert len(rows) == len(plan['slots']) == receipt['queries']
    pairs = defaultdict(dict)
    steps = 0
    for row, slot in zip(rows, plan['slots']):
        assert row['slot'] == slot
        expected = SearchTuning(use_pvs=True, use_aspiration=slot['arm']=='aspiration50', use_ordered_qsearch_in_check=False)
        assert row['tuning'] == L.record_value(expected)
        assert row['use_ordering']
        # Native flags request service only on compiled semantic rules. The
        # horizontal guard is explicitly a no-provider semantic compatibility row.
        if row['provider_present']:
            assert row['provider_delta']['availability'].get('calls',0) > 0
            assert row['provider_delta']['check'].get('calls',0) > 0
        else:
            assert slot['case'] == 'horizontal3-root137'
            assert row['provider_delta'] == {'availability': {}, 'check': {}}
            assert row['decision']['native_legality_calls'] == 0
        assert row['provider_delta']['availability'].get('declines',0) == 0
        case = cases[slot['case']]
        compiled = L.compile_rule(L.ruleset_from_dict(case['rule']))
        state = replay(compiled, case['record'])
        assert row['before_record'] == L.record_value(state.to_record())
        assert row['state_sha256'] == L.state_sha(state.state)
        decision = row['decision']
        assert decision['runtime_pushes'] == decision['runtime_pops']
        assert decision['runtime_depth_balanced']
        root_action = L.match_action(state, decision['action'])
        assert row['final_label'] == label(case, decision['action'])
        for action in decision['principal_variation']:
            state.submit(L.match_action(state, action))
            steps += 1
        for event in row['iterations']:
            assert event['source'] == 'completed_main_iteration'
            assert event['label'] == label(case, event['action'])
            assert event['seconds'] <= row['seconds']
            state = replay(compiled, case['record'])
            for action in event['pv']:
                state.submit(L.match_action(state, action))
                steps += 1
        if slot.get('cancel'):
            assert decision['termination_reason'] == 'cancelled'
        else:
            if decision['result_source'] == 'root_immediate_win':
                assert decision['completed_depth'] == 0 and not row['iterations']
            else:
                assert decision['completed_depth'] == slot['depth']
                assert decision['termination_reason'] == 'completed_depth'
                assert row['iterations'][-1]['score'] == decision['score']
                assert row['iterations'][-1]['action'] == decision['action']
            pairs[(slot['case'],slot['depth'])][slot['arm']] = row
    comparisons = []
    for (key, depth), arms in pairs.items():
        a, b = [arms[x] for x in ('baseline','aspiration50')]
        assert a['profile'] == b['profile']
        assert a['decision']['score'] == b['decision']['score']
        comparisons.append(dict(case=key, depth=depth,
            same_action=a['decision']['action']==b['decision']['action'],
            baseline_seconds=a['seconds'], candidate_seconds=b['seconds'],
            baseline_events=a['decision']['nodes']+a['decision']['qnodes'],
            candidate_events=b['decision']['nodes']+b['decision']['qnodes'],
            candidate_researches=b['decision']['aspiration_researches'],
            candidate_label=b['final_label']))
    return dict(passed=True, queries=len(rows), legal_pv_steps=steps,
                pairs=comparisons, limitations=[
                'Actual Nativeboth DEFAULT/PVS Q4hard8 only; not all-domain equivalence.',
                'Tied actions and cached partial PVs allowed; no independent solving.',
                'Small single timing samples under concurrent load; wall differences not demonstrated causal savings.',
                'Root immediate win returns before aspiration; not a window-cost positive.'])


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--directory',type=Path,required=True)
    d = p.parse_args().directory
    result = verify(d)
    write_json(d/'assessment.json',result)
    print(json.dumps(result))
