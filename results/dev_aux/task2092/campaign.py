"""New144game frozen evaluator control with identical qualified proof provider.

Existing2063cap/results stay untouched. Complete teacher was pretrained; this
is actual scoped policy comparison, not a free universal solver.
"""
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import json,hashlib,time,datetime
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
from scripts.generic_win_proof import _same_state
from scripts.generic_session_native_material import _load_transport
from results.dev_aux.task2082.pairs import augmented as features
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2088.provider import CompositeProvider
OUT=Path('results/dev_aux/task2092')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with(OUT/n).open('x',encoding='utf-8')as f:json.dump(d,f,indent=2)
def rawposition(pos):return tuple('.' if p is None else p.current_type_id.lower() if p.owner else p.current_type_id for p in pos.board)+(pos.side_to_move,)
def evaluator(weights):
 def evaluate(pos,target):
  ids,vals=features(rawposition(pos));value=sum(weights[i]*v for i,v in zip(ids,vals))*720
  assert abs(value)<100000
  return value if pos.side_to_move==target else -value
 return evaluate

def run():
 if (OUT/'start.json').exists():raise RuntimeError('Original2092cap already started, no restart')
 t=time.perf_counter()
 p=json.loads((OUT/'run-plan.json').read_text());assert all(sha(k)==v for k,v in p['source_sha'].items());models=json.loads(Path(p['models']).read_text());transport=_load_transport();done=[];moves_count=0;status='COMPLETE'
 write('start.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),one_clock=True,cap_seconds=p['seconds_cap'],restart_forbidden=True))
 compiled={r['family']:compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()))for r in p['roots']};load_start=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074');filters={f:CompositeProvider(teacher) for f in compiled};teacher_load_seconds=time.perf_counter()-load_start
 def cancelled():
  transport.stop_check(Path.cwd());return time.perf_counter()-t>=p['seconds_cap']
 limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds'])
 with(OUT/'games.jsonl').open('x',encoding='utf-8')as games,(OUT/'moves.jsonl').open('x',encoding='utf-8')as moves:
  for slot in p['slots']:
   if cancelled():status='GLOBAL_CAP';break
   c=compiled[slot['family']];session=GameSession(c);players=[]
   for side in(0,1):
    name=slot['model'] if side==slot['candidate_side']else slot['opponent_model'];players.append(SessionCachedPhasePlayer(c,evaluator(models[name]),bank=SessionLogicalProofBank(filters[slot['family']],capacity=256),limits=limits,proof_enabled=True,max_depth=p['normal_depth'],proof_depth=p['proof_depth']))
   beg=time.perf_counter();steps=[];reason='H_UNKNOWN'
   for ply in range(p['H']):
    if session.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
    if cancelled():status='GLOBAL_CAP';reason='GLOBAL_CAP';break
    side=session.state.position.side_to_move;d=players[side].choose(session,max_nodes=p['normal_nodes'],seconds=p['step_seconds'],cancel=cancelled)
    if d.choice is None:reason=d.exit_cause;status='INCOMPLETE_OUTCOME';break
    before=sha_state(session.state);ranks=[None if x.cursor is None else x.cursor.node.rank for x in players];commit_session_decision(session,d,players,cancel=cancelled)
    rebuilt=GameSession.replay(c,session.to_record());assert _same_state(rebuilt.state,session.state) and _same_state(rebuilt.result,session.result)
    data=dict(slot=slot['slot'],ply=ply,side=side,choice=action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,exit_cause=d.exit_cause,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,search_nodes=d.search_nodes,phase_limits=dict(d.phase_limits),seconds=d.seconds,proof_seconds=d.proof_seconds,normal_seconds=d.normal_seconds,bank_hit=d.bank_hit,fill_verification_nodes=d.fill_verification_nodes,before_ranks=ranks,after_ranks=[None if x.cursor is None else x.cursor.node.rank for x in players],before_state_sha=before,after_state_sha=sha_state(session.state),result=dict(status=session.result.status.value,winner=session.result.winner))
    moves.write(json.dumps(data)+'\n');moves.flush();steps.append(data);moves_count+=1
    if session.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
   result=session.result;outcome='UNKNOWN' if result.status is SessionStatus.ONGOING else 'DRAW' if result.winner is None else 'WIN' if result.winner==slot['candidate_side']else'LOSS';score=1 if outcome=='WIN'else -1 if outcome=='LOSS'else 0 if outcome=='DRAW'else None
   row=dict(**slot,outcome=outcome,score=score,moves=len(steps),reason=reason,seconds=time.perf_counter()-beg,result=dict(status=result.status.value,winner=result.winner),record=json.loads(serialize_game_record(session.to_record())),final_state_sha=sha_state(session.state));games.write(json.dumps(row)+'\n');games.flush();done.append(row)
   if len(done)%12==0:print(json.dumps(dict(done=len(done),moves=moves_count,seconds=time.perf_counter()-t)),flush=True)
   if outcome=='UNKNOWN':status='INCOMPLETE_OUTCOME'if status=='COMPLETE'else status;break
 if time.perf_counter()-t>=p['seconds_cap']:status='GLOBAL_CAP'
 write('completion.json',dict(teacher_load_seconds=teacher_load_seconds,status=status,completed=len(done),expected=p['expected_games'],moves=moves_count,seconds=time.perf_counter()-t,source_unchanged=all(sha(k)==v for k,v in p['source_sha'].items()),outcomes=dict(Counter(g['outcome']for g in done))))
 print(json.dumps(dict(status=status,done=len(done),seconds=time.perf_counter()-t)),flush=True)
def sha_state(s):return hashlib.sha256(repr(s).encode()).hexdigest()
if __name__=='__main__':run()
