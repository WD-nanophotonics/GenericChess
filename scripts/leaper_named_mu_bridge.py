"""Bind one initialized-rule family to two fixed rules with explicit named mu.

Semantic protocol validation only; no Player or source-capsule execution.
"""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import argparse,json,time
from generic_chess.rules.schema import RuleInitialSetupOption
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import physical_action
from scripts.leaper_delayed_capture_witness import snapshot,physical
from tools.local_agent.common import write_json


def run(source,output):
    if output.exists():raise ValueError('NEW output required')
    output.mkdir(parents=True);tick=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
    parent=L.load(source);ordered=sorted(parent['rows'],key=lambda r:tuple(r['placement']))
    keys=[None]+[f'common_{i:03d}'for i in range(1,len(ordered))]
    options=tuple(RuleInitialSetupOption(key,L.ruleset_from_dict(row['pair'][0]['rule']).initial_position)
                  for key,row in zip(keys[1:],ordered[1:]))
    rules={};compiled={};compile_times={}
    for frame in ordered[0]['pair']:
        mask=frame['mask'];base=L.ruleset_from_dict(frame['rule'])
        rr=replace(base,initial_setup_options=options)
        rules[mask]=rr
    reg=dict(started_at=started,source_sha256=L.sha(Path(__file__)),parent_sha256=L.sha(source),cap_seconds=300,
             mu=dict(kind='uniform_default_plus_named_initial_setup',keys=keys,count=len(keys),default_selection_weight=1,unselected_default_extra_weight=0),
             fixed_rules={str(k):L.ruleset_to_dict(v,include_metadata=True)for k,v in rules.items()})
    plan=L.load(Path('.local_agent/ag-named-mu-bridge-plan.json'))
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=300)
    if datetime.now(timezone.utc)>=deadline:raise RuntimeError('Original phase cap, no extension')
    reg['original_phase_deadline']=deadline.isoformat()
    write_json(output/'registration.json',reg)
    for mask,rr in rules.items():
        t=time.perf_counter();compiled[mask]=L.compile_rule(rr);compile_times[mask]=time.perf_counter()-t
    rows=[];applications=0
    for key,parent_row in zip(keys,ordered):
        if time.perf_counter()-tick>=300 or datetime.now(timezone.utc)>=deadline:raise RuntimeError('frozen cap')
        frames=[]
        for source_frame in parent_row['pair']:
            mask=source_frame['mask'];rr=rules[mask];c=compiled[mask]
            old_rule=L.ruleset_from_dict(source_frame['rule'])
            assert L.ruleset_to_dict(replace(rr,initial_position=old_rule.initial_position,initial_setup_options=()))==L.ruleset_to_dict(old_rule)
            z=L.GameSession(c,key);new_root=snapshot(z);children=[]
            actual={physical_action(L.record_value(a),3):a for a in z.legal_actions()}
            for old_child in source_frame['branches']:
                action_key=tuple(old_child['action_key']);child=L.GameSession.replay(c,z.to_record())
                child.submit(actual[action_key]);applications+=1
                children.append(dict(action_key=list(action_key),node=snapshot(child)))
            frames.append(dict(mask=mask,root=new_root,children=children))
        rows.append(dict(key=key,placement=parent_row['placement'],frames=frames))
        write_json(output/'latest-raw-root.json',rows[-1])
    # A predeclared legal nonoptimal four-ply cycle tests actual repetition.
    # A c3-c1, B a1-a3, A c1-c3, B a3-a1, under both masks.
    cycle_keys=[('A',8,2,None),('B',0,6,None),('A',2,8,None),('B',6,0,None)]
    target=next(i for i,r in enumerate(ordered)if r['placement']==[5,8,3,0]);cycles=[]
    for source_frame in ordered[target]['pair']:
        mask=source_frame['mask']
        for mode in('source_family','fixed_named'):
            rr=L.ruleset_from_dict(source_frame['rule'])if mode=='source_family'else rules[mask]
            c=L.compile_rule(rr)if mode=='source_family'else compiled[mask]
            z=L.GameSession(c,None if mode=='source_family'else keys[target]);trace=[snapshot(z)]
            for k in cycle_keys:
                actual={physical_action(L.record_value(a),3):a for a in z.legal_actions()}
                z.submit(actual[k]);trace.append(snapshot(z))
            cycles.append(dict(mask=mask,mode=mode,rule=L.ruleset_to_dict(rr,include_metadata=True),trace=trace))
    m=dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,
            compile_seconds=compile_times,rows=rows,cycles=cycles,new_literal_semantic_child_applications=applications,
            new_cycle_action_applications=16,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m)
    q=qualify(reg,m,parent);write_json(output/'qualification.json',q);print(json.dumps(q))


def qualify(reg,m,parent):
    old={tuple(r['placement']):r for r in parent['rows']};keys=reg['mu']['keys'];count=0;order=0
    assert len(m['rows'])==len(keys)==reg['mu']['count']==152
    assert len(set(keys))==152 and keys[0]is None and keys.count(None)==1 and reg['mu']['unselected_default_extra_weight']==0
    assert {r['key']for r in m['rows']}==set(keys)and len({tuple(r['placement'])for r in m['rows']})==152
    assert {tuple(r['placement'])for r in m['rows']}==set(old)
    for mask in(22,23):
        rr=L.ruleset_from_dict(reg['fixed_rules'][str(mask)])
        assert {o.setup_key for o in rr.initial_setup_options}==set(keys[1:])and len(rr.initial_setup_options)==151
    for row in m['rows']:
        assert row['key']in keys
        source=old[tuple(row['placement'])]
        for frame in row['frames']:
            old_frame=next(x for x in source['pair']if x['mask']==frame['mask'])
            assert physical(frame['root'])==physical(old_frame['root'])and frame['root']['result']==old_frame['root']['result']
            assert frame['root']['record']['schema_version']==(1 if row['key']is None else 3)
            assert frame['root']['record'].get('initial_setup_key')==row['key']
            assert frame['root']['record']['ruleset_fingerprint']!=old_frame['root']['record']['ruleset_fingerprint']
            newkeys=[physical_action(a,3)for a in frame['root']['legal_actions']]
            oldkeys=[physical_action(a,3)for a in old_frame['root']['legal_actions']]
            order+=int(newkeys==oldkeys)
            assert set(newkeys)==set(oldkeys)
            indexed={tuple(x['action_key']):x for x in old_frame['branches']}
            assert {tuple(x['action_key'])for x in frame['children']}==set(indexed)
            for child in frame['children']:
                prior=indexed[tuple(child['action_key'])]['child'];node=child['node']
                assert physical(node)==physical(prior)and node['result']==prior['result']
                assert sorted(v for _,v in node['state']['repetition_counts'])==sorted(v for _,v in prior['state']['repetition_counts'])
                count+=1
    for mask in(22,23):
        a,b=[next(x for x in m['cycles']if x['mask']==mask and x['mode']==mode)for mode in('source_family','fixed_named')]
        assert len(a['trace'])==len(b['trace'])==5
        for x,y in zip(a['trace'],b['trace']):
            assert physical(x)==physical(y)and x['result']==y['result']
            assert sorted(v for _,v in x['state']['repetition_counts'])==sorted(v for _,v in y['state']['repetition_counts'])
        assert a['trace'][-1]['result']['status']==b['trace'][-1]['result']['status']=='repetition'
        assert a['trace'][-1]['state']['ply_count']==4
    return dict(status='PASS',fixed_complete_rules=2,root_frames=304,
                preserved_physical_oneply_children=count,preserved_root_physical_action_order_count=order,
                actual_repetition_cycle_records=4,cycle_plies_each=4,
                mu_size=152,named_setup_options_per_rule=151,new_named_GameRecord_schema=3,default_GameRecord_schema=1,default_extra_weight=0,
                compile_seconds=m['compile_seconds'],producer_seconds=m['seconds'],
                implication='The n3 one-ply conclusions are now bound to two fixed complete RuleSets plus one explicit152key mu. Full physical cycle/repetition semantics verified on selected actual histories.',
                limits='Fingerprints/record schemas change. No old record transplant, independent WDL engine, or Player/TT/evaluator/equal-cost equivalence claim. Full all-history Core correspondence still rests on the stated pure-rule source argument, not a finite replay alone.',
                new_Player_queries=0,new_graph_or_solver_calls=0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.source,a.output)
