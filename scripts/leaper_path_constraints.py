"""Two-way interval consistency on retained full-history edges only.

Bellman max bounds constrain a parent and every legal action. A known parent's
upper bound constrains each child; a uniquely potentially optimal action must
meet the parent's lower bound. These implications are lost by backward-only
label propagation. No graph expansion, predictor or policy is introduced.
"""
from collections import Counter, defaultdict, deque
from copy import deepcopy
import json
from pathlib import Path
import time

from scripts.leaper_saved_child_bounds import meet, current_truth, propagate
from scripts.leaper_explorer_truth import digest, load, save
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.actions import action_from_dict
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record


def max_consistency(root, actions):
    if not actions:
        raise ValueError('complete nonempty action set required')
    parent = meet(root, [max(a[0] for a in actions), max(a[1] for a in actions)])
    possible = [i for i, a in enumerate(actions) if a[1] >= parent[0]]
    assert possible
    children = [meet(a, [parent[0] if possible == [i] else -1, parent[1]])
                for i, a in enumerate(actions)]
    return parent, children


def recorded_edges(truth, *, seconds=180):
    began=time.perf_counter();rows={};stats=Counter()
    roots={r['id']:r for r in truth['roots']}
    compiled={fp:compile_rule(ruleset_from_dict(raw)) for fp,raw in truth['rules'].items()}
    for rid,record in truth['records'].items():
        c=compiled[record['ruleset_fingerprint']]
        s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
        for action in record['actions']:
            if role_stop_requested():raise RuntimeError('USER_STOP')
            if time.perf_counter()-began>=seconds:raise RuntimeError('REPLAY_CAP_UNKNOWN')
            hid=state_sha(s.state);r=roots[hid];mover=s.state.position.side_to_move
            if r['fingerprint']!=record['ruleset_fingerprint']:raise ValueError('record rule mismatch')
            s.submit(action_from_dict(action));ch=s.state
            child_id=state_sha(ch)
            key=(hid,digest(action))
            row=dict(id=hid,fingerprint=r['fingerprint'],ply=r['ply'],action=action,
                     child_id=child_id,child_ply=ch.ply_count,
                     parent_mover=mover,child_mover=ch.position.side_to_move,
                     terminal=ch.terminal_status.status.value,terminal_winner=ch.terminal_status.winner)
            if key in rows and rows[key]!=row:raise ValueError('inconsistent same action/history')
            rows[key]=row;stats['replayed_actions']+=1
        stats['records']+=1
    return dict(format='leaper-recorded-edges-v1',input_digest=digest(truth),
                rows=list(rows.values()),counts=dict(stats),seconds=time.perf_counter()-began,
                scope='Only existing recorded actions, directly replayed once. No alternate-action query or new history search.')


def constrain(truth, recorded, local, *, seconds=180):
    began=time.perf_counter()
    if recorded['input_digest']!=digest(truth):raise ValueError('recorded edge source mismatch')
    if truth.get('saved_child_packet_digest')!=digest(local):raise ValueError('local edge source mismatch')
    out=deepcopy(truth);roots={r['id']:r for r in out['roots']}
    bounds={r['id']:r['wdl_bounds'][:] for r in out['roots']}
    actions={r['id']:{digest(a['action']):a['wdl_bounds'][:] for a in r['action_bounds']}for r in out['roots']}
    if any(not a for a in actions.values()):raise ValueError('incomplete source action universe')
    edges={}
    all_edges=list(recorded['rows'])+[dict(id=q['id'],fingerprint=q['fingerprint'],ply=q['ply'],**e)
               for q in local['rows'] for e in q['children']]
    for e in all_edges:
        parent=roots[e['id']];key=e['id'],digest(e['action'])
        if e['fingerprint']!=parent['fingerprint']or e['ply']!=parent['ply']:
            raise ValueError('edge source mismatch')
        if key[1]not in actions[key[0]]:raise ValueError('unbound action')
        if e['child_ply']!=e['ply']+1:raise ValueError('nonranked edge')
        if key in edges and edges[key]!=e:raise ValueError('edge mismatch')
        if e['child_id']in roots:
            child=roots[e['child_id']]
            if child['fingerprint']!=e['fingerprint']or child['ply']!=e['child_ply']:
                raise ValueError('wrong child rule/history')
        edges[key]=e
    watchers=defaultdict(set)
    for (hid,_),e in edges.items():
        if e['child_id']in roots:watchers[e['child_id']].add(hid)
    queue=deque(roots);queued=set(roots);stats=Counter()
    while queue:
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-began>=seconds:raise RuntimeError('CONSTRAINT_CAP_UNKNOWN')
        hid=queue.popleft();queued.remove(hid);stats['root_updates_examined']+=1
        old_root=bounds[hid][:];old_actions=deepcopy(actions[hid])
        # Child-to-action intersection, including actual terminal observations.
        for ah,bs in actions[hid].items():
            e=edges.get((hid,ah))
            if e is None:continue
            child=e['child_id']
            if e['terminal']=='ongoing'and child in roots:
                cb=bounds[child]
                actions[hid][ah]=meet(bs,cb if e['parent_mover']==e['child_mover']else[-cb[1],-cb[0]])
            elif e['terminal']not in ('ongoing','no_contest'):
                winner=e['terminal_winner'];v=0 if winner is None else 1 if winner==e['parent_mover']else-1
                actions[hid][ah]=meet(bs,[v,v])
        keys=list(actions[hid])
        bounds[hid],ab=max_consistency(bounds[hid],[actions[hid][a]for a in keys])
        actions[hid]=dict(zip(keys,ab))
        affected=set()
        if old_root!=bounds[hid]:affected.update(watchers[hid]);stats['root_narrowings']+=1
        # Action-to-child intersection: exact history identity and actual mover.
        for ah,bs in actions[hid].items():
            e=edges.get((hid,ah))
            if e is None or e['terminal']!='ongoing'or e['child_id']not in roots:continue
            child=e['child_id'];cb=bs if e['parent_mover']==e['child_mover']else[-bs[1],-bs[0]]
            narrowed=meet(bounds[child],cb)
            if narrowed!=bounds[child]:
                bounds[child]=narrowed;affected.add(child);affected.update(watchers[child]);stats['child_narrowings']+=1
        if old_actions!=actions[hid]:stats['action_sets_narrowed']+=1
        for other in sorted(affected):
            if other not in queued:queue.append(other);queued.add(other)
    changes=[]
    for hid,r in roots.items():
        before=dict(wdl_bounds=r['wdl_bounds'],action_bounds=r['action_bounds'],wdl_fork=r['wdl_fork'])
        r['wdl_bounds']=bounds[hid]
        r['action_bounds']=[dict(action=a['action'],wdl_bounds=actions[hid][digest(a['action'])])for a in r['action_bounds']]
        bs=list(actions[hid].values())
        fork=(False if len(bs)==1 or all(b==bs[0]and b[0]==b[1]for b in bs)else
              True if max(b[0]for b in bs)>min(b[1]for b in bs)else None)
        if fork is not None:
            if r['wdl_fork']is not None and r['wdl_fork']!=fork:raise ValueError('fork contradiction')
            r['wdl_fork']=fork
        after={k:r[k]for k in before}
        if before!=after:changes.append(dict(id=hid,ply=r['ply'],before=before,after=after))
    out['path_constraint_digest']=digest(recorded)
    stats['seconds']=time.perf_counter()-began
    return out,changes,dict(stats)
