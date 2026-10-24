"""Scoped strict-rank strategy avoiding actual incoming repetition barriers.

This only proves a positive history WIN when a complete existing physical
certificate admits an avoiding strategy. Failure remains UNKNOWN, never DRAW.
No labels enter experience or learning and no experimental Player is called.
"""
from pathlib import Path
from copy import copy
from functools import lru_cache
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,source_documents,write
from scripts.leaper_cooperative_certificate import encode_position,decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.identity import repetition_identity_key


def rank_avoidance(edges,sides,terminals,ranks,blocked,root):
    """One winning seat0, original strict ranks; original terminals win first."""
    @lru_cache(None)
    def solve(i):
        if i in terminals:return 0 if terminals[i]==0 else None
        if i in blocked or i not in ranks:return None
        options=[]
        for j in edges[i]:
            v=solve(j)if j in ranks and ranks[j]<ranks[i]else None
            options.append((j,v))
        if sides[i]==0:
            valid=[(j,v)for j,v in options if v is not None]
            if not valid:return None
            return min(v for j,v in valid)+1
        if not options or any(v is None for j,v in options):return None
        return max(v for j,v in options)+1
    value=solve(root)
    chosen={}
    def visit(i):
        if i in chosen or i in terminals:return
        rank=solve(i)
        if rank is None:return
        children=[j for j in edges[i]if j in ranks and ranks[j]<ranks[i]and solve(j)is not None]
        if sides[i]==0:children=[min(children,key=lambda j:(solve(j),j))]
        chosen[i]=children
        for j in children:visit(j)
    if value is not None:visit(root)
    return value,chosen,solve.cache_info().currsize


def run(output):
    output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter()
    graph=Path('docs/research/data/leaper_ab_learning_and_rank_20261024/domain-0.json.gz')
    g=json.loads(gzip.decompress(graph.read_bytes()));world=json.loads(source_documents()['contact/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    assert g['rule']==world['rule']
    indices={tuple(p):i for i,p in enumerate(g['positions'])};ranks={int(k):v for k,v in g['ranks'].items()};terms={int(k):v for k,v in g['terminals'].items()};sides=[p[0]for p in g['positions']]
    assert set(terms.values())=={None,0}
    identity={repetition_identity_key(decode_position(p,c.initial_position),c):i for i,p in enumerate(g['positions'])}
    assert len(identity)==len(indices)
    old=Path('artifacts/leaper-ab-uniform-20261024');oldplan=json.loads((old/'plan.json').read_bytes());oldresult=json.loads((old/'result.json').read_bytes());selected=None
    for entry in oldresult['rows']:
        slot=entry['slot']
        if slot['group']!='contact':continue
        row=json.loads((old/f"game-{slot['id']:03d}.json").read_bytes());s=restore(c,world['roots'][slot['root']]['record'])
        events={e['state_sha256']for e in row['events']if e['kind']=='candidate'}
        for action in L.deserialize_game_record(json.dumps(row['final_record'])).actions:
            encoded=tuple(encode_position(s.state.position,c.initial_position));i=indices.get(encoded)
            if L.state_sha(s.state)in events and i in ranks and ranks[i]<=64-s.state.ply_count:
                barriers={identity[k]for k,n in s.state.repetition_counts if n>=3 and k in identity and identity[k]in ranks and ranks[identity[k]]<ranks[i]}
                if barriers:
                    selected=(copy(s),i,barriers,slot);break
            s.submit(action)
        if selected:break
    if selected is None:raise ValueError('no actual source-order rank barrier')
    root,index,barriers,slot=selected
    all_blocked={identity[k]for k,n in root.state.repetition_counts if n>=3 and k in identity}-{index}
    rank,policy,visited=rank_avoidance(g['edges'],sides,terms,ranks,all_blocked,index)
    spec=dict(graph_sha256=L.sha(graph),source_plan_sha256=L.sha(old/'plan.json'),slot=slot,record=L.record_value(root.to_record()),state_sha256=L.state_sha(root.state),index=index,original_rank=ranks[index],remaining=64-root.state.ply_count,lower_rank_barriers=sorted(barriers),all_nonroot_incoming_count3=sorted(all_blocked),selection='First actual candidate context in closed contact Uniform cohort with a relevant lower-rank incoming count3, source row/ply order. Posthoc proof diagnostic only, never TRAIN.',scope='Fixed contact King8/Ferz/Wazir remove, draw-onlyH64/repeat4, singlewinningseat0 complete domain. Strict ORIGINAL rank decreases on selected strategy; full actualhistory tree independently checked. No generic PositionTT or DRAW inference on failure.')
    write(output/'spec.json',spec)
    write(output/'policy.json',dict(root_safe_rank=rank,policy=policy,graph_states_visited=visited))
    if rank is None:
        result=dict(status='UNKNOWN',reason='No avoiding strategy in strict-original-rank subset',seconds=time.perf_counter()-tick)
        write(output/'result.json',result);return result
    assert rank<=ranks[index]<=64-root.state.ply_count
    nodes=[];cap=20000;deadline=time.perf_counter()+180
    def expand(s):
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if len(nodes)>=cap or time.perf_counter()>=deadline:raise RuntimeError('HISTORY_TREE_CAP_UNKNOWN')
        i=indices[tuple(encode_position(s.state.position,c.initial_position))];nid=len(nodes)
        node=dict(state_sha256=L.state_sha(s.state),index=i,original_rank=ranks.get(i),ply=s.state.ply_count,terminal=L.record_value(s.result),children=[]);nodes.append(node)
        if s.state.terminal_status.is_terminal:
            assert s.result.winner==0
            return nid
        legal=s.legal_actions();by_child={}
        for a in legal:
            ch=copy(s);ch.submit(a);j=indices[tuple(encode_position(ch.state.position,c.initial_position))]
            by_child.setdefault(j,[]).append((a,ch))
        selected_children=policy[i]
        if s.state.position.side_to_move==1:assert sorted(j for j,aa in by_child.items()for _ in aa)==sorted(g['edges'][i])
        for j in selected_children:
            alternatives=by_child[j]
            if s.state.position.side_to_move==0:alternatives=alternatives[:1]
            for a,ch in alternatives:
                assert ranks[j]<ranks[i]
                cid=expand(ch);node['children'].append(dict(action=L.record_value(a),node=cid))
        return nid
    status='WIN';reason='Complete actual-history strategy tree'
    try:expand(root)
    except RuntimeError as error:status='UNKNOWN';reason=str(error)
    payload=json.dumps(dict(spec=spec,nodes=nodes),separators=(',',':')).encode();(output/'history-tree.json.gz').write_bytes(gzip.compress(payload,mtime=0))
    result=dict(status=status,reason=reason,nodes=len(nodes),safe_rank=rank,original_rank=ranks[index],barriers=sorted(barriers),graph_states_visited=visited,tree_sha256=L.sha(output/'history-tree.json.gz'),seconds=time.perf_counter()-tick,Player_queries=0,training_updates=0)
    write(output/'result.json',result);print(result,flush=True);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.output)
