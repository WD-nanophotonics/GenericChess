"""Cooperative mating capacity along already frozen played full histories.

Shortest paths use the Core-qualified closure. Incoming count3 vertices are
arrival-only draw exits, except scoring terminals (mate precedes repeat).
Strictly decreasing distances give simple paths, so no new repeat can arise.
This is cooperative reachability, never forced WDL or policy utility.
"""
from __future__ import annotations
from collections import Counter, defaultdict, deque, OrderedDict
from pathlib import Path
import argparse, gzip, json, time
from copy import copy
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from scripts.verify_leaper_twoa_graph import verify as verify_graph
from scripts.verify_leaper_twoa_safety import admission, SOURCE
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.actions import action_from_dict


class CooperativeCapacity:
    def __init__(self, graph, compiled):
        self.graph=graph; self.c=compiled
        self.positions=[decode_position(p,compiled.initial_position)for p in graph['positions']]
        self.indices={p:i for i,p in enumerate(self.positions)}
        self.key_index={repetition_identity_key(p,compiled):i for i,p in enumerate(self.positions)}
        self.targets={int(i)for i,v in graph['terminals'].items()if v}
        self.parents=[[]for _ in self.positions]
        for i,children in enumerate(graph['edges']):
            for j in children:self.parents[j].append(i)
        self.cache=OrderedDict(); self.bfs_count=0
        self.base=self.distances(frozenset())

    def distances(self,blocked):
        if blocked in self.cache:
            self.cache.move_to_end(blocked);return self.cache[blocked]
        distances={i:0 for i in self.targets};nxt={};todo=deque(sorted(self.targets))
        while todo:
            j=todo.popleft()
            for i in self.parents[j]:
                if i not in distances:
                    distances[i]=distances[j]+1;nxt[i]=j
                    if i not in blocked or i in self.targets:todo.append(i)
        self.bfs_count+=1;self.cache[blocked]=distances,nxt
        # Keep memory bounded; repeated game histories can reuse recent maps.
        while len(self.cache)>4:self.cache.popitem(last=False)
        return distances,nxt

    def at(self,session,*,replay_positive=True):
        state=session.state
        if state.position.ruleset_fingerprint!=self.c.ruleset_fingerprint:raise ValueError('capacity full rule differs')
        i=self.indices[state.position]
        if state.terminal_status.is_terminal:
            return dict(possible=state.terminal_status.winner==0,distance=0 if state.terminal_status.winner==0 else None,basis='actual_terminal',vertex=i,path=[])
        if len(state.history)!=state.ply_count+1 or Counter(h.position_key for h in state.history)!=dict(state.repetition_counts):
            raise ValueError('capacity complete history differs')
        blocked=frozenset(self.key_index[k]for k,n in state.repetition_counts if n==3 and k in self.key_index)
        if any(n>=4 for _,n in state.repetition_counts):raise ValueError('capacity root already repeats')
        distances,nxt=self.base
        if i in distances:
            current=i;intersects=False
            while distances[current]:
                current=nxt[current]
                if current in blocked and current not in self.targets:intersects=True;break
            if intersects:distances,nxt=self.distances(blocked)
        distance=distances.get(i);remaining=64-state.ply_count
        possible=distance is not None and distance<=remaining
        basis=('cooperative_path'if possible else 'physical_no_mate'if i not in self.base[0] else 'history_no_mate'if distance is None else 'clock_too_short')
        path=[]
        if possible:
            current=i
            while distances[current]:
                child=nxt[current];choice=self.graph['edges'][current].index(child)
                path.append(self.graph['actions'][current][choice]);current=child
            if replay_positive:
                actual=copy(session)
                for raw in path:actual.submit(action_from_dict(raw))
                if not actual.state.terminal_status.is_terminal or actual.result.winner!=0 or actual.state.ply_count-state.ply_count!=distance:
                    raise ValueError('literal positive cooperative witness differs')
        return dict(possible=possible,distance=distance,basis=basis,vertex=i,path=path,blocked=len(blocked))


def analyze(graph,compiled,docs,truth,output,*,seconds=600):
    tick=time.perf_counter();observer=CooperativeCapacity(graph,compiled);summary=defaultdict(Counter);rows=[];witnesses=[];path_plies=0
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('CAPACITY_CAP_UNKNOWN_NO_REFILL')
    for saved in truth['rows']:
        guard();game=json.loads(docs['forward/'+saved['source_receipt']]);s=L.GameSession.replay(compiled,L.deserialize_game_record(json.dumps(game['initial_record'])))
        counts=Counter();transitions=[];first_loss=None;last=None;chosen_witnesses=set()
        for q,context in zip(game['queries'],saved['contexts'],strict=True):
            guard()
            if L.state_sha(s.state)!=q['state_sha256'] or q['state_sha256']!=context['state_sha']:
                raise ValueError('capacity frozen full-prefix differs')
            result=observer.at(s);path_plies+=len(result['path']);counts['contexts']+=1;counts[result['basis']]+=1
            actor=s.state.position.side_to_move;counts['seat'+str(actor)+'_'+result['basis']]+=1
            ordinary=sum(p is not None and p.current_type_id=='A'for p in s.state.position.board)
            if result['possible'] and ordinary<2:raise ValueError('single-color obstruction violated')
            if not result['possible'] and first_loss is None:first_loss=s.state.ply_count
            if last is not None and not last['possible'] and result['possible']:raise ValueError('reachability cannot reappear along actual continuation')
            if result['basis'] not in chosen_witnesses:
                chosen_witnesses.add(result['basis'])
                witnesses.append(dict(policy=game['policy'],seed=game['seed'],receipt=saved['source_receipt'],ply=s.state.ply_count,record=L.record_value(s.to_record()),state_sha=q['state_sha256'],result=result))
            transitions.append(dict(ply=s.state.ply_count,actor=actor,state_sha=q['state_sha256'],ordinary=ordinary,**{k:v for k,v in result.items()if k!='path'}))
            action=L.match_action(s,q['action']);s.submit(action);last=result
        if not s.state.terminal_status.is_terminal or L.record_value(s.to_record())!=game['final_record']:raise ValueError('capacity final full record differs')
        counts['games']=1;counts['first_loss_ply_sum']+=s.state.ply_count if first_loss is None else first_loss
        counts['positive_path_Core_plies']+=sum(r['distance'] for r in transitions if r['possible'])
        summary[game['policy']].update(counts)
        rows.append(dict(policy=game['policy'],seed=game['seed'],receipt=saved['source_receipt'],first_no_cooperative_mate_ply=first_loss,terminal_ply=s.state.ply_count,terminal=s.result.status.value,counts=dict(counts),contexts=transitions))
        print('CAPACITY',len(rows),game['policy'],first_loss,dict(counts),flush=True)
    result=dict(status='PASS',summary={p:dict(v)for p,v in summary.items()},rows=rows,witnesses=witnesses,positive_path_Core_plies=path_plies,reverse_BFS_maps=observer.bfs_count,seconds=time.perf_counter()-tick,Player_queries=0,training_episodes=0,scope='Only120existing complete policy games; every positive prefix has literal Core mate replay, negatives use the complete closure shortest-path invariant plus actual incoming count3 and H64. Cooperative possibility is not forced WIN, error, occupancy under another policy or utility. Truth-selected saved witnesses are never experiential training starts.')
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--truth',type=Path,required=True);p.add_argument('--graph-packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if L.sha(a.packet)!=load(a.manifest)['packet_sha256']:raise ValueError('capacity packet hash differs')
    truth=load(a.truth)
    if truth['source_packet_sha256']!=L.sha(a.packet) or truth['truth_packet_sha256']!=L.sha(a.graph_packet):raise ValueError('capacity truth source differs')
    docs=json.loads(gzip.decompress(a.packet.read_bytes()))['documents_utf8'];gp=load(a.graph_packet);source=load(SOURCE);c,_=admission(gp,source)
    receipt,graph=verify_graph(gp,source,return_graph=True)
    r=analyze(graph,c,docs,truth,a.output)
    print(json.dumps({k:v for k,v in r.items()if k not in ('rows','witnesses')}))
