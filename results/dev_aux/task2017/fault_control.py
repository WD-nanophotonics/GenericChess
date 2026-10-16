"""Actual Session/player cancellation and None-result controls; no utility adoption."""
from pathlib import Path
import json,ast,hashlib,time
from dataclasses import asdict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
from scripts.generic_session_proof_player import commit_session_decision
from results.dev_aux.task2016.campaign import scheduled_slots,CampaignCap
OUT=Path('results/dev_aux/task2017')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def run():
 start=time.perf_counter();old=read('results/dev_aux/task2014/result.json');plan=read('results/dev_aux/task1997/run-plan.json')
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
 record=deserialize_game_record(json.dumps(old['counterexample']['prefix_record']))
 filt=SetupTransportedNoWinFilter('results/dev_aux/task1895','results/dev_aux/task1896/coverage.json',c)
 source=Path('results/dev_aux/task2016/campaign.py').read_text(encoding='utf-8');tree=ast.parse(source)
 # Execute the EXACT frozen producer's outcome/score assignments, not a parallel scorer.
 assignments=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('outcome','score')]
 assert len(assignments)==2
 score_code=compile(ast.Module(body=assignments,type_ignores=[]),'frozen2016-outcome-assignments','exec')
 def actual_score(s):
  env=dict(result=s.result,SessionStatus=SessionStatus,slot={'candidate_side':0});exec(score_code,env);return dict(outcome=env['outcome'],score=env['score'])
 controls=[]
 for mode in ('NORMAL_RETURNS_NONE','CANCEL_BEFORE_DECISION'):
  s=GameSession.replay(c,record);assert filt.eligible(s);before=serialize_game_record(s.to_record());calls=[]
  def missing(state,n,seconds,cancel):calls.append('None');return None,0
  player=SessionCachedPhasePlayer(c,lambda p,t:0,bank=SessionLogicalProofBank(filt),normal_search=missing,limits=PhaseLimits(proof_nodes=1024),max_depth=3)
  d=player.choose(s,max_nodes=4096,seconds=2.75,cancel=(lambda:True) if mode=='CANCEL_BEFORE_DECISION' else None)
  assert d.choice is None and serialize_game_record(s.to_record())==before and s.result.status is SessionStatus.ONGOING
  score=actual_score(s);assert score==dict(outcome='UNKNOWN',score=None)
  # Real production selector must reject this observed incomplete training outcome.
  temp=OUT/mode;temp.mkdir(exist_ok=False);rows=[]
  generator=scheduled_slots(dict(prices=[360,720,1440,2880],train_opponent_R=[360,720,1440,2880]*4),rows,temp,lambda:False)
  slot=next(generator);rows.append(dict(slot,outcome=score['outcome'],finite_event_score=score['score'],seconds=d.seconds))
  try:next(generator)
  except CampaignCap:pass
  else:raise AssertionError('Actual selector accepted UNKNOWN')
  assert not list(temp.iterdir())
  controls.append(dict(mode=mode,choice=None,exit_cause=d.exit_cause,source=d.source,callback_calls=calls,logical_status=d.logical_status,logical_reason=d.logical_reason,score=score,record_unchanged=True,selector_rejected=True))
 # Separate explicitly fixed legal-progress policy, NOT the study's Native policy.
 # This demonstrates sufficiency of real progress, not Native timeout immunity.
 s=GameSession.replay(c,record);trace=[]
 def first_legal(state,n,seconds,cancel):return GameSession.replay(c,s.to_record()).legal_actions()[0],0
 players=[SessionCachedPhasePlayer(c,lambda p,t:0,bank=SessionLogicalProofBank(filt),normal_search=first_legal,limits=PhaseLimits(proof_nodes=1024),max_depth=3) for _ in (0,1)]
 while s.result.status is SessionStatus.ONGOING:
  assert time.perf_counter()-start<30
  before=len(s.to_record().actions);d=players[s.state.position.side_to_move].choose(s,max_nodes=4096,seconds=2.75)
  assert d.choice is not None;commit_session_decision(s,d,players)
  assert len(s.to_record().actions)==before+1
  trace.append(dict(ply=before,source=d.source,logical_status=d.logical_status,logical_reason=d.logical_reason,status=s.result.status.value))
 assert s.result.winner is None and actual_score(s)==dict(outcome='DRAW',score=0)
 result=dict(status='PASS_REAL_PLAYER_FAULT_AND_PROGRESS_CONTROLS',controls=controls,normal_progress=dict(policy='FIRST_PUBLIC_LEGAL_ACTION, explicitly different from Native study policy',new_moves=len(trace),trace=trace,result={**asdict(s.result),'status':s.result.status.value},record=json.loads(serialize_game_record(s.to_record())),score=actual_score(s)),input_record=json.loads(serialize_game_record(record)),seconds=time.perf_counter()-start,source_sha={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['results/dev_aux/task2016/campaign.py',Path(__file__).relative_to(Path.cwd()).as_posix(),'scripts/generic_session_cached_phase_player.py','scripts/generic_inventory_proof_transport.py']},scope='Injected normal None and actual cancellation through real cached player, exact producer scoring AST and actual TRAIN selector. No Native/prover execution, no whole campaign fault injection; no reward/certificate/Sessionstatus adoption. Interruptions remain UNKNOWN/unscored. Legal-progress control reaches real DRAW but does not prove arbitrary runtime always progresses.')
 with(OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ('normal_progress','input_record','source_sha')}))
if __name__=='__main__':run()
