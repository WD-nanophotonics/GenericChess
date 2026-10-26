"""Verify derived finite source strategies using the existing public checker."""
from collections import Counter
import argparse,gzip,json,time
from pathlib import Path
from generic_chess.core.actions import action_from_dict
from generic_chess.core.transition import apply_action
from scripts.leaper_truth_compatibility import bind_context,verify_bound_tree,digest
from scripts.qualify_pvs_source_intake import git_bytes,BASE,INPUT
from scripts.research_record import record_value
from scripts.propagate_pvs_terminal_bounds import load


def verify(derived,frontiers,max_proofs=100,max_seconds=90):
    begun=time.perf_counter()
    games={g['game_id']:g for g in json.loads(gzip.decompress(git_bytes(BASE+'pilot/games.json.gz')))}
    roots={r['id']:r for r in json.loads(gzip.decompress(git_bytes(INPUT)))['rows']}
    representatives={q['context_sha256']:q for q in frontiers['queries']}
    data={(r['ruleset_fingerprint'],r['record_sha256']):r for r in derived['contexts']}
    cache={};producer_selected=0
    def context(key):
        if key not in cache:
            d=data[key];q=representatives[d['source_context_sha256']];game=games[q['game_id']]
            record=dict(game['final_record']);record['actions']=record['actions'][:d['ply']]
            c=bind_context(roots[d['case_id']]['RuleSet'],record)
            if c.identity['state_sha256']!=d['state_sha256']or c.identity['record_sha256']!=key[1]:
                raise ValueError('proof parent differs from bound full source')
            cache[key]=c
        return cache[key]
    def build(key,direction):
        nonlocal producer_selected
        indexed={};pending=[key];depths={key:0};leaves=Counter()
        while pending:
            current=pending.pop();row=data[current];c=context(current);state=record_value(c.session.state);state_key=digest(state)
            if state_key in indexed:continue
            existential=(row['side_to_move']==0)==(direction=='lower')
            choose=lambda e:e['bounds'][0]>=0 if direction=='lower'else e['bounds'][1]<=0
            edges=[e for e in row['children']if choose(e)]
            if not edges or (not existential and len(edges)!=len(row['children'])):
                raise ValueError('derived bound lacks its required quantified edges')
            if existential:edges=edges[:1]
            wire_edges=[]
            for edge in edges:
                child_key=tuple(edge['child_key'])
                if edge['authority']=='CORE_TERMINAL':
                    child=apply_action(c.session.state,action_from_dict(edge['action']),c.session.compiled)
                    producer_selected+=1;child_state=record_value(child)
                    if digest(child_state)!=edge['state_sha256']or not child.terminal_status.is_terminal:
                        raise ValueError('proof terminal differs from checked source edge')
                    if child.terminal_status.winner is not None:raise ValueError('this source-only zero proof unexpectedly has nonzero leaf')
                    indexed[digest(child_state)]={'state':child_state,'children':[]}
                    leaves[child.terminal_status.status.value]+=1
                elif child_key in data:
                    child_state=record_value(context(child_key).session.state)
                    if digest(child_state)!=edge['state_sha256']:raise ValueError('proof child full state differs')
                    pending.append(child_key);depths[child_key]=max(depths.get(child_key,0),depths[current]+1)
                else:raise ValueError('unexpanded unknown is not a certificate leaf')
                wire_edges.append({'action':edge['action'],'state':child_state})
            indexed[state_key]={'state':state,'children':wire_edges}
        return list(indexed.values()),max(depths.values(),default=0)+1,dict(leaves)
    checks=[];counts=Counter();example=None;complete=True
    changed=[(k,v)for k,v in data.items()if v['one_step_bounds']!=v['derived_bounds']]
    for key,d in sorted(changed,key=lambda item:(item[1]['ply'],item[1]['case_id'])):
        if len(checks)>=max_proofs or time.perf_counter()-begun>=max_seconds:
            complete=False;break
        if d['derived_bounds']==[0,0]:
            raise ValueError('new exact roots require both lower and upper certificates; this source batch has none')
        direction='lower'if d['derived_bounds'][0]==0 else'upper'
        nodes,depth,leaves=build(key,direction)
        proof=verify_bound_tree(context(key),nodes,0,direction=direction,value_seat=0)
        counts.update(proof['counts'])
        checks.append({'context_key':list(key),'case_id':d['case_id'],'ply':d['ply'],'derived_bounds':d['derived_bounds'],
                       'proof':proof,'maximum_certificate_edges_on_path':depth,'terminal_leaf_reasons':leaves})
        if example is None:
            q=representatives[d['source_context_sha256']];g=games[q['game_id']]
            record=dict(g['final_record']);record['actions']=record['actions'][:d['ply']]
            example={'rule':roots[d['case_id']]['RuleSet'],'record':record,'direction':direction,'bound':0,'value_seat':0,'nodes':nodes}
    return dict(status='COMPLETE'if complete else'PARTIAL',planned_strengthened_roots=len(changed),
                verified_strengthened_roots=len(checks),seconds=time.perf_counter()-begun,max_seconds=max_seconds,max_proofs=max_proofs,
                production_selected_apply_calls=producer_selected,verification_Core_counts=dict(counts),
                checks=checks,first_concrete_certificate=example,new_graph_state_expansions=0,new_Player_calls=0,
                scope='Actual existing finite AND/OR checker, full-history Core edges and terminal leaves; verification computations counted. No unknown leaf accepted, source branch expanded beyond prior frontier, heuristic value or play-strength claim.')


def replay_bound_with_horizon(rule,record,nodes,bound,direction,target_max_ply,*,value_seat=0):
    """Revalidate only supplied strategy edges after one explicit horizon edit.

    Default context attribution stays incompatible. An ongoing target leaf is
    UNKNOWN; no new continuation is generated to complete the old certificate.
    """
    from copy import deepcopy
    from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
    from scripts.leaper_truth_compatibility import compare_contexts
    old=bind_context(rule,record)
    source=verify_bound_tree(old,nodes,bound,direction=direction,value_seat=value_seat)
    target_rule=deepcopy(rule);target_rule['max_ply']=target_max_ply
    target_record=deepcopy(record);target_record['ruleset_fingerprint']=compute_fingerprint(ruleset_from_dict(target_rule))
    target=bind_context(target_rule,target_record)
    indexed={digest(n['state']):n for n in nodes}
    pending=[(digest(record_value(old.session.state)),target.session.state)]
    rebuilt={};unresolved=[];target_applies=0
    while pending:
        old_key,state=pending.pop();node=indexed[old_key];wire=record_value(state);key=digest(wire)
        if key in rebuilt:continue
        if state.terminal_status.is_terminal and node['children']:
            unresolved.append({'ply':state.ply_count,'reason':'TARGET_TERMINAL_BEFORE_SOURCE_CONTINUATION'})
            rebuilt[key]={'state':wire,'children':[]};continue
        edges=[]
        if not node['children']and not state.terminal_status.is_terminal:
            unresolved.append({'ply':state.ply_count,'reason':'SOURCE_TERMINAL_NOW_ONGOING'})
        for edge in node['children']:
            child=apply_action(state,action_from_dict(edge['action']),target.session.compiled)
            target_applies+=1;child_wire=record_value(child)
            edges.append({'action':edge['action'],'state':child_wire})
            pending.append((digest(edge['state']),child))
        rebuilt[key]={'state':wire,'children':edges}
    result=dict(source_proof=source,default_context_attribution=compare_contexts(old,target),
                source_rule_fingerprint=old.identity['ruleset_fingerprint'],target_context=target.identity,
                target_selected_apply_calls=target_applies,target_unresolved_leaves=unresolved,
                new_missing_continuations_generated=0,
                scope='Explicit new-rule certificate replay, never automatic source-label transfer. An unresolved target leaf is UNKNOWN, not a refutation of the bound or proof of another WDL.')
    if unresolved:
        return dict(result,status='UNKNOWN_TARGET_CERTIFICATE_NOT_COMPLETE',target_verified_bound=None)
    proof=verify_bound_tree(target,list(rebuilt.values()),bound,direction=direction,value_seat=value_seat)
    return dict(result,status='NEW_TARGET_RULE_CERTIFICATE_VERIFIED',target_verified_bound=proof)


def main():
    p=argparse.ArgumentParser();p.add_argument('--frontiers',type=Path,required=True);p.add_argument('--derived',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(load(a.derived),load(a.frontiers));a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items()if k not in ('checks','first_concrete_certificate')}))
    if r['checks']:print(json.dumps(r['checks'][0]))
if __name__=='__main__':main()
