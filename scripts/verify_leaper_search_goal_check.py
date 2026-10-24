"""Bind explicit goal/default caller receipts to the original complete history."""
from pathlib import Path
import argparse, json, hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_ordering_diagnosis import load,rows
from tools.local_agent.common import write_json


def qualify(d,baseline_directory):
    reg=load(d/'plan.json');case=load(d/'case.json');rr=rows(d/'queries.jsonl');receipt=load(d/'receipt.json')
    assert receipt['status']=='CLOSED' and receipt['queries']==2
    assert [r['controller']for r in rr]==[x['controller']for x in reg['slots']]
    baseline=next(r for r in rows(baseline_directory/'ordering-queries.jsonl')if r['slot']=={'arm':'baseline','ply':50})
    assert hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest()==reg['reused_baseline_sha256']
    c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
    result=[];pv_count=0
    for r,slot in zip(rr,reg['slots']):
        dec=r['decision'];assert dec['action']is not None
        L.match_action(s,dec['action']);truth=next(ch['truth']['value']for ch in case['children']if ch['action']==dec['action'])
        assert truth==r['published_child_WDL']
        leaf=replay(c,case['record'])
        for a in dec['principal_variation']:leaf.submit(L.match_action(leaf,a));pv_count+=1
        assert L.record_value(leaf.result)==r['PV_final_result']
        assert dec['runtime_depth_balanced']and dec['runtime_pushes']==dec['runtime_pops']
        assert dec['nodes']+dec['qnodes']<=r['limits']['max_nodes']
        assert r['limits']['max_time_seconds']==slot['seconds']
        if slot['controller']=='unit_anywin':
            assert r['tuning']['stop_after_root_win']and r['tuning']['require_full_pv']
            assert r['limits']['quiescence_max_depth']==r['limits']['quiescence_hard_max_depth']==0
            assert r['actual_default_profile']is None and dec['qnodes']==0
            for a,b in zip(r['iterations'],baseline['iterations']):
                assert all(a[k]==b[k]for k in ('depth','nodes','qnodes','score','action'))
            assert truth==1 and dec['score']>=900000000
            assert leaf.result.winner==0 and leaf.result.status.value=='checkmate'
            assert dec['termination_reason']=='root_win_found'
            assert dec['result_source']in ('completed_root_win','main_iteration')
        else:
            assert not r['tuning']['stop_after_root_win']and not r['tuning']['require_full_pv']
            assert r['limits']['quiescence_max_depth']==4 and r['limits']['quiescence_hard_max_depth']==8
            assert r['actual_default_profile']is not None
        good=[x for x in r['iterations']if x['published_child_WDL']==case['root_truth']['value']]
        result.append(dict(controller=r['controller'],query_seconds=r['query_seconds'],outer_seconds=r['outer_seconds'],CPU_seconds=r['cpu_seconds'],completed_depth=dec['completed_depth'],requested_depth=14,result_source=dec['result_source'],termination_reason=dec['termination_reason'],nodes=dec['nodes'],qnodes=dec['qnodes'],score=dec['score'],chosen_WDL=truth,first_correct_iteration=good[0]if good else None,first_observed_correct_action_seconds=good[0]['elapsed']if good else r['query_seconds']if truth==case['root_truth']['value']else None,incorrect_completed_depths=[x['depth']for x in r['iterations']if x['published_child_WDL']!=case['root_truth']['value']],all_completed_actions_correct=len(good)==len(r['iterations']),exported_PV_terminal=leaf.result.status.value!='ongoing',PV_plies=r['PV_plies'],warning='Default qsearch may omit q suffix from exported PV. Graph-certified chosen-action WDL is separate from a complete literal mate explanation. Any-win stops at a completed winning child and does not claim completedD14/shortestmate.'))
    a=rr[0];b=baseline
    return dict(status='PASS',new_retained_queries=2,new_Player_queries_during_reader=0,new_solver_or_graph_calls=0,PV_actions=pv_count,summary=result,anywin_comparison=dict(baseline_seconds=b['outer_seconds'],anywin_seconds=a['outer_seconds'],baseline_work=b['decision']['nodes']+b['decision']['qnodes'],anywin_work=a['decision']['nodes']+a['decision']['qnodes'],same_pre_goal_completed_iteration_work=True,scope='One exposed fullhistory. Baseline also paid per-cutoff histogram recording overhead. Wall ratio descriptive, not replicated speedup or strength. The any-win caller intentionally changes stopping objective, never depth/evaluator/history equivalence.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--baseline-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=qualify(a.directory,a.baseline_directory);write_json(a.output,r);print(json.dumps({k:v for k,v in r.items()if k not in ('summary','anywin_comparison')}))
