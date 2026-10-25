"""Independent derived readers for leaf-factorial, frontier and causal controls.
No new Player search or evaluator calls; Core binding/classification is explicit.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_certified_choice_timing import label
from scripts.leaper_ordinary_qorder_study import tuning
from generic_chess.ai.alphabeta.search import _bounded_static_score,terminal_score
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from tools.local_agent.common import write_json


def readrows(p):return [json.loads(x)for x in Path(p).read_text().splitlines()]


def factorial(d):
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');receipt=L.load(d/'receipt.json');rows=readrows(d/'rows.jsonl');cases={c['key']:c for c in data['cases']}
    assert receipt['status']=='CLOSED'and len(rows)==len(cases)==19
    assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
    total=0;manual=0;terminal_mismatches=[];summary=defaultdict(Counter)
    for row in rows:
        case=cases[row['case']];assert row['root_record']==case['record']
        c=L.compile_rule(L.ruleset_from_dict(case['rule']));root=replay(c,case['record']);actor=root.state.position.side_to_move
        assert row['root_actor']==actor
        labels={json.dumps(x['action'],sort_keys=True):x['own_WDL']for x in case['action_labels']}
        actual={L.match_action(root,x['action'])for x in row['records']};assert actual==set(root.legal_actions())
        assert [x['action_text']for x in row['records']]==sorted(str(a)for a in actual)
        for r in row['records']:
            a=L.match_action(root,r['action']);s=replay(c,case['record']);s.submit(a);total+=1
            assert r['child_record']==L.record_value(s.to_record())and r['Core_result']==L.record_value(s.result)
            assert r['source_own_WDL']==labels[json.dumps(r['action'],sort_keys=True)]
            if s.result.status.value=='ongoing':
                assert not r['terminal']and set(r['raw_evaluate'])==set(plan['variants'])
                for name,v in r['raw_evaluate'].items():
                    expected=_bounded_static_score(v)*(1 if s.state.position.side_to_move==actor else -1)
                    assert r['values'][name]==expected;manual+=1
            else:
                assert r['terminal']and not r['raw_evaluate']
                value=terminal_score(s.state.terminal_status,actor,1)
                assert all(v==value for v in r['values'].values())
                truth=0 if s.result.winner is None else 1 if s.result.winner==actor else -1
                if truth!=r['source_own_WDL']:terminal_mismatches.append((case['key'],r['action']))
        for variant in plan['variants']:
            cfg=row['actual_configs'][variant];base=row['actual_configs']['actual_DEFAULT']
            for k,v in cfg.items():
                expected=0 if k=='dynamic_mobility_weight'and variant in ['mobility_zero','both_zero']or k=='anchor_escape_weight'and variant in ['anchor_zero','both_zero']else base[k]
                assert v==expected
            best=max(r['values'][variant]for r in row['records']);ties=[r for r in row['records']if r['values'][variant]==best]
            s=row['summary'][variant]
            assert s['score']==best and s['maximizers']==len(ties)
            assert s['canonical_action']==ties[0]['action']and s['canonical_chosen_WDL']==ties[0]['source_own_WDL']
            assert s['maximizer_WDLs']==sorted({r['source_own_WDL']for r in ties})
            goal=case['root_own_WDL'];assert s['all_ties_source_optimal']==all(r['source_own_WDL']==goal for r in ties)
            assert s['some_tie_source_optimal']==any(r['source_own_WDL']==goal for r in ties)
            q=summary[row['source_group']+':'+variant];q['roots']+=1;q['canonical_correct']+=s['canonical_chosen_WDL']==goal;q['all_ties_optimal']+=s['all_ties_source_optimal']
            bv=row['summary']['actual_DEFAULT']['canonical_chosen_WDL'];q['repairs']+=s['canonical_chosen_WDL']>bv;q['regressions']+=s['canonical_chosen_WDL']<bv
    assert total==receipt['Core_children']==153 and manual==receipt['manual_evaluations']==584
    assert terminal_mismatches==receipt['terminal_source_mismatches']==[]
    return dict(passed=True,roots=19,Core_children=total,producer_manual_evaluations=manual,reader_manual_evaluations=0,source_terminal_mismatches=0,by_group=dict(summary),scope='One-ply frozen-feature ranking only; no Playerdecision/quality/holdout claim. Anchorzero positive2/0posthoc source signal is not an executed search repair.')


def frontier(d):
    data=L.load(d/'inputs.json');rows=readrows(d/'rows.jsonl');receipt=L.load(d/'receipt.json');assert receipt['status']=='CLOSED'and len(rows)==4
    source=L.load(Path('.local_agent/assignment-e410/inputs.json'));case=next(c for c in source['cases']if c['key']=='next-role-p49');c=L.compile_rule(L.ruleset_from_dict(case['rule']));checked=0;results=[]
    for row,leaf in zip(rows,data['leaves']):
        assert row['leaf']==leaf
        root=replay(c,leaf['record']);side=root.state.position.side_to_move;assert row['side']==side and row['standpat']==leaf['leaf_event']['value']
        actual={L.match_action(root,r['action'])for r in row['children']};assert actual==set(root.legal_actions())
        pairs=[]
        for r in row['children']:
            a=L.match_action(root,r['action']);child=replay(c,leaf['record']);child.submit(a);checked+=1
            assert r['child_record']==L.record_value(child.to_record())and r['Core_result']==L.record_value(child.result)
            pairs.append((a,child.state))
        noisy=set(classify_noisy(root.state,pairs,c))
        assert all(r['offline_noisy']==(L.match_action(root,r['action'])in noisy)for r in row['children'])
        best=max(r['leaf_side_value']for r in row['children']);assert best==row['fulllegal_oneply_best']and row['standpat_minus_best']==row['standpat']-best
        results.append(dict(event=leaf['leaf_event']['id'],standpat=row['standpat'],best=best,legal=len(actual),offline_noisy=len(noisy),all_legal_static_worse=best<row['standpat']))
    first=next(r for r in rows if r['leaf']['leaf_event']['id']==1990);later=next(r for r in rows if r['leaf']['leaf_event']['id']==12217)
    assert len(first['children'])==1 and first['children'][0]['child_record']==later['leaf']['record']
    assert first['children'][0]['leaf_side_value']==-later['standpat']
    assert checked==receipt['Core_children']==34
    return dict(passed=True,rows=results,Core_children_replayed=checked,new_offline_classifications=checked,reader_manual_evaluations=0,source_record_link='D3Bsolequietchild fullGameRecord equals D4Bscoutleaf fullGameRecord, exacthistory not scorematching.',scope='Staticoneply frontier slack, not trueWDLzugzwang or rootrepair. Actualobserver never generated thoseD4scoutactions.')


def controls(tt,surgery):
    case=L.load(surgery/'inputs.json')['case'];c=L.compile_rule(L.ruleset_from_dict(case['rule']));rows=readrows(tt/'queries.jsonl');assert L.load(tt/'receipt.json')['status']=='CLOSED'and len(rows)==2
    pvsteps=0;observed=[]
    for r in rows:
        assert r['before_record']==case['record']and r['tuning']==L.record_value(tuning('baseline'))
        assert r['decision']['completed_depth']==r['depth']and r['decision']['termination_reason']=='completed_depth'
        assert r['diagnostic']['masked_hits']>0 and r['diagnostic']['returned_proxy_depth']==-1
        assert r['decision']['runtime_pushes']==r['decision']['runtime_pops']
        assert r['final_label']==label(case,r['decision']['action'])
        s=replay(c,case['record'])
        for a in r['decision']['principal_variation']:s.submit(L.match_action(s,a));pvsteps+=1
        observed.append(dict(depth=r['depth'],score=r['decision']['score'],label=r['final_label'],masked_hits=r['diagnostic']['masked_hits']))
    target=L.load(surgery/'inputs.json');r=L.load(surgery/'result.json');assert L.load(surgery/'receipt.json')['status']=='CLOSED'
    assert r['before_record']==case['record']and r['tuning']==L.record_value(tuning('baseline'))
    assert r['decision']['completed_depth']==3 and r['decision']['termination_reason']=='completed_depth'
    assert r['decision']['runtime_pushes']==r['decision']['runtime_pops']
    assert len(r['interventions'])==1
    e=r['interventions'][0];assert e['path']==target['target_path']and e['actor']==target['expected_actor']and e['absolute_ply']==target['expected_absolute_ply']
    assert e['entry_alpha']==target['entry_alpha']and e['entry_beta']==target['entry_beta']
    assert e['original_return']==target['old_value']and e['replacement']==target['replacement']
    s=replay(c,case['record'])
    for a in e['path']:s.submit(L.match_action(s,a))
    assert L.record_value(s.to_record())==target['target_leaf_record']
    assert len(s.legal_actions())==1
    a=next(iter(s.legal_actions()));s.submit(a);assert L.record_value(s.to_record())==target['offline_child']['child_record']
    assert target['replacement']==target['offline_child']['leaf_side_value']
    s=replay(c,case['record'])
    for a in r['decision']['principal_variation']:s.submit(L.match_action(s,a));pvsteps+=1
    assert r['final_label']==label(case,r['decision']['action'])
    return dict(passed=True,TT_score_suppression=observed,event_replacement=dict(score=r['decision']['score'],label=r['final_label'],interventions=1),legal_pv_steps=pvsteps,new_search_queries=0,reader_manual_evaluations=0,scope='TTscore reuse notnecessaryfor thisflip. One history-specificevent intervention makes observedD3sourcequality worse; notgeneralcoverage/singleton/feature-policy effect or deployedoptimization.')


if __name__=='__main__':
    root=Path('.local_agent');a=factorial(root/'leaf-factorial-e410');b=frontier(root/'frontier-oneply-e410');c=controls(root/'tt-counterfactual-e410',root/'frontier-surgery-e410')
    for path,data in [('leaf-factorial-e410',a),('frontier-oneply-e410',b),('tt-counterfactual-e410',c)]:write_json(root/path/'assessment.json',data)
    print(json.dumps(dict(factorial=a,frontier=b,controls=c)))
