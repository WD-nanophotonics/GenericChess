"""One exposed three-ply all-defense existence certificate, never a solver.

The old two-orbit closure plan remains closed. This caller answers one narrowed
existence question and fixed clock controls under the actual named full rules.
"""
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import argparse, hashlib, json, time
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import snapshot, replay, follow, nodes, action_map
from scripts.verify_leaper_delayed_capture import load, compile_scoped
from tools.local_agent.common import write_json


def now():
    return datetime.now(timezone.utc)


def selected_frame(named):
    row = next(r for r in named['rows'] if r['placement'] == [1, 0, 7, 3])
    return row['key'], next(f for f in row['frames'] if f['mask'] == 23)


def measure(plan, data, output):
    start = now(); tick = time.perf_counter()
    deadline = datetime.fromisoformat(plan['started_at']) + timedelta(
        seconds=plan['absolute_preparation_and_validation_cap_seconds'])
    def gate():
        if now() >= deadline:
            raise RuntimeError('original inclusive finite-existence deadline; no extension')
    gate()
    source_reg = load(data/'named-mu-registration.json.gz')
    named = load(data/'named-mu-bridge.json.gz')
    key, source = selected_frame(named)
    original = L.ruleset_from_dict(source_reg['fixed_rules']['23'])
    rules = {h: replace(original, max_ply=h) for h in (6, *plan['clock_controls'])}
    registration = dict(plan=plan, selected_key=key, complete_rules={str(h):
        L.ruleset_to_dict(r, include_metadata=True) for h, r in rules.items()},
        source_inputs_sha256={name: L.sha(data/name) for name in
        ('named-mu-registration.json.gz', 'named-mu-bridge.json.gz')},
        producer_source_sha256=L.sha(Path(__file__)), original_deadline=deadline.isoformat())
    write_json(output/'registration.json', registration)  # BEFORE any compilation
    rows = []; new_children = 0
    for h, rule in rules.items():
        gate(); c = L.compile_rule(rule)
        if h == 6:
            root = source['root']; children = source['children']
            assert snapshot(replay(c, root['record'])) == root
            origin = 'EXACT_REUSED_PUBLISHED_NAMED_ROOT_AND_COMPLETE_ONEPLY_FRONTIER'
        else:
            z = L.GameSession(c, key); root = snapshot(z); children = []
            for action in z.legal_actions():
                gate(); child = replay(c, root['record']); child.submit(action)
                children.append(dict(action_key=list(next(k for k, a in action_map(z).items() if a == action)), node=snapshot(child)))
                new_children += 1
                write_json(output/'latest-return.json', children[-1])
            origin = 'NEW_COMPLETE_CLOCK_COUNTERFACTUAL'
        chosen = next(x['node'] for x in children if x['action_key'] == plan['steps'][0])
        defenses = []
        z = replay(c, chosen['record'])
        for action_key in action_map(z):
            gate(); after = follow(c, chosen['record'], action_key); node = snapshot(after)
            new_children += 1
            item = dict(action_key=list(action_key), node=node, finish=None)
            write_json(output/'latest-return.json', item)
            if node['result']['status'] == 'ongoing':
                finish = follow(c, node['record'], plan['steps'][2])
                item['finish'] = snapshot(finish); new_children += 1
                write_json(output/'latest-return.json', item)
            defenses.append(item)
        rows.append(dict(H=h, origin=origin, root=root, all_white_first=children,
                         chosen_capture=chosen, all_black_defenses=defenses))
        write_json(output/'partial.json', dict(rows=rows))
    gate()
    return registration, dict(started_at=start.isoformat(), ended_at=now().isoformat(),
        producer_seconds_before_final_write=time.perf_counter()-tick, rows=rows,
        new_Core_child_applications=new_children, new_Player_queries=0,
        new_graph_or_solver_calls=0, source_capsule_executions=0)


def complete_missing_finishes(reg, measured, output):
    """Repair only missing serialized-enum branch output, never repeat a query.

    The failed producer's exact source/raw output remain immutable evidence.
    This adds only the two absent fixed final moves within the ORIGINAL deadline.
    """
    from copy import deepcopy
    if now() >= datetime.fromisoformat(reg['original_deadline']):
        raise RuntimeError('original inclusive deadline, no repair extension')
    m=deepcopy(measured); added=0
    for row in m['rows']:
        c=L.compile_rule(L.ruleset_from_dict(reg['complete_rules'][str(row['H'])]))
        for d in row['all_black_defenses']:
            if d['node']['result']['status']!='ongoing' or d['finish'] is not None:
                continue
            if now() >= datetime.fromisoformat(reg['original_deadline']):
                raise RuntimeError('original inclusive deadline, no repair extension')
            assert row['H'] in (3,6)
            d['finish']=snapshot(follow(c,d['node']['record'],reg['plan']['steps'][2]))
            added+=1;write_json(output/('added-final-'+str(row['H'])+'.json'),d['finish'])
    assert added==2
    m['new_Core_child_applications']+=added
    m['ended_at']=now().isoformat()
    m['repair']=dict(reason='SessionStatus is Enum; comparing it to a string skipped the declared final-move branch. Use already serialized node status. Scientific prediction unchanged.',added_final_moves=added,original_measurement_sha256=L.sha(output/'measurements.json'),repair_source_sha256=L.sha(Path(__file__)),original_deadline=reg['original_deadline'])
    write_json(output/'measurements-completed.json',m)
    return m


def qualify(reg, m, data):
    plan=reg['plan']; source_reg=load(data/'named-mu-registration.json.gz')
    key, source=selected_frame(load(data/'named-mu-bridge.json.gz'))
    base=L.ruleset_from_dict(source_reg['fixed_rules']['23'])
    # Full grammar is checked before restoring the actual named options.
    compile_scoped(L.ruleset_to_dict(replace(base,initial_setup_options=())),3,23,5)
    assert key==reg['selected_key'] and plan['selected_placement']==[1,0,7,3]
    assert plan['steps']==[['A',0,3,None],['K',7,8,None],['A',3,4,None]]
    assert plan['expected_black_frontier']==[['K',7,8,None]]
    assert [r['H'] for r in m['rows']]==[6,1,2,3]
    assert datetime.fromisoformat(m['ended_at'])<=datetime.fromisoformat(reg['original_deadline'])
    cache={};occurrences=0;values=[]
    for row in m['rows']:
        h=row['H']; expected=replace(base,max_ply=h)
        assert reg['complete_rules'][str(h)]==L.ruleset_to_dict(expected,include_metadata=True), 'complete rule/clock mismatch'
        c=L.compile_rule(expected)
        for node in nodes(row):
            occurrences+=1;k=json.dumps(node['record'],sort_keys=True)
            if k in cache: assert node==cache[k], 'same record inconsistent retained node'
            else: assert snapshot(replay(c,node['record']))==node; cache[k]=node
        root=row['root']; assert root==snapshot(L.GameSession(c,key)), 'actual named root mismatch'
        assert root['result']['status']=='ongoing'
        expected_keys=set(action_map(replay(c,root['record'])))
        children=row['all_white_first']
        assert len(children)==len(expected_keys) and {tuple(x['action_key'])for x in children}==expected_keys, 'complete White first frontier required'
        for x in children:
            assert x['node']==snapshot(follow(c,root['record'],x['action_key'])), 'White prefix mismatch'
            assert x['node']['result']['winner']!=0, 'not a non-immediate witness'
        if h==6: assert root==source['root'] and children==source['children']
        chosen=next(x['node']for x in children if x['action_key']==plan['steps'][0])
        assert row['chosen_capture']==chosen
        assert not any(p and p['current_type_id']=='B' for p in chosen['state']['position']['board'])
        defenses=row['all_black_defenses'];actual=list(action_map(replay(c,chosen['record'])))
        assert len(defenses)==len(actual) and {tuple(d['action_key'])for d in defenses}==set(actual), 'complete Black defense frontier required'
        if h==1:
            assert not defenses and all(x['node']['result']['status']=='max_ply' and x['node']['result']['winner']is None for x in children)
            value=0
        else:
            assert set(actual)=={tuple(x) for x in plan['expected_black_frontier']}, 'fixed strategy has an additional or missing defense'
            for d in defenses:
                assert d['node']==snapshot(follow(c,chosen['record'],d['action_key'])), 'Black prefix mismatch'
                if h==2:
                    assert d['node']['result']['status']=='max_ply' and d['node']['result']['winner']is None
                    assert d['finish']is None
                else:
                    assert d['node']['result']['status']=='ongoing'
                    assert d['finish']==snapshot(follow(c,d['node']['record'],plan['steps'][2])), 'finish prefix mismatch'
                    assert d['finish']['state']['ply_count']==3
                    assert d['finish']['result']['status']=='checkmate' and d['finish']['result']['winner']==0
            value=0 if h==2 else 1
        values.append(dict(H=h,White_WDL=value))
    return dict(status='PASS',selected_key=key,placement=[1,0,7,3],root_has_immediate_win=False,
        finite_strategy_WDL=values,record_occurrences=occurrences,unique_full_records=len(cache),
        newly_labeled_H6_roots=1,population_WIN_count_lower_bound=113,population_WIN_count_upper_bound=128,
        new_Core_child_applications=m['new_Core_child_applications'],new_Player_queries=0,new_graph_or_solver_calls=0,
        source_capsule_executions=0,scope='One named exposed root, all Black defenses; no D4 label expansion, other15 UNKNOWN retained. All-H1/H2 first moves cannot mate; fixed capture forces draw by clock. H3/H6 mate wins at ply3, including terminal precedence.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output directory required')
    a.output.mkdir(parents=True)
    plan=json.loads(a.plan.read_text(encoding='utf-8-sig'))
    try:
        reg,m=measure(plan,a.data,a.output);write_json(a.output/'measurements.json',m)
        q=qualify(reg,m,a.data);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:
        write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc),at=now().isoformat()))
        raise


if __name__=='__main__':main()
