"""New structurally sampled3x3botharmed feasibilitypilot, no training."""
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
from results.dev_aux.task2048.portable_certificate import encode
from scripts.generic_session_native_material import _load_transport
from scripts.generic_win_proof import _same_state,_Interrupted
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2105.provider import TriggerProvider
from results.dev_aux.task2100.campaign import evaluate,reuse_role,sha_state
OUT=Path('results/dev_aux/task2128')
def write(name,data):
 with(OUT/name).open('x',encoding='utf-8')as f:json.dump(data,f,indent=2)
def run():
 if (OUT/'started.json').exists():raise RuntimeError('original240cap never restart')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());deadline=start+p['one_game_cap_seconds'];write('started.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=p['one_game_cap_seconds']));stop=_load_transport().stop_check
 stop_calls=0;stop_seconds=0.
 def cancelled():
  nonlocal stop_calls,stop_seconds
  began=time.perf_counter();stop(Path.cwd());stop_calls+=1;stop_seconds+=time.perf_counter()-began;return time.perf_counter()>=deadline
 roots=json.loads(Path('results/dev_aux/task2128/inputs.json').read_text())['roots'];compiled={f:compile_ruleset_for_execution(deserialize_ruleset(Path(roots[f]['rules']).read_text(encoding='utf-8')))for f in range(p['families'])};load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2093','results/dev_aux/task2094','results/dev_aux/task2095');teacherload=time.perf_counter()-load;provider=TriggerProvider(teacher);limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds']);games=[];physical={};status='COMPLETE';physicalcount=0;movecount=0
 with (OUT/'games.jsonl').open('x',encoding='utf-8')as jf,(OUT/'moves.jsonl').open('x',encoding='utf-8')as mf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for family in range(p['families']):
   if cancelled():status='GLOBAL_CAP';break
   for candidate in(0,1):
    conditions=[(r,'TRIGGER')for r in p['ratios']];offset=(family+candidate)%len(conditions);conditions=conditions[offset:]+conditions[:offset]
    for ratio,policy in conditions:
     logical=len(games);key=(family,ratio,policy,0 if ratio==1. else candidate)
     if key in physical:
      row=reuse_role(physical[key],candidate,logical);games.append(row);jf.write(json.dumps(row)+'\n');jf.flush();continue
     if cancelled():status='GLOBAL_CAP';break
     pid=physicalcount;physicalcount+=1;c=compiled[family];s=GameSession(c);players=[SessionCachedPhasePlayer(c,evaluate(ratio if side==candidate else 1.),bank=SessionLogicalProofBank(provider,capacity=256),limits=limits,proof_enabled=True,max_depth=p['normal_depth'],proof_depth=p['proof_depth'])for side in(0,1)];began=time.perf_counter();steps=0;reason='H_UNKNOWN'
     for ply in range(p['H']):
      if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
      if cancelled():status='GLOBAL_CAP';reason=status;break
      side=s.state.position.side_to_move;d=players[side].choose(s,max_nodes=p['normal_nodes'],seconds=p['step_seconds'],cancel=cancelled)
      if d.choice is None:reason=d.exit_cause;status='INCOMPLETE_OUTCOME';break
      if d.source=='PROOF':
       cert=players[side].cursor.certificate;cf.write(json.dumps(dict(physical_id=pid,ply=ply,target=side,ruleset_fingerprint=cert.ruleset_fingerprint,root_record=json.loads(serialize_game_record(cert.root_record)),tree=encode(cert.tree)))+'\n');cf.flush()
      before=sha_state(s.state)
      try:commit_session_decision(s,d,players,cancel=cancelled)
      except _Interrupted:status='GLOBAL_CAP';reason='cancelled_before_commit';break
      rp=GameSession.replay(c,s.to_record());assert _same_state(rp.state,s.state)and rp.result==s.result
      row=dict(physical_id=pid,logical_slot=logical,ply=ply,side=side,is_candidate=side==candidate,choice=action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,logical_status=d.logical_status,exit_cause=d.exit_cause,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,fill_verification_nodes=d.fill_verification_nodes,search_nodes=d.search_nodes,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,seconds=d.seconds,proof_seconds=d.proof_seconds,normal_seconds=d.normal_seconds,verification_seconds=d.verification_seconds,fill_verification_seconds=d.fill_verification_seconds,bank_query_seconds=d.bank_query_seconds,admission_seconds=d.admission_seconds,phase_limits=dict(d.phase_limits),before_state_sha=before,after_state_sha=sha_state(s.state),result=dict(status=s.result.status.value,winner=s.result.winner));mf.write(json.dumps(row)+'\n');mf.flush();steps+=1;movecount+=1
      if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
     result=s.result;outcome='UNKNOWN'if result.status is SessionStatus.ONGOING else'DRAW'if result.winner is None else'WIN'if result.winner==candidate else'LOSS';g=dict(logical_slot=logical,physical_id=pid,phase='EXPOSED_POPULATION_3X3_FEASIBILITY',family=family,ratio=ratio,candidate_side=candidate,candidate_policy=policy,opponent_ratio=1.,opponent_policy='TRIGGER',reused_from=None,outcome=outcome,score=None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else-1 if outcome=='LOSS'else 0,moves=steps,reason=reason,seconds=time.perf_counter()-began,result=dict(status=result.status.value,winner=result.winner),record=json.loads(serialize_game_record(s.to_record())),final_state_sha=sha_state(s.state));physical[key]=g;games.append(g);jf.write(json.dumps(g)+'\n');jf.flush();print(json.dumps(dict(logical=len(games),physical=physicalcount,moves=movecount,last=dict(family=family,ratio=ratio,candidate=candidate,policy=policy,outcome=outcome),seconds=time.perf_counter()-start)),flush=True)
     if outcome=='UNKNOWN':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 result=dict(status=status,logical_games=len(games),physical_games=physicalcount,moves=movecount,outcomes=dict(Counter(g['outcome']for g in games)),teacher_load_seconds=teacherload,teacher_prepaid_seconds=p['teacher_prepaid_seconds'],seconds=time.perf_counter()-start,selector=None,expected_logical=64,missing_logical=64-len(games),no_training=True,no_old_cap_restart=True,stop_check_calls=stop_calls,stop_check_seconds=stop_seconds)
 write('completion.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':run()
