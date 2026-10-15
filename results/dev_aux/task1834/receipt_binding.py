"""Bind every actual mature query to independently replayed full public history.

Closes a specific receipt-audit gap: the earlier audit matched slots, moves,
prices and node budgets, but did not independently compare the entire sent
position command / complete record string with each actual before-state.
No new search or game; original records/auditor/results remain immutable.
"""
from pathlib import Path
from collections import defaultdict
import json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci

def rows(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines()]
start=time.perf_counter();folder=Path('results/dev_aux/task1825');plan=json.loads((folder/'plan.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));roots=json.loads(Path(plan['roots']).read_text())['roots'];games=rows(folder/'games.jsonl');moves=rows(folder/'moves.jsonl');by=defaultdict(list)
for step in moves:by[step['slot']].append(step)
expected=[];actor=RoyalActor(4)
for game in games:
    s=GameSession(c,roots[game['family']]['setup']);root_fen=actor.fen(actor_state(s.state));prefix=[]
    for step in by[game['slot']]:
        if step['source']=='EXTERNAL_SEARCH':
            expected.append(dict(slot=step['slot'],ply=step['ply'],position='position fen '+root_fen+(' moves '+' '.join(prefix) if prefix else ''),record=repr(s.to_record()),R=game['R'] if step['side']==game['candidate_side'] else 720))
        actual={uci(a):a for a in s.legal_actions()};encoded=step['choice'];text=chr(97+encoded['from'][0])+str(encoded['from'][1]+1)+chr(97+encoded['to'][0])+str(encoded['to'][1]+1) if 'from' in encoded else None
        if text is None:
            from generic_chess.session.serialization import deserialize_game_record
            raw={'schema_version':1,'ruleset_fingerprint':c.ruleset_fingerprint,'actions':[encoded],'resigned_by':None};action=deserialize_game_record(json.dumps(raw)).actions[0];text=uci(action)
        s.submit(actual[text]);prefix.append(text)
events=rows(folder/'run/transport.jsonl');profile=None;intents=[];acks=0;clears=0;options={}
for event in events:
    if event['event']=='OPTION':
        options[event['name']]=event['value'];assert not any('No such option' in line or 'Unknown command' in line for line in event['raw'])
    elif event['event']=='PROFILE':
        profile=event['R'];line=f'info string DEV_AUX leafRNBP {profile} 720 720 720 nativeP 720 nativeR {profile} nativeN 720 nativeB 720 captureP 720 captureR {profile} captureN 720 captureB 720';assert line in event['ack'];acks+=1
    elif event['event']=='CLEAR':assert profile==event['R'] and 'readyok' in event['raw'];clears+=1
    elif event['event']=='INTENT':
        index=len(intents);actual=expected[index]
        assert event['query']==index and event['R']==profile==actual['R']
        assert event['position']==actual['position'] and event['root_record']==actual['record']
        intents.append(event)
assert len(intents)==len(expected)==4421 and acks+clears==4421
assert options['Threads']==1 and options['Hash']==16 and options['Use NNUE']=='false' and options['SyzygyPath']=='<empty>'
result=dict(status='PASS_ALL_NATIVE_POSITION_HISTORY_AND_PROFILE_BINDINGS',queries=len(intents),actual_full_root_plus_prefix_commands=len(intents),actual_full_record_strings=len(intents),exact_profile_acks=acks,cold_clears=clears,options=options,seconds=time.perf_counter()-start,new_native_go=0,new_games=0,scope='Independent complete actual before-record/rootFEN/actionprefix/role-price binding against saved Native INTENT; no raw-log source or oldresult rewrite.')
with Path('results/dev_aux/task1834/result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
