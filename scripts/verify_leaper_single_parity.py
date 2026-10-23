"""Portable finite proof reader, no private graph/pickle or policy execution."""
from __future__ import annotations
import argparse
from collections import Counter
from copy import copy
import json
from pathlib import Path
import time

from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.leaper_single_parity_truth import admit,exhaustive,bind
from scripts.leaper_single_parity_truth import bare_opponent_bound,domain as single_actor_domain
from generic_chess.core.actions import action_from_dict
from scripts.leaper_clock_rebinding import check_domain
from scripts.leaper_handoff_witnesses import apply_clock,apply_paths
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_design import state_sha

DEFAULT=Path('docs/research/data/leaper_single_parity_20261023')


def literal_value(session,counts,*,start,seconds=60,max_nodes=20000):
    counts['nodes']+=1
    if counts['nodes']>max_nodes or time.perf_counter()-start>seconds:
        raise RuntimeError('LITERAL_CONTROL_CAP_UNKNOWN')
    if session.result.status.value!='ongoing':
        counts['terminal_'+session.result.status.value]+=1;winner=session.result.winner
        return 0 if winner is None else 1 if winner==session.state.position.side_to_move else-1
    values=[]
    for action in session.legal_actions():
        child=copy(session);child.submit(action)
        values.append(-literal_value(child,counts,start=start,seconds=seconds,max_nodes=max_nodes))
    return max(values)


def without_cost(value):
    if isinstance(value,dict):return {k:without_cost(v)for k,v in value.items()if k not in('seconds',)}
    if isinstance(value,list):return [without_cost(v)for v in value]
    return value


def verify(directory=DEFAULT):
    start=time.perf_counter();data=load(directory/'inputs.json.gz');worlds=data['worlds'];handoff=data['handoff']
    if len(worlds)!=48 or len(handoff['rows'])!=48:raise ValueError('expected unchanged48 target histories')
    checks={};stored=load(directory/'local-summary.json')
    for row in stored['checks']:
        w=next(w for w in worlds if w['masks']==[row['mask']])
        result=exhaustive(w['rule'])
        if without_cost(result)!=without_cost({k:v for k,v in row.items()if k!='mask'}):
            raise ValueError('local geometry/Core proof differs')
        checks[row['mask'],]=result
    actual=bind(worlds,handoff,checks)
    clock=load(directory/'clock-rebinding.json.gz');domain=load(directory/'clock-domain.json.gz')
    derived=check_domain(domain,worlds)
    if without_cost(derived)!=without_cost(clock):raise ValueError('closed domain/clock result differs')
    literal_nodes=0
    for row in clock['rows']:
        w=next(w for w in worlds if w['world']==row['world']);_,c,_=admit(w['rule'],require_parity=False)
        session,certificate=decode_session_certificate(c,row['literal_win_certificate'])
        receipt=verify_session_certificate(session,certificate,max_nodes=8192,seconds=30)
        if not receipt['verified']or state_sha(session.state)!=row['state_sha']:
            raise ValueError('stored literal all-defense certificate failed')
        literal_nodes+=receipt['nodes']
    actual=apply_clock(actual,clock)
    actual,witnesses=apply_paths(actual,worlds,load(directory/'source-paths.json'))
    if without_cost(witnesses)!=without_cost(load(directory/'witness-layer.json.gz')):
        raise ValueError('literal path/terminal-child layer differs')
    if digest(actual)!=digest(load(directory/'truth.json.gz')):raise ValueError('final48target truth differs')
    controls=load(directory/'clock-controls.json.gz');control_nodes=0
    for row in controls['rows']:
        _,c,_=admit(row['rule'],require_parity=False)
        session=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
        if state_sha(session.state)!=row['state_sha']or c.max_ply-session.state.ply_count!=row['remaining']:
            raise ValueError('clock control full history binding failed')
        counts=Counter();value=literal_value(session,counts,start=time.perf_counter())
        if value!=row['value']or dict(counts)!=row['literal_counts']:
            raise ValueError('literal full-history finite tree differs')
        control_nodes+=counts['nodes']
    fork=load(directory/'literal-fork-witness.json');w=next(w for w in worlds if w['world']==fork['world'])
    _,c,_=admit(w['rule'],require_parity=False)
    s=GameSession.replay(c,deserialize_game_record(json.dumps(fork['root_record'])))
    if state_sha(s.state)!=fork['root_state_sha']:raise ValueError('literal fork wrong root')
    s.submit(action_from_dict(fork['bad_action']))
    if state_sha(s.state)!=fork['child_state_sha']or bare_opponent_bound(s.state.position)!=[-1,0]:
        raise ValueError('literal fork bad-action binding failed')
    s.submit(action_from_dict(fork['defender_capture']))
    if state_sha(s.state)!=fork['bare_leaf_state_sha']or single_actor_domain(s.state.position)[1]:
        raise ValueError('literal fork capture does not reach bare-King domain')
    return dict(verified=True,truth_digest=digest(actual),target_histories=48,
        WDL=dict(Counter(str(r['wdl_bounds'])for r in actual['rows'])),
        cooperative=dict(Counter(str(r['cooperative_decisive'])for r in actual['rows'])),
        fork=dict(Counter(str(r['fork'])for r in actual['rows'])),
        local_mask_checks=len(checks),closed_domain_vertices=derived['vertices'],
        closed_domain_edges=derived['counts']['Core_edges'],literal_certificate_nodes=literal_nodes,
        literal_clock_control_nodes=control_nodes,path_edges=witnesses['path_edges'],
        terminal_child_edges=witnesses['local_Core_edges'],seconds=time.perf_counter()-start,
        scope='All public selected48histories, geometry checks, full target closure/rank binding, literal all-defense paths and independent finite-clock trees. No Player, private pickle, old graph scalar label or new trajectory. Source policy forecasts/execution/calibration not independently rerun here.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',type=Path,default=DEFAULT);cli.add_argument('--output',required=True)
    args=cli.parse_args();result=verify(args.directory);save(args.output,result);print(json.dumps(result))
