"""A fixed two-prefix history-value witness, not a TT benchmark or solver."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import argparse,json,time
from scripts import leaper_design as L
from scripts.verify_leaper_delayed_capture import load,compile_scoped
from scripts.leaper_delayed_capture_witness import snapshot,replay,follow,action_map,nodes
from tools.local_agent.common import write_json


def measure(plan,data,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter()
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['cost']['new_inclusive_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original inclusive history deadline')
    gate();base=load(data/'named-mu-registration.json.gz')['fixed_rules']['23']
    rule=replace(L.ruleset_from_dict(base),max_ply=8)
    reg=dict(plan=plan,complete_rule=L.ruleset_to_dict(rule,include_metadata=True),source_sha256=L.sha(Path(__file__)),deadline=deadline.isoformat())
    write_json(output/'registration.json',reg)
    c=L.compile_rule(rule);rows=[]
    for label in ('cycle','alternate'):
        gate();z=L.GameSession(c,plan[label+'_setup_key']);trace=[snapshot(z)]
        for k in plan[label+'_actions']:
            gate();z=follow(c,L.record_value(z.to_record()),k);trace.append(snapshot(z))
            write_json(output/('latest-'+label+'.json'),trace[-1])
        rows.append(dict(label=label,setup_key=plan[label+'_setup_key'],trace=trace))
    target=rows[1]['trace'][-1];capture=follow(c,target['record'],plan['winning_followup'][0]);after=snapshot(capture)
    write_json(output/'capture.json',after);defenses=[]
    for k in action_map(capture):
        gate();z=follow(c,after['record'],k);node=snapshot(z)
        write_json(output/'latest-defense.json',node)
        mate=follow(c,node['record'],plan['winning_followup'][2]);finish=snapshot(mate)
        defenses.append(dict(action_key=list(k),node=node,finish=finish));write_json(output/'latest-defense-complete.json',defenses[-1])
    gate();m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,rows=rows,capture=after,all_defenses=defenses,new_Core_child_applications=8+1+2*len(defenses),new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return reg,m


def qualify(reg,m,data):
    plan=reg['plan'];base=L.ruleset_from_dict(load(data/'named-mu-registration.json.gz')['fixed_rules']['23'])
    compile_scoped(L.ruleset_to_dict(replace(base,initial_setup_options=())),3,23,5)
    expected=replace(base,max_ply=8)
    assert reg['complete_rule']==L.ruleset_to_dict(expected,include_metadata=True), 'complete H8 rule mismatch'
    assert plan['H']==8 and plan['repetition_limit']==2
    assert plan['cycle_actions']==[['A',0,2,None],['B',3,5,None],['A',2,0,None],['B',5,3,None]]
    assert plan['alternate_actions']==[['A',0,2,None],['B',8,5,None],['A',2,0,None],['B',5,3,None]]
    c=L.compile_rule(expected);cache={};count=0
    for node in nodes(m):
        count+=1;key=json.dumps(node['record'],sort_keys=True)
        if key in cache:assert cache[key]==node
        else:assert snapshot(replay(c,node['record']))==node;cache[key]=node
    assert [r['label']for r in m['rows']]==['cycle','alternate']
    for row in m['rows']:
        label=row['label'];trace=row['trace'];assert len(trace)==5
        assert trace[0]==snapshot(L.GameSession(c,plan[label+'_setup_key']))
        for i,k in enumerate(plan[label+'_actions']):
            assert trace[i+1]==snapshot(follow(c,trace[i]['record'],k)), 'actual history prefix mismatch'
    a,b=[r['trace'][-1]for r in m['rows']]
    assert a['state']['position']==b['state']['position'], 'Position mismatch'
    assert a['state']['ply_count']==b['state']['ply_count']==4
    assert a['record']['ruleset_fingerprint']==b['record']['ruleset_fingerprint']
    assert a['state']['repetition_counts']!=b['state']['repetition_counts']
    assert a['result']['status']=='repetition' and a['result']['winner']is None
    assert b['result']['status']=='ongoing'
    assert m['capture']==snapshot(follow(c,b['record'],plan['winning_followup'][0]))
    assert not any(p and p['current_type_id']=='B'for p in m['capture']['state']['position']['board'])
    replies=list(action_map(replay(c,m['capture']['record'])))
    assert replies==[('K',7,8,None)], 'fixed response premise failed'
    assert len(m['all_defenses'])==len(replies)and {tuple(r['action_key'])for r in m['all_defenses']}==set(replies), 'complete defense coverage required'
    for d in m['all_defenses']:
        assert d['node']==snapshot(follow(c,m['capture']['record'],d['action_key']))
        assert d['node']['result']['status']=='ongoing'
        assert d['finish']==snapshot(follow(c,d['node']['record'],plan['winning_followup'][2]))
        assert d['finish']['result']['status']=='checkmate'and d['finish']['result']['winner']==0
        assert d['finish']['state']['ply_count']==7
    assert m['ended_at']<=reg['deadline']
    return dict(status='PASS',same_complete_rule=True,same_Position=True,same_ply=4,H=8,remaining_plies=4,White_WDL=[0,1],terminal_status=['repetition','ongoing'],mate_ply=7,record_occurrences=count,unique_full_records=len(cache),new_Core_child_applications=m['new_Core_child_applications'],new_Player_queries=0,new_graph_or_solver_calls=0,
        scope='Two literal histories in the same H8 fixednamedRuleSet and rootmu. Positive history-value witness, not two ongoing contexts, independent WDL engine, TT error or cache-performance benchmark. Current external repetition checks can recognize the terminal contrast.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        reg,m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.data,a.output);q=qualify(reg,m,a.data)
        write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:
        write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
