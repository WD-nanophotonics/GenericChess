"""Recombine only already recorded Position transitions into mate proposals.

This edge book is incomplete. Failure to find/replay a path is UNKNOWN, never
an absence or minimax proof. Actual target-history Core replay certifies each
positive. No additional legal successor generation or policy game is done.
"""
from collections import Counter,defaultdict,deque
from copy import deepcopy
import json
import time

from generic_chess.core.actions import action_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_design import state_sha
from scripts.leaper_explorer_truth import digest
from scripts.leaper_cooperative_truth import admit
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_saved_suffix_transfer import try_witness
from scripts.leaper_microgames import role_stop_requested


def shortest_paths(edges, goals):
    """Finite observed edges only; return one simple path to a supplied goal."""
    parents=defaultdict(list)
    for parent,choices in edges.items():
        for action,child in choices:parents[child].append((parent,action))
    distances={g:0 for g in goals};nxt={};queue=deque(goals)
    while queue:
        child=queue.popleft()
        for parent,action in parents[child]:
            if parent in distances:continue
            distances[parent]=distances[child]+1;nxt[parent]=(action,child);queue.append(parent)
    return distances,nxt


def prepare(truth, *, seconds=180):
    began=time.perf_counter();last=0.;stats=Counter()
    compiled={fp:compile_rule(ruleset_from_dict(raw))for fp,raw in truth['rules'].items()}
    for fp,c in compiled.items():admit(ruleset_from_dict(truth['rules'][fp]),c)
    roots={r['id']:r for r in truth['roots']};targets={};goals=set();edges=defaultdict(dict)
    for rid,record in truth['records'].items():
        c=compiled[record['ruleset_fingerprint']]
        s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
        for action in record['actions']:
            now=time.perf_counter()
            if now-began>=seconds:raise RuntimeError('EDGEBOOK_CAP_UNKNOWN')
            if now-last>=.2:
                last=now
                if role_stop_requested():raise RuntimeError('USER_STOP')
            before=s.state.position;hid=state_sha(s.state)
            if roots[hid]['cooperative_decisive']is None:targets[hid]=before
            s.submit(action_from_dict(action));child=s.state.position
            ah=digest(action)
            if ah in edges[before]and edges[before][ah]!=(action,child):
                raise ValueError('same recorded Position/action has different child')
            edges[before][ah]=(action,child)
            if s.state.terminal_status.winner is not None:goals.add(child)
            stats['replayed_actions']+=1
        stats['source_records']+=1
    # Stable traversal and ties; none of these choices selects an experience root.
    from scripts.research_record import record_value
    key=lambda p:digest(record_value(p))
    ordered={p:sorted(cs.values(),key=lambda ac:(digest(ac[0]),key(ac[1])))
             for p,cs in sorted(edges.items(),key=lambda pair:key(pair[0]))}
    ds,nxt=shortest_paths(ordered,sorted(goals,key=key));rows=[]
    for hid,pos in sorted(targets.items()):
        if pos not in ds:stats['no_observed_path_UNKNOWN']+=1;continue
        r=roots[hid]
        if ds[pos]>r['rule_remaining']:stats['observed_path_exceeds_remaining_UNKNOWN']+=1;continue
        path=[];current=pos
        while current not in goals:
            action,child=nxt[current];path.append(action);assert ds[child]==ds[current]-1;current=child
        assert path and len(path)==ds[pos]
        rows.append(dict(id=hid,fingerprint=r['fingerprint'],witness=path))
    stats['observed_positions']=len(set(ordered)|{ch for cs in ordered.values()for _,ch in cs})
    stats['observed_edges']=sum(len(cs)for cs in ordered.values());stats['decisive_goal_positions']=len(goals)
    return dict(format='leaper-observed-path-proposals-v1',input_digest=digest(truth),rows=rows,counts=dict(stats),
                seconds=time.perf_counter()-began,caps=dict(proof_seconds=180,proposals=2000),
                scope='All remaining cooperation-UNKNOWN saved histories; one shortest path in the union of original recorded transitions, sorted history IDs, no alternate path retry. An incomplete observed edgebook cannot prove absence. Original raw/shortened attempts remain closed; no new successor expansion, rules/layouts or TRAIN selection.')


def run(truth,proposals):
    if proposals['input_digest']!=digest(truth):raise ValueError('observed-path source mismatch')
    start=time.perf_counter();compiled={};rows=[];status='COMPLETE';stats=Counter()
    for q in proposals['rows']:
        if role_stop_requested():status='USER_STOP';break
        if time.perf_counter()-start>=proposals['caps']['proof_seconds']:status='PROOF_CAP_UNKNOWN';break
        if len(rows)>=proposals['caps']['proposals']:status='PROPOSAL_CAP_UNKNOWN';break
        fp=q['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        r,s=root_session(truth,q['id'],compiled[fp])
        if r['fingerprint']!=fp or r['cooperative_decisive']is not None:raise ValueError('target mismatch')
        if not q['witness']or len(q['witness'])>r['rule_remaining']:raise ValueError('invalid proposed length')
        observation=try_witness(s,q['witness']);rows.append(q|dict(observation=observation))
        stats['literal_edges']+=observation['executed'];stats['proved'if observation['proved']else'unknown']+=1
    return dict(format='leaper-observed-path-proofs-v1',input_digest=digest(truth),proposal_digest=digest(proposals),
                rows=rows,status=status,unstarted=[q['id']for q in proposals['rows'][len(rows):]],
                counts=dict(stats),seconds=time.perf_counter()-start)


def apply(truth,packet):
    if packet['input_digest']!=digest(truth):raise ValueError('observed proof source mismatch')
    out=deepcopy(truth);roots={r['id']:r for r in out['roots']};seen=set()
    for q in packet['rows']:
        if q['id']in seen:raise ValueError('duplicate observed proof root')
        seen.add(q['id']);r=roots[q['id']]
        if q['fingerprint']!=r['fingerprint']:raise ValueError('observed proof rule mismatch')
        if type(q['observation']['proved'])is not bool:raise ValueError('boolean proof flag required')
        if q['observation']['proved']:
            if r['cooperative_decisive']is False:raise ValueError('observed proof contradicts known absence')
            r['cooperative_decisive']=True;r['universal_draw']=False
            r['observed_path_basis']='literal_target_history_recombined_recorded_actions'
    out['observed_path_proof_digest']=digest(packet)
    return out


def verify(truth,proposals,packet, *, seconds=180):
    if packet['proposal_digest']!=digest(proposals)or proposals['input_digest']!=digest(truth):
        raise ValueError('observed proof proposal mismatch')
    start=time.perf_counter();compiled={};stats=Counter();by={q['id']:q for q in proposals['rows']}
    for q in packet['rows']:
        if time.perf_counter()-start>=seconds:raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if {k:q[k]for k in ('id','fingerprint','witness')}!=by[q['id']]:raise ValueError('witness binding mismatch')
        if not q['observation']['proved']:continue
        fp=q['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        r,s=root_session(truth,q['id'],compiled[fp]);executed=0
        if not q['witness']or len(q['witness'])>r['rule_remaining']:raise ValueError('witness length mismatch')
        for a in q['witness']:
            if s.state.terminal_status.is_terminal:break
            s.submit(action_from_dict(a));executed+=1
        t=s.state.terminal_status
        actual=dict(proved=t.is_terminal and t.winner is not None,status=t.status.value,terminal_winner=t.winner,
                    executed=executed,final_ply=s.state.ply_count,final_history_id=state_sha(s.state))
        if digest(actual)!=digest(q['observation'])or not actual['proved']:raise ValueError('observed literal proof mismatch')
        stats['positive_roots']+=1;stats['literal_edges']+=executed
    out=apply(truth,packet)
    return dict(verified=True,counts=dict(stats),seconds=time.perf_counter()-start,
                output_digest=digest(out),scope='All positive literal target-history paths, not completeness of the observed edgebook or any negative/minimax/E0 claim.')
