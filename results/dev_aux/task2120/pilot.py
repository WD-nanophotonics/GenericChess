"""New fixed-opponent candidate-only negativefilter price/control pilot, no training."""
from pathlib import Path
from collections import Counter
import json,time,hashlib,datetime
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
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_native_material import _load_transport
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2072.no_win_filter import CompleteGraphNoWinFilter
from results.dev_aux.task2100.campaign import evaluate,reuse_role,sha_state
OUT=Path('results/dev_aux/task2120')
def write(name,data):
 with(OUT/name).open('x',encoding='utf-8')as f:json.dump(data,f,indent=2)
def run():
 if (OUT/'started.json').exists():raise RuntimeError('original2700cap never restart')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());deadline=start+p['one_cap_seconds'];write('started.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=p['one_cap_seconds']));stop=_load_transport().stop_check
 def cancelled():stop(Path.cwd());return time.perf_counter()>=deadline
 roots=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];compiled={f:compile_ruleset_for_execution(deserialize_ruleset(Path(roots[f]['rules']).read_text(encoding='utf-8')))for f in p['families']};load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');teacherload=time.perf_counter()-load;provider=CompleteGraphNoWinFilter(teacher);limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds']);games=[];physical={};status='COMPLETE';physicalcount=0;movecount=0
 with (OUT/'games.jsonl').open('x',encoding='utf-8')as jf,(OUT/'moves.jsonl').open('x',encoding='utf-8')as mf:
  for family in p['families']:
   if cancelled():status='GLOBAL_CAP';break
   for candidate in(0,1):
    conditions=[(r,n)for r in p['ratios']for n in p['policies']];offset=(family+candidate)%len(conditions);conditions=conditions[offset:]+conditions[:offset]
    for ratio,policy in conditions:
     logical=len(games);key=(family,ratio,policy,0 if ratio==1. and policy=='PN'else candidate)
     if key in physical:
      row=reuse_role(physical[key],candidate,logical);games.append(row);jf.write(json.dumps(row)+'\n');jf.flush();continue
     if cancelled():status='GLOBAL_CAP';break
     pid=physicalcount;physicalcount+=1;c=compiled[family];s=GameSession(c);players=[SessionCachedPhasePlayer(c,evaluate(ratio if side==candidate else 1.),bank=SessionLogicalProofBank(provider if side==candidate and policy=='NEGATIVE_FILTER'else prove_session_win_batch_pn,capacity=256),limits=limits,proof_enabled=True,max_depth=p['normal_depth'],proof_depth=p['proof_depth'])for side in(0,1)];began=time.perf_counter();steps=0;reason='H_UNKNOWN'
     for ply in range(p['H']):
      if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
      if cancelled():status='GLOBAL_CAP';reason=status;break
      side=s.state.position.side_to_move;d=players[side].choose(s,max_nodes=p['normal_nodes'],seconds=p['step_seconds'],cancel=cancelled)
      if d.choice is None:reason=d.exit_cause;status='INCOMPLETE_OUTCOME';break
      before=sha_state(s.state);commit_session_decision(s,d,players,cancel=cancelled);rp=GameSession.replay(c,s.to_record());assert _same_state(rp.state,s.state)and rp.result==s.result
      row=dict(physical_id=pid,logical_slot=logical,ply=ply,side=side,is_candidate=side==candidate,choice=action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,logical_status=d.logical_status,exit_cause=d.exit_cause,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,fill_verification_nodes=d.fill_verification_nodes,search_nodes=d.search_nodes,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,seconds=d.seconds,proof_seconds=d.proof_seconds,normal_seconds=d.normal_seconds,phase_limits=dict(d.phase_limits),before_state_sha=before,after_state_sha=sha_state(s.state),result=dict(status=s.result.status.value,winner=s.result.winner));mf.write(json.dumps(row)+'\n');mf.flush();steps+=1;movecount+=1
      if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
     result=s.result;outcome='UNKNOWN'if result.status is SessionStatus.ONGOING else'DRAW'if result.winner is None else'WIN'if result.winner==candidate else'LOSS';g=dict(logical_slot=logical,physical_id=pid,phase='EXPOSED_TRAIN_FIXED_OPPONENT_PILOT',family=family,ratio=ratio,candidate_side=candidate,candidate_policy=policy,opponent_ratio=1.,opponent_policy='PN',reused_from=None,outcome=outcome,score=None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else-1 if outcome=='LOSS'else 0,moves=steps,reason=reason,seconds=time.perf_counter()-began,result=dict(status=result.status.value,winner=result.winner),record=json.loads(serialize_game_record(s.to_record())),final_state_sha=sha_state(s.state));physical[key]=g;games.append(g);jf.write(json.dumps(g)+'\n');jf.flush();print(json.dumps(dict(logical=len(games),physical=physicalcount,moves=movecount,last=dict(family=family,ratio=ratio,candidate=candidate,policy=policy,outcome=outcome),seconds=time.perf_counter()-start)),flush=True)
     if outcome=='UNKNOWN':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 result=dict(status=status,logical_games=len(games),physical_games=physicalcount,moves=movecount,outcomes=dict(Counter(g['outcome']for g in games)),teacher_load_seconds=teacherload,teacher_prepaid_seconds=p['teacher_prepaid_seconds'],seconds=time.perf_counter()-start,selector=None,expected_logical=32,missing_logical=32-len(games),no_training=True,no_old_cap_restart=True)
 write('completion.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':run()
