"""Read literal saved root-call cost records; no new search/solver."""
from pathlib import Path
import json
from collections import defaultdict
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_certified_choice_timing import label
from tools.local_agent.common import write_json


def verify(d):
    plan=L.load(d/'plan.json');rows=[json.loads(x)for x in(d/'queries.jsonl').read_text().splitlines()]
    assert L.load(d/'receipt.json')['status']=='CLOSED'
    assert len(rows)==len(plan['slots'])==8
    cases={c['key']:c for c in L.load(d/'inputs.json')['cases']}
    fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','runtime_pushes','runtime_pops']
    for a,b in [rows[:2],rows[2:4],rows[6:8]]:
        assert all(a['decision'][k]==b['decision'][k]for k in fields)
        assert a['provider_delta']==b['provider_delta']
    out=[];steps=0
    for row,slot in zip(rows,plan['slots']):
        assert row['slot']==slot
        case=cases[slot['case']];compiled=L.compile_rule(L.ruleset_from_dict(case['rule']))
        assert row['before_record']==case['record']
        assert row['decision']['runtime_pushes']==row['decision']['runtime_pops']
        obs=row['root_observer']
        if obs is None:continue
        assert obs['dropped']==0 and obs['root_child_calls']==len(obs['events'])
        last=-1.;iterations=defaultdict(list)
        for n,e in enumerate(obs['events'],1):
            assert e['call_id']==n
            assert e['start_seconds']>=last and e['end_seconds']>=e['start_seconds']
            last=e['end_seconds']
            assert e['end_seconds']<=row['seconds']
            state=replay(compiled,case['record']);action=L.match_action(state,e['action']);state.submit(action);steps+=1
            if e['completed']:
                assert e['raw_return']==-e['root_negated_return']
                a,b=e['child_entry_alpha'],e['child_entry_beta'];v=e['raw_return']
                tag='UPPER'if v<=a else'LOWER'if v>=b else'INTERIOR'
                assert tag==e['original_window_label']
                for item in e['child_pv']:
                    state.submit(L.match_action(state,item));steps+=1
            else:assert e['raw_return']is None and e['exception_type']
            iterations[e['iteration']].append(e)
        if slot['depth']==6:
            selected=[]
            for e in iterations[6]:
                lab=label(case,e['action'])
                selected.append(dict(call_id=e['call_id'],index=e['move_index'],
                    action=e['action'],source_own_WDL=lab['own_WDL'],
                    start_seconds=e['start_seconds'],end_seconds=e['end_seconds'],
                    root_score=e['root_negated_return'],root_alpha=e['root_alpha_before'],
                    root_window_numerical_bound={'LOWER':'UPPER','UPPER':'LOWER','INTERIOR':'INTERIOR'}[e['original_window_label']],
                    paid_events=e['end_nodes']+e['end_qnodes']-e['start_nodes']-e['start_qnodes']))
            supported=[e for e in selected if e['source_own_WDL']==1]
            promoting=[e for e in supported if e['root_score']>e['root_alpha']and e['root_window_numerical_bound']=='INTERIOR']
            out.append(dict(case=slot['case'],caller_seconds=row['seconds'],
                root_calls=len(obs['events']),D6calls=selected,
                earliest_known_win_action_return_seconds=min(e['end_seconds']for e in supported),
                earliest_known_win_interior_promotion_candidate_seconds=min(e['end_seconds']for e in promoting),
                first_D6_call_end_seconds=selected[0]['end_seconds']))
    return dict(passed=True,queries=8,pv_steps=steps,pairs=3,observations=out,
        limitations=['No new all-defense proof. WDL comes from existing exposed source graph.',
        'Entry-window bounds are numerical, not an independently certified fixed-horizon/TT proof.',
        'Promoting candidate inferred from pre-return window; no full Q/TT dependency chain.',
        'Observer perturbs wall time. No counterfactual move-order savings or first-correct stop inferred.'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);d=p.parse_args().directory
    r=verify(d);write_json(d/'assessment.json',r)
    print(json.dumps({k:v for k,v in r.items()if k!='observations'}))
    for o in r['observations']:
        print(o['case'],{k:v for k,v in o.items()if k!='D6calls'})
