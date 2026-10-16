from pathlib import Path
from collections import Counter
from copy import copy
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from generic_chess.core.actions import action_to_dict
from results.dev_aux.task2376.material import material as shared
from results.dev_aux.task2397.material import material as separate
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2396')
def board_key(s):return(s.state.position.board,s.state.position.side_to_move,s.state.position.aux_state)
def action_key(a):return json.dumps(action_to_dict(a),sort_keys=True)
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();f=Path('results/dev_aux/task2385');roots=json.loads((f/'inputs.json').read_text());games=list(map(json.loads,(f/'games.jsonl').read_text().splitlines()));sample=[g for g in games if roots[g['root']]['variant']!='HAND_WITH_DROPS'];states=edges=scores=0;counterexamples=[];families=set()
 for game in sample:
  family=roots[game['root']]['family'];families.add(family);defs=[deserialize_ruleset(Path(roots[i*8+family]['rules']).read_text())for i in(0,1)];assert all(not d.semantic_actions and not any(t.is_promotable for t in d.piece_types)for d in defs);sessions=[GameSession(compile_ruleset_for_execution(d))for d in defs];anchors=frozenset(t.type_id for t in defs[0].piece_types if t.is_anchor);initial=[Counter(pc.current_type_id for pc in sessions[0].state.position.board if pc is not None and pc.owner==owner and pc.current_type_id not in anchors)for owner in(0,1)]
  for action in[None]+list(deserialize_game_record(json.dumps(game['record'])).actions):
   stop()
   if action is not None:
    for s in sessions:s.submit(action)
   a,b=sessions;assert board_key(a)==board_key(b)and a.result.status==b.result.status and a.result.winner==b.result.winner;la=sorted(a.legal_actions(),key=action_key)if a.result.status is SessionStatus.ONGOING else[];lb=sorted(b.legal_actions(),key=action_key)if b.result.status is SessionStatus.ONGOING else[];assert list(map(action_key,la))==list(map(action_key,lb));states+=1
   for owner in(0,1):
    current=Counter(pc.current_type_id for pc in b.state.position.board if pc is not None and pc.owner==1-owner and pc.current_type_id not in anchors);expected=initial[1-owner]-current;assert dict(b.state.position.hands[owner].counts)==dict(expected)
   for x,y in zip(la,lb):
    ca,cb=copy(a),copy(b);ca.submit(x);cb.submit(y);assert board_key(ca)==board_key(cb)and ca.result.status==cb.result.status and ca.result.winner==cb.result.winner;edges+=1
   for ratio in(1.,1.5):
    prices={t.type_id:(ratio if t.type_id=='R'else 1.)for t in defs[0].piece_types if not t.is_anchor};zero={t:0. for t in prices}
    for target in(0,1):
     original=shared(a.state.position,target,prices,excluded_type_ids=anchors);dormant=shared(b.state.position,target,prices,excluded_type_ids=anchors);corrected=separate(b.state.position,target,prices,zero,excluded_type_ids=anchors);assert original==corrected;assert separate(b.state.position,target,prices,prices,excluded_type_ids=anchors)==dormant;scores+=2
     if original!=dormant and len(counterexamples)<12:counterexamples.append(dict(family=family,slot=game['slot'],ply=a.state.ply_count,target=target,ratio=ratio,board_projection_equal=True,actual_terminal_equal=True,legal_choices=len(la),removal_score=original,dormant_hand_shared_price_score=dormant,explicit_zero_hand_score=corrected,hands=[dict(h.counts)for h in b.state.position.hands]))
 result=dict(status='PASS_DORMANT_HAND_VALUE_COUNTEREXAMPLE_AND_DUAL_CHANNEL_QUALIFICATION',source='ONLY19closed2385records frombeforefault; excludeWITH_DROPSbyruleclass, no ongoing2394fitnessread',games=len(sample),families=sorted(families),paired_history_states=states,paired_actual_legal_children=edges,score_equalities=scores,counterexamples=counterexamples,seconds=time.perf_counter()-start,derivation='For this no-promotion/no-drop/no-hand-guard simplelegacydomain, capturedhand counts are determined by initial opponentinventory minus survivingopponentboardtypes. Hands neverreenter/affectlegaltransitions; thisdeterministicliftpreservesboardrepetitionequality andfinitehorizonterminal. Pairedactualhistory/childchecks support onlythisclass, notallgeneratedrules.',scope='2397explicitboard/handpricechannels only, noautomaticallyzeroinghandsfromdropmaskingeneral: semanticguards/triggers/declarations mayusehands. Current2385/2394sharedpricecallbackunchanged;HAND_NO_DROPSisanadversarialrepresentationcontrol notvalidatedgenericmaterialaxiom. No human/WDLfit/newsearch/newgame/default/PRIMARYadoption. Equalchannelmaps reproduce2376; dormanthand0reproducesremovalscore on pairedsample. Materialequalitynotcompletepositionalvalue.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='counterexamples'}));print(json.dumps(counterexamples[:2]))
if __name__=='__main__':run()
