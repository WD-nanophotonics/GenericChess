"""Verify saved root subtrees against another full successor history; no search."""
from pathlib import Path
from dataclasses import replace
from copy import copy
from time import perf_counter
from unittest.mock import patch
import hashlib,json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate,execute
from scripts.research_record import record_value

def run(folder):
    folder=Path(folder);output=folder/'branch-observed.json'
    if output.exists():raise RuntimeError('fixed branch checks already executed; no refill')
    start=perf_counter();raw=(folder/'branch-protocol.json').read_bytes();proto=json.loads(raw)
    f=json.loads((folder/'repeat4-counterexample.json').read_bytes())
    observed=json.loads((folder/'observed.json').read_bytes())
    assert hashlib.sha256((folder/'observed.json').read_bytes()).hexdigest()==proto['source_observed_sha256']
    compiled=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(f['rule']))
    draw,win=sorted(f['rows'],key=lambda x:x['value'])
    d=GameSession.replay(compiled,deserialize_game_record(json.dumps(draw['record'])))
    w,cert=decode_session_certificate(compiled,win['win_certificate'],max_nodes=8192)
    assert len(cert.tree.edges)==proto['budget']['subtree_verifications']==4
    safe=observed['matched_root_policy']['common_certified_optimal_action']
    results=[];submits=0
    original=GameSession.submit
    def counted(s,a):
        nonlocal submits
        submits+=1
        return original(s,a)
    with patch.object(GameSession,'submit',counted):
        for choice,tree in cert.tree.edges:
            dc,wc=copy(d),copy(w)
            execute(dc,choice);execute(wc,choice)
            assert dc.state.position==wc.state.position
            rebound=replace(cert,root_record=dc.to_record(),root_state=dc.state,tree=tree)
            check=verify_session_certificate(dc,rebound,max_nodes=8192,seconds=5.)
            wire=action_to_dict(choice.action)
            if wire==safe and check['verified']:raise RuntimeError('contradictory accepted existing proofs')
            results.append(dict(action=wire,source_rank=tree.rank,
                successor_terminal=dc.result.status.value,
                same_successor_Position=True,same_successor_full_state=dc.state==wc.state,
                verified_check=check,
                child_value_for0_bounds=[1,1]if check['verified']else[-1,1],
                root_actor1_regret_bounds=[1,1]if check['verified']else[0,1],
                classification='CERTIFIED_LOSS'if check['verified']else'UNKNOWN'))
    elapsed=perf_counter()-start
    if elapsed>30:raise RuntimeError('whole cap exceeded; no rerun')
    out=dict(protocol_sha256=hashlib.sha256(raw).hexdigest(),rows=results,
        verified_loss_actions=sum(x['classification']=='CERTIFIED_LOSS'for x in results),
        unknown_actions=sum(x['classification']=='UNKNOWN'for x in results),
        actual_GameSession_submit_calls=submits,
        whole_wall_seconds=elapsed,new_Player_calls=0,new_solver_calls=0,
        limits='Existing exposed tree transfer only; rejecting a tree does not refute another WIN strategy. Initial prefix replays/decode before counter are excluded from submit count and reported separately.',
        initial_prefix_replay_actions=2*11)
    output.write_text(json.dumps(record_value(out),indent=2)+'\n',encoding='utf8')
    return out
