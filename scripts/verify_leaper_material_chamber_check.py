"""Verify this finite study's saved literal PVs; never dispatch Player."""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--data',type=Path,required=True)
 args=p.parse_args(); path=args.data
 plan=json.loads((path/'plan.json').read_bytes())
 inputs=Path(plan['input']).read_bytes()
 assert sha256(inputs).hexdigest()==plan['input_sha256']
 worlds=json.loads(inputs)
 raw=(path/'queries.jsonl').read_bytes()
 rows=[json.loads(v) for v in raw.splitlines()]
 indexed={(r['world'],r['depth'],r['B']):r for r in rows}
 expected={(w,d,b) for w in plan['world_order'] for d in plan['depths'] for b in plan['B_weights']}
 assert len(indexed)==len(rows) and set(indexed)==expected
 compiled={}; plies=0
 for r in rows:
  w=worlds[r['world']]
  if r['world'] not in compiled:
   compiled[r['world']]=compile_ruleset_for_execution(ruleset_from_dict(w['rule']))
  c=compiled[r['world']]
  assert c.ruleset_fingerprint==w['fingerprint']
  assert all(v['kind']=='ACTION' and v['declaration_id'] is None for v in r['pv'])
  assert r['choice']==r['pv'][0] and len(r['pv'])==r['depth']
  record=dict(w['initial_record'])
  record['actions']=list(record['actions'])+[v['action'] for v in r['pv']]
  s=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
  assert s.result.status is SessionStatus.ONGOING
  assert all(not h.counts for h in s.state.position.hands)
  counts=Counter()
  for piece in s.state.position.board:
   if piece: counts[piece.current_type_id]+=1 if piece.owner==0 else -1
  phi=[counts['A'],counts['B'],0,0]
  assert r['pv_phi']==phi and not r['pv_terminal']
  assert r['value']==phi[0]+r['B']*phi[1]
  assert r['state_and_model_unchanged']
  assert sum(a['nodes'] for a in r['attempts'])==r['nodes']
  assert all(a['complete'] for a in r['attempts'])
  plies+=len(r['pv'])
 pairs=[]; cross=[]
 for w in plan['world_order']:
  for d in plan['depths']:
   x,y,z=indexed[w,d,.75],indexed[w,d,.875],indexed[w,d,1.25]
   qualified=all(v['complete'] and v['completed_depth']==d and v['reason']=='completed_depth' for v in [x,y])
   pairs.append(dict(world=w,depth=d,qualified=qualified,action_equal=x['choice']==y['choice'],PV_equal=x['pv']==y['pv'],nodes_equal=x['nodes']==y['nodes'],phi_equal=x['pv_phi']==y['pv_phi'],nodes=x['nodes']))
   cross.append(dict(world=w,depth=d,action_differs=x['choice']!=z['choice'],PV_differs=x['pv']!=z['pv'],nodes_differ=x['nodes']!=z['nodes'],scores=[x['value'],z['value']]))
 result=dict(raw_sha256=sha256(raw).hexdigest(),verifier_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),actual_calls=len(rows),PV_replayed=len(rows),PV_plies=plies,all_replayed_session_status='ONGOING',root_or_model_mutations=0,complete_requested=sum(r['complete'] and r['completed_depth']==r['depth'] and r['reason']=='completed_depth' for r in rows),paid_nodes=sum(r['nodes'] for r in rows),same_chamber_pairs=pairs,cross_chamber_pairs=cross,returned_PV_nonzero_B=sum(r['pv_phi'][1]!=0 for r in rows),terminal_PVs=sum(r['pv_terminal'] for r in rows),training_admitted='NOT_MEASURED: no episode/TD observer invoked',full_games=0,strength='NOT_MEASURED',scope='ten exposed owner0 default empty-record roots; three complete q0 depths, not random-opening or equal-wall quality',verification_note='Final verifier explicitly asserts SessionStatus.ONGOING; initial inline exploratory check conditionally skipped that assertion, not used as terminal qualification.')
 (path/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 (path/'verifier.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps({k:v for k,v in result.items() if not isinstance(v,list)},indent=2))
if __name__=='__main__': main()
