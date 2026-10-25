"""Explicit offline one-ply continuation at four measured qfrontiers.
Extra Core transitions/evaluations here are counterfactual data, NOT observer calls.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player
from generic_chess.ai.alphabeta.search import _bounded_static_score,terminal_score
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent import session


def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json')
    case=next(c for c in L.load(Path('.local_agent/assignment-e410/inputs.json'))['cases']if c['key']=='next-role-p49')
    c=L.compile_rule(L.ruleset_from_dict(case['rule']));p=player(c,'baseline')
    assert not(d/'rows.jsonl').exists();start=stamp();tick=time.perf_counter();count=0;evcount=0;status='FAILED'
    try:
        for leaf in data['leaves']:
            assert not session.stopped()and time.perf_counter()-tick<plan['caps']['batch_seconds']
            s=replay(c,leaf['record']);side=s.state.position.side_to_move;began=stamp();actual=_bounded_static_score(p._evaluator.evaluate(s.state));evcount+=1
            assert actual==leaf['leaf_event']['value']
            actions=sorted(s.legal_actions(),key=str);children=[];successors=[]
            for a in actions:
                assert not session.stopped();count+=1;assert count<=plan['caps']['children']
                child=replay(c,leaf['record']);child.submit(a);successors.append((a,child.state))
                if child.result.status.value=='ongoing':
                    value=_bounded_static_score(p._evaluator.evaluate(child.state));evcount+=1
                    if child.state.position.side_to_move!=side:value=-value
                    source='unchanged_DEFAULT_child_static'
                else:value=terminal_score(child.state.terminal_status,side,1);source='actual_Core_terminal'
                assert evcount<=plan['caps']['evaluations']
                children.append(dict(action=L.record_value(a),leaf_side_value=value,source=source,child_record=L.record_value(child.to_record()),Core_result=L.record_value(child.result)))
            noisy=set(classify_noisy(s.state,successors,c))
            for row,a in zip(children,actions):row['offline_noisy']=a in noisy
            best=max(row['leaf_side_value']for row in children);noisy_values=[row['leaf_side_value']for row in children if row['offline_noisy']]
            ended=stamp();append(d/'rows.jsonl',dict(leaf=leaf,started_at=began,ended_at=ended,side=side,standpat=actual,children=children,fulllegal_oneply_best=best,best_noisy_oneply=max(noisy_values)if noisy_values else None,standpat_minus_best=actual-best,all_legal_static_worse=best<actual,scope='Offline actualCore/alllegal one-ply static horizon only. Not trueWDLzugzwang, not actual tree logging or proof of a rootrepair.'))
            if ended>began:session.record_work(began,ended,'research',f'{d.as_posix()}/rows.jsonl actual offlinefulllegaloneply boundary at event{leaf["leaf_event"]["id"]}; explicitextraCore/Evalcost,notobserver')
            print('FRONTIER',leaf['leaf_event']['id'],leaf['iteration'],leaf['actor'],actual,best,'noisy',len(noisy),'/',len(actions),flush=True)
        status='CLOSED'
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),error=traceback.format_exc()));raise
    finally:write_json(d/'receipt.json',dict(status=status,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,Core_children=count,manual_evaluations=evcount,Player_choose_queries=0))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
