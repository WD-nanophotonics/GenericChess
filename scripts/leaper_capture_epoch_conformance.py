"""Finite paired conformance after capture, never a production history reset.

All states are actual GameSession prefixes. The projection is a derived
observation; full history remains in every recorded Core state.
"""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from collections import Counter
import argparse,json,time
from scripts import leaper_design as L
from scripts.verify_leaper_delayed_capture import load,compile_scoped
from scripts.leaper_delayed_capture_witness import snapshot,replay,follow,action_map
from tools.local_agent.common import write_json


def inventory(node):return sum(p is not None for p in node['state']['position']['board'])


def observed_inventory(trace):
    result={}
    for node in trace:
        key=node['state']['history'][-1]['position_key'];n=inventory(node)
        if key in result:assert result[key]==n, 'observed identity/inventory conflict'
        result[key]=n
    return result


def projected(node,key_inventory):
    n=inventory(node);counts=node['state']['repetition_counts']
    assert all(k in key_inventory for k,_ in counts), 'unobserved prefix inventory key'
    return [(k,v)for k,v in counts if key_inventory[k]<=n]


def equivalent(pair,key_maps):
    a,b=pair
    assert a['state']['position']==b['state']['position']
    assert a['state']['ply_count']==b['state']['ply_count']
    assert a['result']==b['result'] and a['check']==b['check']
    assert a['legal_actions']==b['legal_actions']
    assert projected(a,key_maps[0])==projected(b,key_maps[1]), 'current-inventory repetition mismatch'


def measure(plan,history_plan,data,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter()
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['resources']['inclusive_hard_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original capture-epoch inclusive deadline')
    gate();base=load(data/'named-mu-registration.json.gz')['fixed_rules']['23']
    rr=replace(L.ruleset_from_dict(base),max_ply=10,repetition_limit=3)
    reg=dict(plan=plan,history_plan=history_plan,rule=L.ruleset_to_dict(rr,include_metadata=True),source_sha256=L.sha(Path(__file__)),deadline=deadline.isoformat())
    write_json(output/'registration.json',reg)
    c=L.compile_rule(rr);traces=[];calls=0
    for label in ('cycle','alternate'):
        z=L.GameSession(c,history_plan[label+'_setup_key']);trace=[snapshot(z)]
        for k in history_plan[label+'_actions']+[history_plan['winning_followup'][0]]:
            gate();z=follow(c,L.record_value(z.to_record()),k);calls+=1;trace.append(snapshot(z))
            write_json(output/('latest-prefix-'+label+'.json'),trace[-1])
        traces.append(trace)
    initial=[tr[-1]for tr in traces];maps=[observed_inventory(t)for t in traces]
    queue=[dict(pair=initial,key_maps=maps,parent=None,action=None,depth=0)]
    tape=[];cursor=0
    while cursor<len(queue):
        gate()
        if len(queue)>plan['resources']['maximum_pair_nodes']or calls>plan['resources']['Core_calls_cap']:
            write_json(output/'partial.json',dict(traces=traces,tape=tape,pending=len(queue)-cursor,calls=calls));raise RuntimeError('paired conformance cap, missing frontier UNKNOWN')
        q=queue[cursor];pair=q['pair'];equivalent(pair,q['key_maps'])
        children=[]
        z=replay(c,pair[0]['record']);keys=list(action_map(z))
        for k in keys:
            gate();new_pair=[];new_maps=[]
            for i,node in enumerate(pair):
                child=snapshot(follow(c,node['record'],k));calls+=1
                key=child['state']['history'][-1]['position_key'];d=dict(q['key_maps'][i]);n=inventory(child)
                assert n<=inventory(node), 'remove-only inventory must not increase'
                if key in d:assert d[key]==n
                d[key]=n;new_pair.append(child);new_maps.append(d)
            children.append(len(queue));queue.append(dict(pair=new_pair,key_maps=new_maps,parent=cursor,action=list(k),depth=q['depth']+1))
            write_json(output/'latest-pair.json',queue[-1])
        tape.append(dict(pair=pair,parent=q['parent'],action=q['action'],depth=q['depth'],children=children))
        cursor+=1
    gate();m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,traces=traces,tape=tape,new_Core_child_applications=calls,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return reg,m


def qualify(reg,m,data):
    base=L.ruleset_from_dict(load(data/'named-mu-registration.json.gz')['fixed_rules']['23'])
    compile_scoped(L.ruleset_to_dict(replace(base,initial_setup_options=())),3,23,5)
    rr=replace(base,max_ply=10,repetition_limit=3)
    assert reg['rule']==L.ruleset_to_dict(rr,include_metadata=True), 'complete capture-epoch scope mismatch'
    c=L.compile_rule(rr);hp=reg['history_plan'];traces=m['traces'];assert len(traces)==2
    cache={};occurrences=0
    def check(node):
        nonlocal occurrences
        occurrences+=1;k=json.dumps(node['record'],sort_keys=True)
        if k in cache:assert cache[k]==node
        else:assert snapshot(replay(c,node['record']))==node;cache[k]=node
    for label,trace in zip(('cycle','alternate'),traces):
        assert len(trace)==6 and trace[0]==snapshot(L.GameSession(c,hp[label+'_setup_key']))
        for n in trace:check(n)
        for i,k in enumerate(hp[label+'_actions']+[hp['winning_followup'][0]]):
            assert trace[i+1]==snapshot(follow(c,trace[i]['record'],k)), 'prefix action mismatch'
        assert all(n['result']['status']=='ongoing'for n in trace)
        assert [inventory(n)for n in trace]==[4,4,4,4,4,3]
    assert traces[0][-1]['state']['repetition_counts']!=traces[1][-1]['state']['repetition_counts']
    tape=m['tape'];assert tape and tape[0]['pair']==[traces[0][-1],traces[1][-1]]
    assert tape[0]['parent']is None and tape[0]['action']is None and tape[0]['depth']==0
    maps={0:[observed_inventory(t)for t in traces]};seen=set();edges=0;status=Counter()
    for index,row in enumerate(tape):
        assert index in maps, 'unreachable or reordered paired node'
        pair=row['pair'];key_maps=maps[index]
        for n in pair:check(n)
        equivalent(pair,key_maps)
        assert pair[0]['state']['ply_count']==5+row['depth']
        assert row['depth']<=5
        keys=list(action_map(replay(c,pair[0]['record'])))
        assert len(row['children'])==len(keys), 'complete paired frontier required'
        if not keys:
            assert pair[0]['result']['status']!='ongoing';status[pair[0]['result']['status']]+=1
        for key,child_index in zip(keys,row['children']):
            assert type(child_index)is int and index<child_index<len(tape) and child_index not in seen, 'unique forward edge required'
            seen.add(child_index);child=tape[child_index]
            assert child['parent']==index and child['action']==list(key)and child['depth']==row['depth']+1
            child_maps=[]
            for i,n in enumerate(pair):
                expected=snapshot(follow(c,n['record'],key));assert child['pair'][i]==expected, 'paired successor prefix mismatch'
                nn=inventory(expected);assert nn<=inventory(n)
                d=dict(key_maps[i]);identity=expected['state']['history'][-1]['position_key']
                if identity in d:assert d[identity]==nn
                d[identity]=nn;child_maps.append(d)
            maps[child_index]=child_maps;edges+=1
    assert seen==set(range(1,len(tape)))
    assert m['ended_at']<=reg['deadline']
    return dict(status='PASS',pair_nodes=len(tape),pair_edges=edges,complete_remaining_plies=5,terminal_pair_counts=dict(status),record_occurrences=occurrences,unique_full_records=len(cache),initial_full_history_tables_differ=True,projected_current_inventory_tables_equal=True,new_Core_child_applications=m['new_Core_child_applications'],new_Player_queries=0,new_graph_or_solver_calls=0,
        scope='Literal paired Core continuation conformance atH10/repeat3, no state injection/history reset, no outcome solver or TT change. All-history forgetting rests on the stated monotonic inventory and history-blind terminal argument, not this finite tree alone; remainingclock/currentinventory repetition are retained.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--history-plan',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        reg,m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),json.loads(a.history_plan.read_text(encoding='utf-8-sig')),a.data,a.output)
        q=qualify(reg,m,a.data);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:
        write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
