"""Replay retained paths and terminal-child facts on the exact H64 targets.

No Player, new trajectory, path recombination or solver budget. A missing
cooperative witness is UNKNOWN. Supplied PRIMARY paths are not independent runs.
"""
from copy import deepcopy
import json
import time
from collections import Counter

from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_single_parity_truth import admit,domain,bare_opponent_bound
from scripts.leaper_explorer_truth import digest
from scripts.leaper_design import state_sha


def apply_paths(truth,worlds,source_paths):
    start=time.perf_counter();out=deepcopy(truth);by={r['world']:r for r in out['rows']};verified=[];nodes=0
    # Exact prefix equality, not a Position join or hash-only path transfer.
    for w in worlds:
        row=by[w['world']];_,c,_=admit(w['rule'],require_parity=False)
        target=GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record'])))
        prefix=w['initial_record']['actions']
        for source in source_paths:
            record=source['complete_record']
            if(record['ruleset_fingerprint']!=w['fingerprint']or record['actions'][:len(prefix)]!=prefix):continue
            s=GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record'])))
            for a in record['actions'][len(prefix):]:
                if s.state.terminal_status.is_terminal:raise ValueError('source suffix continues past target terminal')
                s.submit(action_from_dict(a));nodes+=1
            if s.result.winner is None:raise ValueError('provided positive path does not win')
            if row['cooperative_decisive']is False:raise ValueError('path contradicts no-mate certificate')
            row['cooperative_decisive']=True
            verified.append(dict(world=w['world'],source_world=source['world'],source_slot=source['slot'],
                source_record_digest=digest(record),source_complete_record=record,
                target_state_sha=state_sha(target.state),suffix=record['actions'][len(prefix):],
                terminal_state_sha=state_sha(s.state),terminal_status=s.result.status.value,winner=s.result.winner))
    # Independently bind PRIMARY's existing one-ply witness flags and retain all
    # legal actions; ongoing children are never filled by a search estimate.
    local=[]
    for w in worlds:
        row=by[w['world']]
        if row['wdl_bounds'][0]==row['wdl_bounds'][1]:continue
        _,c,_=admit(w['rule'],require_parity=False)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record'])))
        actor=s.state.position.side_to_move;branches=[];immediate=[]
        for ac,ch in legal_successors(s.state,c):
            domain(ch.position);term=ch.terminal_status
            if term.is_terminal:
                v=0 if term.winner is None else 1 if term.winner==actor else-1;b=[v,v]
            else:
                child_bound=bare_opponent_bound(ch.position)
                b=[-child_bound[1],-child_bound[0]]
            branches.append(dict(action=action_to_dict(ac),bounds=b,child_state_sha=state_sha(ch),terminal=term.status.value))
            if b==[1,1]:immediate.append(action_to_dict(ac))
        if bool(immediate)!=w['initial_oneply_win_witness']:raise ValueError('PRIMARY one-ply metadata disagrees')
        bounds=[max(b['bounds'][i]for b in branches)for i in(0,1)]
        fork=True if any(a['bounds'][0]>b['bounds'][1]for a in branches for b in branches)else False if len(branches)==1 or all(b['bounds']==bounds and bounds[0]==bounds[1]for b in branches)else None
        row.update(wdl_bounds=bounds,fork=fork,action_bounds=branches)
        if immediate:
            row['cooperative_decisive']=True
            row['reason']='literal_immediate_WIN'
        local.append(dict(world=w['world'],state_sha=state_sha(s.state),bounds=bounds,fork=fork,immediate_wins=immediate,branches=branches))
    return out,dict(format='leaper-handoff-witness-layer-v1',input_truth_digest=digest(truth),output_truth_digest=digest(out),
        paths=verified,path_edges=nodes,local=local,local_Core_edges=sum(len(r['branches'])for r in local),
        seconds=time.perf_counter()-start,scope='Retained literal full-record suffixes sharing the exact target rule and prefix; no fresh path search. Actual one-ply PRIMARY witness flags independently checked; unknown children stay intervals. Existence is not a forced-WIN certificate.')


def apply_clock(truth,clock):
    out=deepcopy(truth);by={r['world']:r for r in out['rows']}
    for source in clock['rows']:
        r=by[source['world']]
        if r['state_sha']!=source['state_sha']or r['fingerprint']!=source['fingerprint']:
            raise ValueError('clock layer wrong target')
        r.update(reason='closed_domain_H64_rank',wdl_bounds=[source['value']]*2,
            cooperative_decisive=True if source['value']else r['cooperative_decisive'],
            fork=source['fork'],action_bounds=[dict(action=a['action'],bounds=[a['wdl']]*2,child_state_sha=a['child_state_sha'])for a in source['actions']])
    return out
