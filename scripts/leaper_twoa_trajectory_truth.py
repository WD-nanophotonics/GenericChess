"""History-qualified truth census on the fixed, already played two-A panel.

This does not generate games, choose training starts, query a Player or change
the product. A complete Core-qualified physical draw invariant survives the
addition of draw-only clocks/repetition. Decisive physical vertices remain
UNKNOWN here until a separate actual full-history certificate establishes them.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import argparse, gzip, hashlib, json, time

from scripts import leaper_design as L
from scripts.leaper_cooperative_certificate import decode_position, encode_position
from scripts.leaper_explorer_truth import digest, load
from scripts.verify_leaper_twoa_graph import verify as verify_graph
from scripts.verify_leaper_twoa_safety import admission, check_position, SOURCE
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict


class FrozenHistoryTruth:
    """Scoped observer, never a scalar Position TT or learner interface."""
    def __init__(self, packet, graph, compiled):
        if packet['rule'] != graph['rule']:
            raise ValueError('full graph rule differs')
        self.c = compiled
        self.positions = [decode_position(p, compiled.initial_position) for p in packet['positions']]
        self.indices = {p:i for i,p in enumerate(self.positions)}
        self.values = graph['values']; self.ranks = graph['ranks']
        self.terminals = {int(i):v for i,v in graph['terminals'].items()}
        if any(v != (1 if self.positions[i].side_to_move == 0 else -1) for i,v in self.values.items() if v):
            raise ValueError('bare opponent cannot be a scoring winner')

    def physical(self, state):
        check_position(state.position)
        if state.position not in self.indices:
            raise ValueError('actual position outside complete supplied graph')
        i = self.indices[state.position]
        return i, self.values[i], self.ranks.get(i)

    def label(self, state):
        i,v,rank = self.physical(state)
        if state.position.ruleset_fingerprint != self.c.ruleset_fingerprint:
            raise ValueError('history fingerprint differs')
        if len(state.history) != state.ply_count+1 or Counter(h.position_key for h in state.history) != dict(state.repetition_counts):
            raise ValueError('complete history/count binding differs')
        if state.history[-1].position_key != repetition_identity_key(state.position,self.c):
            raise ValueError('current history identity differs')
        if state.terminal_status.is_terminal:
            w = state.terminal_status.winner
            if w not in (None,0):raise ValueError('unexpected opponent terminal win')
            return int(w == 0),0 if w == 0 else None,'actual_terminal'
        if any(n >= 4 for _,n in state.repetition_counts) or state.ply_count >= 64:
            raise ValueError('ongoing state after terminal boundary')
        if not v:return 0,None,'physical_draw_safety'
        return None,rank,'physical_decisive_needs_full_history_proof'

    def actions(self, state):
        value,rank,basis=self.label(state)
        if state.terminal_status.is_terminal:return value,rank,basis,[]
        branches=[]
        for a,ch in legal_successors(state,self.c):
            v,r,b=self.label(ch)
            branches.append(dict(action=action_to_dict(a),value_for0=v,rank=r,basis=b,state_sha=L.state_sha(ch)))
        if value is not None and all(r['value_for0'] is not None for r in branches):
            optimum=(max if state.position.side_to_move==0 else min)(r['value_for0'] for r in branches)
            if value!=optimum:raise ValueError('actual full-history Bellman inconsistency')
        return value,rank,basis,branches


def census(packet_path,manifest_path,graph_packet_path,output,*,seconds=600,qualified_graph=None):
    output=Path(output); output.mkdir(parents=True,exist_ok=False); tick=time.perf_counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('TRAJECTORY_TRUTH_CAP_UNKNOWN_NO_REFILL')
    manifest=L.load(manifest_path)
    if L.sha(packet_path)!=manifest['packet_sha256']:raise ValueError('policy packet bytes differ')
    docs=json.loads(gzip.decompress(Path(packet_path).read_bytes()))['documents_utf8']
    if set(docs)!=set(manifest['documents']):raise ValueError('packet document coverage differs')
    for name,text in docs.items():
        b=text.encode('utf8'); expected=manifest['documents'][name]
        if len(b)!=expected['bytes'] or hashlib.sha256(b).hexdigest()!=expected['sha256']:
            raise ValueError('original document bytes differ')
    read=lambda name:json.loads(docs[name])
    inputs=read('inputs.json'); reg=read('registration.json'); results=read('forward/results.json'); world=inputs['worlds'][1]
    gp=load(graph_packet_path); source=load(SOURCE); c,_=admission(gp,source)
    if world['rule']!=gp['rule']:raise ValueError('policy full rule differs from truth rule')
    if qualified_graph is None:
        qualification,graph=verify_graph(gp,source,seconds=min(300,seconds),return_graph=True)
    else:
        # Internal composition hook for a reader that has ALREADY performed
        # this same full Core verification in its current process.
        qualification,graph=qualified_graph
        from scripts.leaper_frozen_truth_packet import frontier_digest
        if graph['positions']!=gp['positions']or graph['rule']!=gp['rule']or frontier_digest(graph)!=gp['frontier_sha256']:
            raise ValueError('qualified Core graph differs')
    (output/'graph-qualification.json').write_text(json.dumps(qualification,indent=2))
    observer=FrozenHistoryTruth(gp,graph,c); rows=[]; events=[]; totals=defaultdict(Counter)
    expected={(seed,p) for seed in reg['seeds'] for p in reg['policies']}
    if {(r['seed'],r['policy']) for r in results['slots']}!=expected or len(results['slots'])!=120:
        raise ValueError('frozen panel coverage differs')
    for slot in results['slots']:
        guard()
        if slot['status']!='finished':raise ValueError('missing original game is not a draw')
        game=read('forward/'+slot['receipt']); policy=game['policy']; seed=game['seed']
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(game['initial_record'])))
        if L.record_value(s.to_record())!=world['roots'][0]['record']:raise ValueError('unfiltered original start differs')
        counts=Counter(); transitions=[]
        for q in game['queries']:
            guard(); st=s.state
            if q['state_sha256']!=L.state_sha(st) or q['root_ply']!=st.ply_count or q['actor']!=st.position.side_to_move:
                raise ValueError('played full-prefix binding differs')
            v,rank,basis,aa=observer.actions(st); action=L.match_action(s,q['action']); wire=action_to_dict(action)
            selected=next(r for r in aa if r['action']==wire)
            if len(aa)!=q['legal_count']:raise ValueError('actual complete action frontier differs')
            actor=st.position.side_to_move
            if v is None or any(a['value_for0'] is None for a in aa):
                raise ValueError('decisive physical vertex requires separate full-history proof; do not impute DRAW')
            useful=len({a['value_for0'] for a in aa})>1
            counts['contexts']+=1;counts['seat'+str(actor)+'_contexts']+=1
            counts['root_'+basis]+=1
            if v:counts['WIN_for0_contexts']+=1;counts['seat'+str(actor)+'_WIN_for0_contexts']+=1
            if useful:counts['seat'+str(actor)+'_value_forks']+=1
            if actor==0 and v and not selected['value_for0']:counts['missed_forced_wins']+=1
            if actor==1 and not v and selected['value_for0']:counts['defender_gifts']+=1
            transitions.append(dict(ply=st.ply_count,actor=actor,state_sha=q['state_sha256'],value_for0=v,rank=rank,basis=basis,selected_value_for0=selected['value_for0'],selected_action=wire,useful=useful))
            # Save all truth-positive roots and every decision with different
            # exact outcomes. These are post-hoc mechanism witnesses only.
            if v or useful:
                events.append(dict(policy=policy,seed=seed,ply=st.ply_count,source_receipt=slot['receipt'],record=L.record_value(s.to_record()),state_sha=q['state_sha256'],value_for0=v,rank=rank,basis=basis,actor=actor,useful=useful,selected_action=wire,selected_value_for0=selected['value_for0'],actions=aa))
            s.submit(action)
        if L.record_value(s.to_record())!=game['final_record'] or L.record_value(s.state)!=game['final_state'] or not s.state.terminal_status.is_terminal:
            raise ValueError('full final record/state/terminal differs')
        if observer.label(s.state)[0]!=game['value']:raise ValueError('literal terminal value differs')
        counts['games']=1; counts['games_with_win_exposure']=int(bool(counts['seat0_WIN_for0_contexts']))
        counts['games_with_missed_win']=int(bool(counts['missed_forced_wins']));counts['games_with_defender_gift']=int(bool(counts['defender_gifts']))
        totals[policy].update(counts);rows.append(dict(seed=seed,policy=policy,source_receipt=slot['receipt'],counts=dict(counts),contexts=transitions))
        print('TRUTH',len(rows),policy,seed,dict(counts),flush=True)
    result=dict(status='PASS',source_sha='303cb4c6d6d5e706be04f9df20ec6746556d1fc2',source_packet_sha256=L.sha(packet_path),truth_packet_sha256=L.sha(graph_packet_path),rule_fingerprint=c.ruleset_fingerprint,summary={p:dict(v)for p,v in totals.items()},events=events,rows=rows,seconds=time.perf_counter()-tick,Player_queries=0,training_episodes=0,scope='Posthoc complete census of120 already frozen policy trajectories. Original unfiltered mu preserved. Only Core-qualified physical DRAW safety is lifted through draw-only H64/repeat4; decisive vertices fail closed pending separate full-history proof. No learner labels, new sampling, evaluator ablation, policy population estimate or generic history TT.')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8');return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--graph-packet',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--seconds',type=float,default=600);a=ap.parse_args()
    r=census(a.packet,a.manifest,a.graph_packet,a.output,seconds=a.seconds)
    print(json.dumps({k:v for k,v in r.items()if k not in ('rows','events')}))
