"""One actual key-identity observation, not a TT performance experiment."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import argparse,json,time
from scripts import leaper_design as L
from scripts.verify_leaper_delayed_capture import load,compile_scoped
from scripts.leaper_delayed_capture_witness import snapshot,replay,follow
from generic_chess.core.identity import search_state_identity
from generic_chess.core.search_runtime import SearchPathRuntime
from tools.local_agent.common import write_json


def observe(c,traces):
    sessions=[replay(c,t[-1]['record'])for t in traces]
    witnesses=[[replay(c,n['record']).state.position for n in t]for t in traces]
    runtimes=[SearchPathRuntime.from_state(s.state,c,history_witnesses=w)for s,w in zip(sessions,witnesses)]
    a,b=[r.search_key()for r in runtimes]
    return dict(fallback_equal=search_state_identity(sessions[0].state,c)==search_state_identity(sessions[1].state,c),
        eligible=[r.tt_eligible for r in runtimes],runtime_keys_equal=a==b,
        fingerprint_equal=a.ruleset_fingerprint==b.ruleset_fingerprint,
        runtime_position_hash_equal=a.runtime_hash==b.runtime_hash,
        exact_position_identity_equal=a.position_key==b.position_key,
        repetition_snapshot_equal=a.repetition==b.repetition,
        ply_equal=a.ply_count==b.ply_count,
        ordered_history_context_equal=a.history_context==b.history_context,
        ordered_history_lengths=[a.history_context.length,b.history_context.length],
        history_witness_misses=[r.history_witness_misses for r in runtimes],
        TT_probes_performed=0,Player_calls=0)


def measure(plan,data,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter()
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['cost']['new_inclusive_hard_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original key-observation inclusive deadline')
    gate();base=L.ruleset_from_dict(load(data/'named-mu-registration.json.gz')['fixed_rules']['23'])
    rr=replace(base,max_ply=12,repetition_limit=4)
    reg=dict(plan=plan,rule=L.ruleset_to_dict(rr,include_metadata=True),source_sha256=L.sha(Path(__file__)),deadline=deadline.isoformat())
    write_json(output/'registration.json',reg)
    c=L.compile_rule(rr);traces=[]
    for order in plan['paths']:
        z=L.GameSession(c,'common_026');trace=[snapshot(z)]
        for cycle in order:
            for k in plan['cycles'][cycle]:
                gate();z=follow(c,L.record_value(z.to_record()),k);trace.append(snapshot(z))
                write_json(output/'latest-prefix.json',trace[-1])
        traces.append(trace)
    gate();obs=observe(c,traces);write_json(output/'observations.json',obs)
    m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,traces=traces,observations=obs,new_Core_child_applications=16,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return reg,m


def qualify(reg,m,data):
    base=L.ruleset_from_dict(load(data/'named-mu-registration.json.gz')['fixed_rules']['23'])
    compile_scoped(L.ruleset_to_dict(replace(base,initial_setup_options=())),3,23,5)
    rr=replace(base,max_ply=12,repetition_limit=4);assert reg['rule']==L.ruleset_to_dict(rr,include_metadata=True)
    c=L.compile_rule(rr);plan=reg['plan'];traces=m['traces'];assert len(traces)==2
    assert plan['paths']==[['A','K'],['K','A']]
    assert plan['cycles']=={'A':[['A',0,2,None],['B',3,5,None],['A',2,0,None],['B',5,3,None]],'K':[['K',1,2,None],['B',3,5,None],['K',2,1,None],['B',5,3,None]]}
    count=0
    for order,trace in zip(plan['paths'],traces):
        assert len(trace)==9 and trace[0]==snapshot(L.GameSession(c,'common_026'))
        actions=[a for cy in order for a in plan['cycles'][cy]]
        for node in trace:
            assert node==snapshot(replay(c,node['record']))
            assert node['result']['status']=='ongoing';count+=1
        for i,k in enumerate(actions):assert trace[i+1]==snapshot(follow(c,trace[i]['record'],k))
    a,b=[t[-1]for t in traces]
    assert a['state']['position']==b['state']['position']
    assert a['state']['ply_count']==b['state']['ply_count']==8
    assert a['state']['repetition_counts']==b['state']['repetition_counts']
    assert a['state']['history']!=b['state']['history']
    obs=observe(c,traces);assert obs==m['observations']
    assert obs['fallback_equal'] and obs['eligible']==[True,True]and obs['history_witness_misses']==[0,0]
    assert all(obs[k]for k in('fingerprint_equal','runtime_position_hash_equal','exact_position_identity_equal','repetition_snapshot_equal','ply_equal'))
    assert not obs['ordered_history_context_equal']and not obs['runtime_keys_equal']
    assert m['ended_at']<=reg['deadline']
    return dict(status='PASS',same_named_start=True,same_Position_ply_and_repetition=True,actual_observations=obs,record_occurrences=count,new_Core_child_applications=16,new_Player_queries=0,new_graph_or_solver_calls=0,
        semantic_argument='In this full plain rule, no action/no-progress/continuous-check/other adjudication is active. Legal moves depend onPosition; terminal depends onPosition,ply andcounts. Equalthese fields imply equalfuturesemantic continuations byinduction. Orderedpast difference is extra information in the actualruntimekey here.',
        limit='One exact structural key inequality. No TTmiss/hitrate/speed/WDLerror measurement, no production key change, no statement about otherhistoryadjudications or generic game equivalence. Source fallback and normal runtime must be distinguished.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        reg,m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.data,a.output);q=qualify(reg,m,a.data);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
