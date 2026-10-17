"""Unchanged R/N mechanics; rule-only dual-capture sparse initial distribution."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import random,json,time,datetime,hashlib
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from scripts.generic_proof_rnb_bridge import orbit,actor_state
OUT=Path('results/dev_aux/task2460')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd());rng=random.Random(856001);template=deserialize_ruleset(Path(p['template']).read_text());seen=set(json.loads((OUT/'excluded-orbits.json').read_text()));roots=[];attempts=[];reject=Counter();t=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cap=p['cap_seconds'])));
 for ix in range(p['max_attempts']):
  stop()
  if len(roots)==8 or time.perf_counter()-t>=p['cap_seconds']:break
  squares=rng.sample(range(16),6);flat=[None]*16
  for j,(owner,kind)in zip(squares,[(0,'K'),(1,'K'),(0,'R'),(0,'N'),(1,'R'),(1,'N')]):flat[j]=Piece(owner,kind,kind)
  rs=replace(template,initial_position=tuple(tuple(flat[i:i+4])for i in range(0,16,4)),initial_setup_options=());row=dict(attempt=ix,squares=squares)
  try:c=compile_ruleset_for_execution(rs)
  except ValueError as e:
   if 'INITIAL_ANCHOR_ATTACKED'not in str(e):raise
   row['rejection']='INITIAL_ANCHOR_ATTACKED';reject[row['rejection']]+=1;attempts.append(row);continue
  s=GameSession(c);legal=s.legal_actions();captures={k:[]for k in('R','N')}
  for a in legal:
   if not hasattr(a,'from_square'):continue
   victim=s.state.position.board[a.to_square.rank*4+a.to_square.file]
   if victim is not None and victim.owner==1 and victim.current_type_id==victim.base_type_id and victim.current_type_id in captures:captures[victim.current_type_id].append(a)
  pairs=[(a,b)for a in captures['R']for b in captures['N']if a.from_square==b.from_square]
  key=min(map(repr,orbit(actor_state(s.state))))
  reason='TERMINAL'if s.result.status is not SessionStatus.ONGOING else'NO_SAME_ACTOR_DUAL_CAPTURE'if not pairs else'DUPLICATE_INITIAL'if key in seen else None
  if reason:row['rejection']=reason;reject[reason]+=1;attempts.append(row);continue
  seen.add(key);i=len(roots);path=OUT/f'rules-{i}.json';path.write_text(serialize_ruleset(rs));roots.append(dict(index=i,family=i,rules=path.as_posix(),record=json.loads(serialize_game_record(s.to_record())),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),attempt=ix,partition='RESERVE',captures={k:[action_to_dict(a)for a in aa]for k,aa in captures.items()},same_actor_pairs=[[action_to_dict(a),action_to_dict(b)]for a,b in pairs],all_legal_actions=[action_to_dict(a)for a in legal]));row['admitted_index']=i;attempts.append(row)
 (OUT/'inputs.json').write_text(json.dumps(roots,indent=2));(OUT/'attempts.json').write_text(json.dumps(attempts,indent=2));r=dict(status='COMPLETE_FROZEN_DUAL_CAPTURE_CORPUS'if len(roots)==8 else'PARTIAL_NO_FITNESS',roots=len(roots),design=0,reserve=len(roots),attempts=len(attempts),rejections=dict(reject),seconds=time.perf_counter()-t,price_fitness_queries=0,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
