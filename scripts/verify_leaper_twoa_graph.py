"""Rebuild the supplied two-A physical closure entirely through public Core.

Portable packet stores only positions, frozen inputs and the producer's full
frontier hash. No saved adjacency or rank is executed/trusted. Full records
and actual diagnostic PVs are checked separately by the evidence reader.
"""
from collections import Counter
from pathlib import Path
import argparse,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.verify_leaper_twoa_safety import admission,check_position,SOURCE
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_frozen_truth_packet import frontier_digest
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict


def verify(packet,source,*,seconds=300,return_graph=False):
    tick=time.perf_counter();c,_=admission(packet,source);positions=[decode_position(p,c.initial_position)for p in packet['positions']];indices={p:i for i,p in enumerate(positions)}
    if len(indices)!=len(positions):raise ValueError('duplicate graph vertex')
    edges=[];actions=[];terms={};counts=Counter()
    for i,p in enumerate(positions):
        if i%128==0:
            if role_stop_requested():raise RuntimeError('USER_STOP')
            if time.perf_counter()-tick>=seconds:raise RuntimeError('TWOA_GRAPH_READER_CAP_UNKNOWN')
        check_position(p);s=fresh_state(p,c);counts['Core_vertices']+=1
        if s.terminal_status.is_terminal:
            w=s.terminal_status.winner
            if w not in(None,0):raise ValueError('bare King scored')
            terms[i]=0 if w is None else 1 if w==p.side_to_move else-1;edges.append([]);actions.append([])
            counts['terminal_'+s.terminal_status.status.value]+=1;continue
        ee=[];aa=[]
        for a,ch in legal_successors(s,c):
            if ch.position not in indices:raise ValueError('incomplete actual Core closure')
            ee.append(indices[ch.position]);aa.append(action_to_dict(a));counts['Core_edges']+=1
        if not ee:raise ValueError('ongoing vertex has no children')
        edges.append(ee);actions.append(aa)
    g=dict(n=5,positions=packet['positions'],actions=actions,edges=edges,terminals=terms,rule=packet['rule'])
    if frontier_digest(g)!=packet['frontier_sha256']:raise ValueError('producer Core frontier hash differs')
    values,ranks=attractor(edges,terms);hist=Counter(ranks.values());relative=Counter()
    for i,(side,b)in enumerate(packet['positions']):relative[f'actor{side}/for0_{values[i]if side==0 else-values[i]}']+=1
    if {str(k):v for k,v in hist.items()}!=packet['rank_histogram']:raise ValueError('rank strata differ')
    receipt=dict(verified=True,counts=dict(counts),rank_histogram=dict(hist),value_counts=dict(relative),seconds=time.perf_counter()-tick,
        scope='Every125940physicalvertexand756108edge rebuiltthroughactualpublicCore; sourcefullfrontierhashandrankstrataequal. Onlythisfrozenposition-localtwoAfinitegame; historylabelsrequireseparateincoming-record/clock/repetitionproof.')
    if return_graph:
        g.update(values=values,ranks=ranks);return receipt,g
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(load(a.packet),load(SOURCE));a.output.write_text(json.dumps(r,indent=2));print(r)
