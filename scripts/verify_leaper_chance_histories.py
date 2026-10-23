"""Expand finite success supports through ACTUAL full-history Session trees.

Converging Position nodes are not merged: their complete histories replay
separately. Only explicitly positive success branches contribute to the lower
probability; every defender's full legal denominator is checked at that actual
history. This never treats an abort as an actual draw or ended game.
"""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load
from scripts.leaper_cooperative_certificate import decode_position
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record


def verify(packet,certificates,output,*,seconds=1200,node_cap=200000,controller_cap=None):
    tick=time.perf_counter();c,_=admission(packet,load(SOURCE));positions=[decode_position(p,c.initial_position)for p in packet['positions']]
    indices={p:i for i,p in enumerate(positions)};counts=Counter();receipts=[];policies=[p for r in certificates for p in r['policies']]
    if controller_cap is not None:policies=policies[:controller_cap]
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds or counts['actual_history_nodes']>=node_cap:raise RuntimeError('ACTUAL_CHANCE_TREE_CAP_UNKNOWN_NO_REFILL')
    for number,policy in enumerate(policies):
        guard();s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(policy['record'])));rows={r['vertex']:r for r in policy['vertices']}
        if L.state_sha(s.state)!=policy['root_state_sha']:raise ValueError('actual chance root differs')
        def expand(current):
            guard();counts['actual_history_nodes']+=1
            # Bind a canonical JSON roundtrip and a fresh replay at EVERY
            # actual history, not just at a shared physical DAG vertex.
            wire=serialize_game_record(current.to_record());decoded=deserialize_game_record(wire)
            if serialize_game_record(decoded)!=wire:raise ValueError('actual chance JSON roundtrip differs')
            actual=L.GameSession.replay(c,decoded);counts['full_record_Core_replay_plies']+=actual.state.ply_count
            if actual.state!=current.state or actual.result!=current.result:raise ValueError('actual chance replay differs')
            i=indices[actual.state.position];row=rows[i];d=row['distance']
            if actual.state.terminal_status.is_terminal:
                if actual.result.winner!=0 or d!=0:raise ValueError('predicted chance success is actual draw/other terminal')
                counts['actual_mate_leaves']+=1;return F(1)
            if not d:raise ValueError('predicted chance terminal is ongoing')
            legal=actual.legal_actions();counts['actual_legal_frontiers']+=1
            selected=row['selected_action_indices'];positive=row['positive_action_indices']
            if actual.state.position.side_to_move==1:
                if selected!=list(range(len(legal))):raise ValueError('actual defense denominator differs')
                denominator=len(legal)
            else:
                if len(selected)!=1:raise ValueError('actual one controller action required')
                denominator=1
            total=F(0)
            for k in positive:
                if k not in selected or not 0<=k<len(legal):raise ValueError('actual positive action not legal')
                child=L.GameSession.replay(c,actual.to_record());child.submit(legal[k]);counts['literal_positive_transitions']+=1
                j=indices[child.state.position]
                if j not in rows or rows[j]['distance']!=d-1:raise ValueError('actual chance rank does not decrease')
                total+=expand(child)
            value=total/denominator
            if value!=F(int(row['numerator']),int(row['denominator'])):raise ValueError('actual full-tree probability differs')
            return value
        value=expand(s)
        if value!=F(policy['lower']):raise ValueError('actual controller root lower differs')
        receipts.append(dict(root_state_sha=policy['root_state_sha'],lower=str(value)))
        if(number+1)%16==0:print('ACTUAL_CHANCE',number+1,dict(counts),time.perf_counter()-tick,flush=True)
    result=dict(verified=True,controllers=len(receipts),counts=dict(counts),rows=receipts,seconds=time.perf_counter()-tick,Player_queries=0,scope='Every successful full-history branch expanded separately, completeactuallegaldefense denominators, canonicalJSON+publicSessionreplayatEVERYnode andliteralterminalmate; no Position/historyquotient. Zero success-accounting aborts are not actual DRAW/terminal labels.')
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--graph-packet',type=Path,required=True);p.add_argument('--certificate',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--controllers',type=int);a=p.parse_args()
    r=verify(load(a.graph_packet),[load(f)for f in a.certificate],a.output,controller_cap=a.controllers)
    print({k:v for k,v in r.items()if k!='rows'})
