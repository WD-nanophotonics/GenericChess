"""Independent saved actual-assignment reader. No search, solver or fitted policy.
Follows executed variable/call refs; never identifies a source by equal scores.
"""
from pathlib import Path
from collections import Counter
import json, ast, hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player
from generic_chess.ai.alphabeta.search import _bounded_static_score
from tools.local_agent.common import write_json


class Graph:
    def __init__(self,data):
        self.data=data
        self.events={e['id']:e for e in data['events']}
        self.calls={c['id']:c for c in data['calls']}
        assert len(self.events)==len(data['events']) and len(self.calls)==len(data['calls'])

    def number(self,ref,name):
        if ref['type']=='ENTRY_BOUND':
            assert ref['name']==name
            return ref['value']
        assert ref['type']=='event'
        return self.events[ref['id']]['scalar'][name]

    def expr_number(self,node,site):
        if isinstance(node,ast.Name):
            assert node.id in {'alpha','beta'}
            return self.number(site[node.id+'_source'],node.id)
        if isinstance(node,ast.Constant):
            assert isinstance(node.value,int)and not isinstance(node.value,bool)
            return node.value
        if isinstance(node,ast.UnaryOp)and isinstance(node.op,ast.USub):
            return -self.expr_number(node.operand,site)
        if isinstance(node,ast.BinOp)and isinstance(node.op,(ast.Add,ast.Sub)):
            a=self.expr_number(node.left,site);b=self.expr_number(node.right,site)
            return a+b if isinstance(node.op,ast.Add)else a-b
        raise AssertionError('unsupported numeric window expression')

    def verify(self,root_ply):
        assert self.data['dropped_events']==self.data['dropped_calls']==0,'incomplete trace; causal claim UNKNOWN'
        assert set(self.events)==set(range(1,len(self.events)+1))
        assert set(self.calls)==set(range(1,len(self.calls)+1))
        qfrontier=Counter()
        for c in self.calls.values():
            assert c['completed']and c['return_ref']['type']=='event'
            ret=self.events[c['return_ref']['id']]
            assert ret['kind']=='RETURN'and ret['call_id']==c['id']and ret['score']==c['score']
            assert self.data['return_sites'][c['kind']][str(ret['site'])]==ret['expression']
            assert c['absolute_ply']==root_ply+len(c['path'])and c['ply']==len(c['path'])
            if c['parent_id']is None:
                assert not c['path']and c['kind']=='m'
            else:
                par=self.calls[c['parent_id']]
                assert par['id']<c['id']and par['iteration']==c['iteration']
                assert c['path']==par['path']+([c['edge']]if c['edge']is not None else [])
                assert c['actor']==(par['actor']if c['edge']is None else 1-par['actor'])
                site=c['callsite'];expr=ast.parse(site['expression'],mode='eval').body
                offset=1 if isinstance(expr.func,ast.Name)and expr.func.id=='quiescence'else 0
                assert self.expr_number(expr.args[offset],site)==c['entry_alpha']
                assert self.expr_number(expr.args[offset+1],site)==c['entry_beta']
            if c['kind']=='q':
                if c['generated_actions']is None:qfrontier['not_generated']+=1
                else:
                    generated=set(c['generated_actions'])
                    classified=[e for e in self.events.values()if e['call_id']==c['id']and e['kind']=='CLASSIFY']
                    assert all(e['action']in generated for e in classified)
                    qfrontier['generated']+=1
                    qfrontier['actual_quiet_rejected']+=sum(not e['noisy']for e in classified)
        for e in self.events.values():
            assert e['call_id']in self.calls
            if e['kind']=='TT_PROBE':assert e['producer']=='UNKNOWN_NOT_CAPTURED'
            if e['kind']=='EVALUATE':
                assert _bounded_static_score(e['reconstructed_raw_side_to_move'])==e['value']
                assert e['material_seat0']+e['mobility_seat0']+e['anchor_term_seat0']+e.get('promotion_sum',0)==(e['reconstructed_raw_side_to_move']if e['side']==0 else -e['reconstructed_raw_side_to_move'])
            for ref in [e.get('last_child'),e.get('last_eval'),e.get('last_tt')]:
                if not ref:continue
                if ref['type']=='call':assert self.calls[ref['id']]['return_ref']['id']<e['id']
                elif ref['type']=='event':assert ref['id']<e['id']
        return dict(calls=len(self.calls),events=len(self.events),qfrontier=dict(qfrontier))

    def walk(self,ref):
        steps=[];seen=set()
        for _ in range(200):
            token=json.dumps(ref,sort_keys=True)
            assert token not in seen,'cyclic dependency'
            seen.add(token)
            if ref['type']=='call':
                c=self.calls[ref['id']]
                steps.append(dict(ref=ref,kind='CALL',call_kind=c['kind'],path=c['path'],entry_window=[c['entry_alpha'],c['entry_beta']],score=c['score']))
                ref=c['return_ref'];continue
            if ref['type']=='ENTRY_BOUND':
                c=self.calls[ref['call_id']];site=c['callsite']
                if site is None:return dict(steps=steps,endpoint='ROOT_ENTRY_BOUND',fringe=ref)
                ex=ast.parse(site['expression'],mode='eval').body
                offset=1 if isinstance(ex.func,ast.Name)and ex.func.id=='quiescence'else 0
                arg=ex.args[offset+(0 if ref['name']=='alpha'else 1)]
                name=arg.operand.id if isinstance(arg,ast.UnaryOp)and isinstance(arg.op,ast.USub)and isinstance(arg.operand,ast.Name)else arg.id if isinstance(arg,ast.Name)else None
                steps.append(dict(ref=ref,kind='INHERITED_BOUND',expression=ast.unparse(arg),callsite=site['expression']))
                if name not in {'alpha','beta'}:return dict(steps=steps,endpoint='COMPOSITE_ENTRY_WINDOW',fringe=site)
                ref=site[name+'_source'];continue
            if ref['type']!='event':return dict(steps=steps,endpoint='UNKNOWN_REFERENCE',fringe=ref)
            e=self.events[ref['id']]
            steps.append(dict(ref=ref,kind=e['kind'],expression=e.get('expression'),call_id=e['call_id']))
            if e['kind']=='RETURN':
                ex=e['expression']
                if ex.startswith('SearchResult(best,'):name='best'
                elif ex.startswith('SearchResult(max(score,')or ex.startswith('SearchResult(score,'):name='score'
                elif ex.startswith('SearchResult(cached_score,'):name='cached_score'
                elif 'stand_pat'in ex and not e['neutral_present']:name='stand_pat'
                elif ex in {'alpha','score'}:name=ex
                else:return dict(steps=steps,endpoint='RETURN_SITE_OR_COMPOSITE',fringe=e)
                ref=e['sources'].get(name)
            elif e['kind']=='ASSIGN':
                ex=e['expression'];reads=e['reads']
                if ex in reads:ref=reads[ex]
                elif ex in {'-child_result.score','child_result.score'}:ref=reads.get('child_result')
                elif any(x in ex for x in ['child_search(','quiescence(','_quiescence_runtime(']):ref=e['last_child']
                elif '_evaluate('in ex:ref=e['last_eval']
                elif ex.startswith('score_from_tt')or ex.startswith('ctx.tt.probe'):ref=e['last_tt']
                else:return dict(steps=steps,endpoint='COMPOSITE_OR_UNTRACKED_ASSIGNMENT',fringe=e)
            elif e['kind']=='EVALUATE':return dict(steps=steps,endpoint='ACTUAL_EVALUATE',fringe=e)
            elif e['kind']=='TT_PROBE':return dict(steps=steps,endpoint='TT_PRODUCER_UNKNOWN',fringe=e)
            else:return dict(steps=steps,endpoint='UNSUPPORTED_EVENT',fringe=e)
            if ref is None:return dict(steps=steps,endpoint='MISSING_SOURCE',fringe=e)
        raise AssertionError('dependency walk bound exhausted')


def verify(d):
    plan=L.load(d/'plan.json');receipt=L.load(d/'receipt.json');assert receipt['status']=='CLOSED'and receipt['queries']==3
    assert receipt['plan_sha256']==hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()
    rows=[json.loads(x)for x in(d/'queries.jsonl').read_text().splitlines()]
    assert len(rows)==len(plan['slots'])==3
    assert L.load(d/'qualification.json')['passed']and L.load(d/'p49-reused-baseline-parity.json')['passed']
    row=rows[-1];case=next(c for c in L.load(d/'inputs.json')['cases']if c['key']=='next-role-p49')
    assert row['before_record']==case['record']and row['decision']['completed_depth']==4
    c=L.compile_rule(L.ruleset_from_dict(case['rule']));root=replay(c,case['record']);p=player(c,'baseline')
    graph=Graph(L.load(d/'p49-D4-trace.json'));integrity=graph.verify(root.state.ply_count)
    two=next(e for e in row['iterations']if e['depth']==2)
    assert sum(n['kind']=='m'for n in graph.calls.values())==row['decision']['nodes']-two['nodes']
    assert sum(n['kind']=='q'for n in graph.calls.values())==row['decision']['qnodes']-two['qnodes']
    selected=[];evaluated=set();checks=[]
    for depth in [3,4]:
        parent=next(n for n in graph.calls.values()if n['iteration']==depth and n['parent_id']is None)
        for n in sorted(graph.calls.values(),key=lambda n:n['id']):
            if n['parent_id']!=parent['id']:continue
            action=graph.data['actions'][n['edge']]
            if action['actor_type_id']not in {'B','K'}or action['to_square']!=dict(file=2,rank=2):continue
            if action['actor_type_id']=='K'and n['entry_beta']-n['entry_alpha']==1:continue
            # Select the two recorded actions and actual window types, not a score-equality/PV guess.
            chain=graph.walk(dict(type='call',id=n['id']))
            item=dict(iteration=depth,action=action,call_id=n['id'],child_entry_window=[n['entry_alpha'],n['entry_beta']],raw_child_return=n['score'],root_negated_return=-n['score'],window_kind='null'if n['entry_beta']-n['entry_alpha']==1 else'wide',chain=chain)
            if chain['endpoint']=='ACTUAL_EVALUATE':
                leaf=chain['fringe'];node=graph.calls[leaf['call_id']]
                if leaf['id']not in evaluated:
                    state=replay(c,case['record'])
                    for aid in node['path']:state.submit(L.match_action(state,graph.data['actions'][aid]))
                    assert state.state.position.side_to_move==leaf['side']
                    actual=_bounded_static_score(p._evaluator.evaluate(state.state))
                    assert actual==leaf['value']
                    evaluated.add(leaf['id']);checks.append(dict(event_id=leaf['id'],path=node['path'],value=actual,full_record=L.record_value(state.to_record())))
                factor=1 if root.state.position.side_to_move==0 else -1
                item['root_oriented_leaf_components']={k:factor*leaf[k]for k in ['material_seat0','mobility_seat0','anchor_term_seat0']}
            selected.append(item)
    assert len(selected)==5
    # These are measured separate chains. No inferred TT producer edge is added.
    b3=next(x for x in selected if x['iteration']==3 and x['action']['actor_type_id']=='B')
    b4scout=next(x for x in selected if x['iteration']==4 and x['action']['actor_type_id']=='B'and x['window_kind']=='null')
    assert b3['chain']['endpoint']==b4scout['chain']['endpoint']=='ACTUAL_EVALUATE'
    deltas={k:b4scout['root_oriented_leaf_components'][k]-b3['root_oriented_leaf_components'][k]for k in b3['root_oriented_leaf_components']}
    return dict(passed=True,integrity=integrity,selected=selected,new_Player_queries=3,reused_baseline_queries=1,new_independent_manual_leaf_evaluations=len(checks),leaf_checks=checks,observed_B_scout_leaf_component_deltas=deltas,limitations=['Final B wide-research dependency includes inherited/TT bounds; no missing TT producer is invented. Scout leaf support is a separately observed chain.','Component arithmetic on frozen observed leaves is not a rerun with altered weights and proves no WDL repair.','Source WDL is exposed graph attribution, not new all-defense proof. No quiet omission causalclaim.','All generated-unvisited/unclassified actions remain unclassified; no extra semantic queries in observer.'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);d=p.parse_args().directory
    a=verify(d);write_json(d/'assessment.json',a)
    print(json.dumps({k:v for k,v in a.items()if k not in ['selected','leaf_checks']}))
    for x in a['selected']:print(x['iteration'],x['action']['actor_type_id'],x['window_kind'],x['root_negated_return'],x['chain']['endpoint'],x.get('root_oriented_leaf_components'))
