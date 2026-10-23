"""Export lower controllers for the already identified strict alternatives."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_twoa_trajectory_capacity import CooperativeCapacity
from scripts.leaper_cooperative_certificate import decode_position
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.actions import action_from_dict


def controller(graph,c,record,*,distances=None):
    positions=[decode_position(p,c.initial_position)for p in graph['positions']];indices={p:i for i,p in enumerate(positions)}
    keys={repetition_identity_key(p,c):i for i,p in enumerate(positions)}
    return _controller(graph,c,record,positions,indices,keys,distances)


def _controller(graph,c,record,positions,indices,keys,distances):
    from functools import reduce
    from math import lcm
    s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(record)));root=indices[s.state.position]
    if s.state.terminal_status.is_terminal:raise ValueError('ongoing lower-controller root required')
    blocked={keys[k]for k,n in s.state.repetition_counts if n==3 and k in keys}
    targets={int(i)for i,v in graph['terminals'].items()if v};edges=graph['edges'];side=[p.side_to_move for p in positions]
    base=reduce(lcm,(len(es)for i,es in enumerate(edges)if side[i]==1 and es),1)
    ds=cooperative_distances(edges,targets)[0]if distances is None else distances
    if root not in ds or ds[root]>64-s.state.ply_count:raise ValueError('positive controller cannot fit actual clock')
    numbers={i:1 for i in targets};choices={};vertices={}
    def go(i):
        if i in vertices:return numbers[i]
        d=ds[i]
        good=[]if not d else [(k,j)for k,j in enumerate(edges[i])if ds.get(j)==d-1 and(j not in blocked or j in targets)]
        if not d:selected=[];positive=[];num=1
        elif side[i]==0:
            values=[(go(j),k,j)for k,j in good]
            best=max(values,key=lambda r:r[0],default=(0,None,None));num=best[0]*base
            selected=[]if best[1]is None else[best[1]];positive=selected if num else[]
        else:
            values=[(go(j),k,j)for k,j in good];num=sum(v for v,_,_ in values)*(base//len(edges[i]))
            selected=list(range(len(edges[i])));positive=[k for v,k,_ in values if v]
        numbers[i]=num
        vertices[i]=dict(vertex=i,distance=d,numerator=str(num),denominator=str(base**d),selected_action_indices=selected,positive_action_indices=positive)
        return num
    num=go(root)
    if not num:raise ValueError('lower-controller probability is zero')
    pending=[root];seen=set()
    while pending:
        i=pending.pop()
        if i in seen:continue
        seen.add(i)
        for k in vertices[i]['positive_action_indices']:pending.append(edges[i][k])
    return dict(root=root,record=record,root_state_sha=L.state_sha(s.state),remaining=64-s.state.ply_count,blocked=sorted(blocked),base=base,lower=str(F(num,base**ds[root])),vertices=[vertices[i]for i in sorted(seen)])


def build(graph,c,docs,choices,output):
    tick=time.perf_counter();positions=[decode_position(p,c.initial_position)for p in graph['positions']];indices={p:i for i,p in enumerate(positions)}
    keys={repetition_identity_key(p,c):i for i,p in enumerate(positions)};targets={int(i)for i,v in graph['terminals'].items()if v}
    ds=cooperative_distances(graph['edges'],targets)[0];policies=[];bindings=[]
    for row in choices['rows']:
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=600:raise RuntimeError('CHOICE_CERTIFICATE_CAP_UNKNOWN')
        if row['quality']!='STRICT_ORACLE_CONTINUATION_INFERIOR':continue
        game=json.loads(docs['forward/'+row['receipt']]);record=game['final_record']|{'actions':game['final_record']['actions'][:row['ply']]}
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(record)))
        if L.state_sha(s.state)!=row['state_sha']:raise ValueError('strict alternative full root differs')
        alternative=row['actions'][row['best_lower_action']];s.submit(action_from_dict(alternative['action']))
        policy=_controller(graph,c,L.record_value(s.to_record()),positions,indices,keys,ds)
        if F(policy['lower'])!=F(alternative['lower']):raise ValueError('strict alternative lower-controller differs')
        policies.append(policy)
        bindings.append(dict(policy=row['policy'],seed=row['seed'],receipt=row['receipt'],ply=row['ply'],state_sha=row['state_sha'],alternative=alternative,selected=row['actions'][row['selected']],gap=row['certified_gap_lower'],certificate_index=len(policies)-1))
    result=dict(status='PASS',policies=policies,bindings=bindings,seconds=time.perf_counter()-tick,scope='Onlylowercontrollersforthe232previouslyidentifiedactualfullprefixalternativeactions. Noplayer, newgame, trainingstartselectionoractualserved-policygain.')
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf8');return result
