"""Rule-only seeded actual-history corpus, BEFORE all coefficient queries."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import random,json,time,datetime,hashlib
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
from generic_chess.core.actions import action_to_dict
from results.dev_aux.task2400.qualify import definition
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2435')
def run():
 assert not(OUT/'started.json').exists();q=json.loads((OUT/'question.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop();rng=random.Random(853501);base=definition('consume');knight=PieceType('N','N',tuple(LeapAtom(x)for x in((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1))));template=replace(base,piece_types=base.piece_types+(knight,),initial_setup_options=(),drop_allowed={**base.drop_allowed,'N':tuple(tuple(False for _ in range(16))for _ in range(2))});roots=[];seen=set();t=time.perf_counter();rejections=Counter();attempts=[]
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cap=q['caps']['generation_seconds'],source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())))
 for attempt in range(q['caps']['generation_attempts']):
  stop()
  if len(roots)>=16 or time.perf_counter()-t>=q['caps']['generation_seconds']:break
  squares=rng.sample(range(16),6);flat=[None]*16
  for ix,(owner,kind)in zip(squares,[(0,'K'),(1,'K'),(0,'P'),(1,'R'),(0,'N'),(0,'R')]):flat[ix]=Piece(owner,kind,kind)
  rs=replace(template,initial_position=tuple(tuple(flat[i:i+4])for i in range(0,16,4)));row=dict(attempt=attempt,squares=squares,prefix=[])
  try:c=compile_ruleset_for_execution(rs)
  except ValueError as e:
   if 'INITIAL_ANCHOR_ATTACKED'not in str(e):raise
   row['rejection']='INITIAL_ANCHOR_ATTACKED';attempts.append(row);rejections[row['rejection']]+=1;continue
  s=GameSession(c)
  for k in range(6):
   stop()
   if s.result.status is not SessionStatus.ONGOING:break
   legal=s.legal_actions()
   if not legal:break
   a=legal[rng.randrange(len(legal))];s.submit(a);row['prefix'].append(action_to_dict(a))
  reason='ACTUAL_TERMINAL'if s.result.status is not SessionStatus.ONGOING else'LESS_THAN_TWO_CHOICES'if len(s.legal_actions())<2 else'NO_REAL_HELD_R'if not any(dict(h.counts).get('R',0)for h in s.state.position.hands)else'NO_SURVIVING_CURRENT_R'if not any(pc is not None and pc.current_type_id=='R'for pc in s.state.position.board)else None
  # Ignore fingerprint for cross-layout structural duplicate detection; preserve full state otherwise.
  key=repr((s.state.position.board,s.state.position.hands,s.state.position.side_to_move,s.state.position.aux_state))
  if reason is None and key in seen:reason='DUPLICATE_COMPLETE_POSITION_PROJECTION'
  if reason:row['rejection']=reason;rejections[reason]+=1;attempts.append(row);continue
  seen.add(key);i=len(roots);path=OUT/f'rules-{i}.json';path.write_text(serialize_ruleset(rs));roots.append(dict(index=i,family=i,rules=path.as_posix(),record=json.loads(serialize_game_record(s.to_record())),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),attempt=attempt,partition='TRAIN'if i<8 else'RESERVE',structural_key=key));row['admitted_index']=i;attempts.append(row)
 (OUT/'inputs.json').write_text(json.dumps(roots,indent=2));(OUT/'generation-attempts.json').write_text(json.dumps(attempts,indent=2));out=dict(status='COMPLETE_PREFIT_CORPUS'if len(roots)==16 else'PARTIAL_CORPUS_NO_QUERY',roots=len(roots),train=min(len(roots),8),reserve=max(0,len(roots)-8),attempts=len(attempts),rejections=dict(rejections),seconds=time.perf_counter()-t,scope=q['scope'],fitness_queries=0)
 (OUT/'completion.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
