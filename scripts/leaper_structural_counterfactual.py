"""Join existing rule coordinates to published root/action labels, never solve."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import argparse,gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import motion_graph,physical_action
from tools.local_agent.common import write_json

PROVIDER='e71968ff8ec5e3ab57cade9b965e44a23558780a'
AUX_PACKET_SHA='aa02eb7967ef9479f17f0710c3d795fc0680dec919adb50f26cf8faaccecf847'
PRIMARY_SHA='c0f942bbd2822261da81cd25f614d2a3d411cee73ec8c03d6b47d06209e706c9'
AUX_ROOTS_LOGICAL_SHA='6cc1faf7bd10dbe2efe5b400c3fe3c3e950b928164bf028e3c922e2e18de7be4'

def load_document(path):
    return json.loads(gzip.decompress(path.read_bytes()))if path.suffix=='.gz'else L.load(path)

def documents(packet,manifest):
    raw=packet.read_bytes();m=L.load(manifest);assert hashlib.sha256(raw).hexdigest()==m['compressed_sha256']==PRIMARY_SHA
    body=gzip.decompress(raw);assert hashlib.sha256(body).hexdigest()==m['decoded_sha256'];p=json.loads(body);docs=p['documents_utf8']
    for name,text in docs.items():assert hashlib.sha256(text.encode('utf-8')).hexdigest()==m['original_sha256'][name]
    return {name:json.loads(text)for name,text in docs.items()if name.endswith('.json')}

def classify(low,high):
    # Values are FROM published full-history labels, not recomputed here.
    a={tuple(k):v for k,v in zip(low['action_keys'],low['values'])};b={tuple(k):v for k,v in zip(high['action_keys'],high['values'])}
    assert len(a)==len(low['action_keys'])and len(b)==len(high['action_keys'])and a.keys()<=b.keys()
    common=sorted(a.keys()&b.keys());added=sorted(b.keys()-a.keys());changed=[k for k in common if a[k]!=b[k]]
    ao={k for k,v in a.items()if v==max(a.values())};bo={k for k,v in b.items()if v==max(b.values())}
    old_membership_changed=[k for k in common if(k in ao)!=(k in bo)]
    return dict(shared_actions=len(common),added_actions=[list(k)for k in added],shared_revaluations=[dict(action=list(k),values=[a[k],b[k]])for k in changed],old_action_optimal_membership_changed=[list(k)for k in old_membership_changed],new_optimal_actions=[list(k)for k in added if k in bo],support_changed=ao!=bo,shared_support_changed=bool(old_membership_changed),new_action_only_value_change=bool(added)and not changed,root_values=[max(a.values()),max(b.values())])

def analyze(primary,aux,costs):
    tick=time.perf_counter();plan=primary['edge-plan.json'];worlds={(w['n'],w['mask'],w['rank']):w for w in primary['edge-inputs.json']['worlds']};profiles={(w['n'],w['mask'],w['rank']):w for w in primary['edge-results.json']['root_profiles']}
    assert aux['provider_commit']==PROVIDER and aux['provider_packet_sha256']==AUX_PACKET_SHA and aux['source_bundle_sha256']==PRIMARY_SHA
    assert hashlib.sha256(json.dumps(aux,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()==AUX_ROOTS_LOGICAL_SHA
    assert costs['source_bundle_sha256']==PRIMARY_SHA
    roots={};core_roots=core_edges=0
    for graph in aux['graphs']:
        n,m=graph['n'],graph['mask']
        for row in graph['roots']:
            key=n,m,row['rank'];assert key not in roots;w=worlds[key];assert row['rule']==w['rule']and row['record']==w['record']
            c=L.compile_rule(L.ruleset_from_dict(w['rule']));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['record'])))
            assert s.state.ply_count==0 and not s.state.terminal_status.is_terminal and L.state_sha(s.state)==row['state_sha']
            actions={physical_action(L.record_value(a),n):a for a in s.legal_actions()};keys=[tuple(k)for k in row['action_keys']];assert set(keys)==actions.keys()and len(keys)==len(actions)==profiles[key]['branch'];assert len(row['clocks'])==2
            immediate={}
            for ak,action in actions.items():
                child=L.GameSession.replay(c,s.to_record());child.submit(action);immediate[ak]=dict(terminal=child.result.status.value,winner=child.result.winner,record=L.record_value(child.to_record()));core_edges+=1
            for clock in row['clocks']:
                assert clock['H']in(6,64)and len(clock['actions'])==len(keys)and all(v in(-1,0,1)for v in clock['actions']);assert clock['WDL']==max(clock['actions'])and clock['fork']==(min(clock['actions'])<max(clock['actions']))
                for ak,value in zip(keys,clock['actions']):
                    terminal=immediate[ak]
                    if terminal['terminal']!='ongoing':assert value==(0 if terminal['winner']is None else 1 if terminal['winner']==0 else -1)
            roots[key]=(row,immediate);core_roots+=1
    assert core_roots==600
    # Literal retained cost joins; no setup cost imputation or fresh query.
    actual_cost={(budget,r['seed']):r for budget in(32768,131072)for r in primary[f'N{budget}.json']['rows']};cost_index={}
    for cr in costs['rows']:
        key=cr['n'],cr['mask'],cr['source_rank'];row,_=roots[key];clock=next(z for z in row['clocks']if z['H']==64);values=dict(zip(map(tuple,row['action_keys']),clock['actions']));raw=actual_cost[cr['budget'],cr['seed']];d=raw['decision'];assert physical_action(d['action'],cr['n'])==tuple(cr['action']);assert cr['chosen_action_WDL']==values[tuple(cr['action'])]and cr['root_WDL']==clock['WDL']
        assert cr['paid_nodes']==d['nodes']+d['qnodes']and cr['actual_completed_depth']==d['completed_depth']and cr['actual_reason']==d['termination_reason']and cr['query_seconds']==raw['query_seconds'];cost_index[key+(cr['budget'],)]=cr
    assert len(cost_index)==costs['matched_returns']==864
    graph_features={(n,m):motion_graph(m,n)for n,m,_ in roots};rows=[];summary={};examples={}
    for n in(4,5,6):
        for edge in plan['edges']:
            lo,hi=edge['masks'];gl,gh=graph_features[n,lo],graph_features[n,hi]
            for rank in range(8):
                a,ia=roots[n,lo,rank];b,ib=roots[n,hi,rank];assert a['rule']['initial_position']==b['rule']['initial_position']and a['record']['actions']==b['record']['actions']==[]
                ra,rb=map(L.ruleset_from_dict,(a['rule'],b['rule']));pts=tuple(next(p for p in rb.piece_types if p.type_id=='A')if p.type_id=='A'else p for p in ra.piece_types);assert L.ruleset_to_dict(replace(ra,piece_types=pts),include_metadata=True)==L.ruleset_to_dict(rb,include_metadata=True)
                for H in(6,64):
                    ac=next(x for x in a['clocks']if x['H']==H);bc=next(x for x in b['clocks']if x['H']==H);cl=classify(dict(action_keys=a['action_keys'],values=ac['actions']),dict(action_keys=b['action_keys'],values=bc['actions']))
                    revaluations=[]
                    for diff in cl['shared_revaluations']:
                        k=tuple(diff['action']);revaluations.append(dict(**diff,immediate_terminals=[ia[k]['terminal'],ib[k]['terminal']],winners=[ia[k]['winner'],ib[k]['winner']]))
                    caps=[not gl['orthogonal_offset_independence'],not gh['orthogonal_offset_independence']];r=dict(n=n,masks=[lo,hi],rank=rank,H=H,stratum=edge['stratum'],state_shas=[a['state_sha'],b['state_sha']],fingerprints=[a['record']['ruleset_fingerprint'],b['record']['ruleset_fingerprint']],static_capacity=caps,components=[len(gl['components']),len(gh['components'])],degrees=[gl['mean_degree'],gh['mean_degree']],forward2=[profiles[n,lo,rank]['forward2_width'],profiles[n,hi,rank]['forward2_width']],WDL=[ac['WDL'],bc['WDL']],fork=[ac['fork'],bc['fork']],cooperative=[ac['cooperative'],bc['cooperative']],classification=cl,shared_value_mechanisms=revaluations,added_action_mechanisms=[dict(action=k,value=dict(zip(map(tuple,b['action_keys']),bc['actions']))[tuple(k)],immediate=ib[tuple(k)])for k in cl['added_actions']],costs={str(B):[cost_index.get((n,m,rank,B))for m in(lo,hi)]for B in(32768,131072)})
                    rows.append(r);counts=summary.setdefault(f'{n}/H{H}',Counter());counts['paired_roots']+=1
                    for label,yes in dict(WDL_changed=r['WDL'][0]!=r['WDL'][1],fork_changed=r['fork'][0]!=r['fork'][1],capacity_changed=caps[0]!=caps[1],shared_revaluation=bool(revaluations),support_changed=cl['support_changed'],shared_support_changed=cl['shared_support_changed'],unchanged_capacity_shared_revaluation=caps[0]==caps[1]and bool(revaluations),unchanged_capacity_fork_change=caps[0]==caps[1]and r['fork'][0]!=r['fork'][1]).items():
                        counts[label]+=yes
                        if yes:examples.setdefault(f'{n}/H{H}/'+label,dict(row=len(rows)-1,n=n,masks=[lo,hi],rank=rank,H=H))
    return dict(status='PASS',rows=rows,summary={k:dict(v)for k,v in summary.items()},examples=examples,Core_roots=core_roots,Core_oneply_edges=core_edges,source_cost_rows=864,source_unlabelled_cost_rows=288,new_Player_queries=0,new_solver_calls=0,new_training_updates=0,source_capsule_executions=0,seconds=time.perf_counter()-tick,scope='Exact published AUX labels joined to PRIMARY rules/history/action frontiers; truth is attributed, not independently re-solved. H6 is an explicit clock counterfactual, H64 the original rule. Shared endpoints and roots, exposed strata, not IID or a population forecast. Missing cost cells remain null.')

def run(primary,manifest,aux,costs,output):
    assert not output.exists();r=analyze(documents(primary,manifest),load_document(aux),load_document(costs));write_json(output,r);print('PASS',r['Core_roots'],r['Core_oneply_edges'],r['summary']);return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--primary',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--aux-roots',type=Path,required=True);p.add_argument('--costs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.primary,a.manifest,a.aux_roots,a.costs,a.output)
