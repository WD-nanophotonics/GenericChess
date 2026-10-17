"""Independent rule-only new TRAIN admission and orbit separation, no fitness queries."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import json,hashlib,time
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_proof_rnb_bridge import orbit,actor_state
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2487')
def run():
 tick=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());folder=Path('results/dev_aux/task2480');p=json.loads((folder/'plan.json').read_text());roots=json.loads((folder/'inputs.json').read_text());attempts=json.loads((folder/'attempts.json').read_text());template=deserialize_ruleset(Path(p['template']).read_text());old=set()
 for task in(2439,2460):
  for root in json.loads(Path(f'results/dev_aux/task{task}/inputs.json').read_text()):
   s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())));old.add(min(map(repr,orbit(actor_state(s.state)))))
 assert len(old)==20 and old==set(json.loads((folder/'excluded-orbits.json').read_text()))
 admitted=[];seen=set(old)
 for row in attempts:
  stop();flat=[None]*16
  for j,(owner,kind)in zip(row['squares'],[(0,'K'),(1,'K'),(0,'R'),(0,'N'),(1,'R'),(1,'N')]):flat[j]=Piece(owner,kind,kind)
  rs=replace(template,initial_position=tuple(tuple(flat[i:i+4])for i in range(0,16,4)),initial_setup_options=())
  try:c=compile_ruleset_for_execution(rs)
  except ValueError as e:
   assert row.get('rejection')=='INITIAL_ANCHOR_ATTACKED' and 'INITIAL_ANCHOR_ATTACKED'in str(e);continue
  s=GameSession(c);legal=s.legal_actions();cap={k:[]for k in('R','N')}
  for a in legal:
   if not hasattr(a,'from_square'):continue
   v=s.state.position.board[a.to_square.rank*4+a.to_square.file]
   if v is not None and v.owner==1 and v.current_type_id==v.base_type_id and v.current_type_id in cap:cap[v.current_type_id].append(a)
  pairs=[(a,b)for a in cap['R']for b in cap['N']if a.from_square==b.from_square];key=min(map(repr,orbit(actor_state(s.state))))
  reason='TERMINAL'if s.result.status.value!='ongoing'else'NO_SAME_ACTOR_DUAL_CAPTURE'if not pairs else'DUPLICATE_INITIAL'if key in seen else None
  if reason:assert row['rejection']==reason;continue
  i=len(admitted);r=roots[i];assert row['admitted_index']==i and r['index']==i and r['attempt']==row['attempt'] and r['partition']=='TRAIN'
  assert deserialize_ruleset(Path(r['rules']).read_text())==rs
  assert r['record']==json.loads(serialize_game_record(s.to_record()))and r['state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()
  assert r['all_legal_actions']==[action_to_dict(a)for a in legal]
  assert r['same_actor_pairs']==[[action_to_dict(a),action_to_dict(b)]for a,b in pairs]
  seen.add(key);admitted.append(key)
 assert len(admitted)==16 and len(seen)==36
 r=dict(status='PASS_ALL602_RULE_ONLY_ATTEMPTS_NEW16TRAIN_AND36_DISJOINT_INITIAL_ORBITS',attempts=len(attempts),new_TRAIN=16,excluded_old_orbits=20,old8reserve_still_no_fitness_queries=True,seconds=time.perf_counter()-tick,scope='Rebuildeveryattemptfromsavedrandomsquares/publicCore, alllegaldualcapabilities/record/fullstate/canonicalD4color-sideorbit separation. No generator rerun/resampling orpricequery. Membership beforefitness andTRAINonly; source/restriction/caps maintained. No all-rule equivalence/defaultadoption.')
 (OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
