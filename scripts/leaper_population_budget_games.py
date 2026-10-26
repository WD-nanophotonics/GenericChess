"""Actual original-Player resource-contrast games, frozen inputs and no labels."""
from __future__ import annotations
import argparse,json,hashlib,time
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json,write_json

def stamp():return datetime.now(timezone.utc).isoformat()
def record_hash(record):return hashlib.sha256(json.dumps(record_value(record),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def frozen_deadline(plan):return datetime.fromisoformat(plan['whole_deadline_utc'])
def stop_reason(plan,tick,attempts):
 state=read_json(Path('.local_agent/rollout.json'))
 if any(state.get(k,False)for k in ['user_paused','research_stopped','stop_requested']):return 'scoped_user_research_stop'
 if time.perf_counter()-tick>=plan['max_batch_seconds']:return 'batch_cap'
 if datetime.now(timezone.utc)>=frozen_deadline(plan):return 'whole_chain_cap'
 if attempts>=plan['max_Player_attempts']:return 'attempt_cap'
 return None

def run(inputs,plan_file,output):
 assert not output.exists();output.mkdir(parents=True);(output/'returns').mkdir()
 plan=read_json(plan_file);all_inputs=read_json(inputs)['rows'];roots=[r for r in all_inputs if r['prefix_length']==2]
 assert len(roots)==12 and len({r['fingerprint']for r in roots})==12
 write_record(output/'executed-source.json',{'driver':Path(__file__).read_bytes().decode(),'input_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(plan_file.read_bytes()).hexdigest(),'root_ids':[r['id']for r in roots]})
 tick=time.perf_counter();started=stamp();games=[];attempts=0;halt=None;call_cpu=0.;call_wall=0.;measurement_start=None
 for ri,row in enumerate(roots):
  for long_seat in [0,1]:
   game={'game_id':len(games),'case_id':row['id'],'fingerprint':row['fingerprint'],'long_seat':long_seat,'initial_record':row['record'],'status':'NOT_STARTED','queries':[]}
   halt=halt or stop_reason(plan,tick,attempts)
   if halt:game['reason']=halt;games.append(game);continue
   tgame=time.perf_counter();game_cpu=time.process_time();start_game=stamp()
   try:
    c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(row['RuleSet']));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
    players={};construction={}
    for seat in [0,1]:
     tp=time.perf_counter();players[seat]=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True);construction[str(seat)]=time.perf_counter()-tp
    game.update(status='RUNNING',started_at=start_game,constructor_seconds=construction,setup_seconds=time.perf_counter()-tgame)
    while not s.state.terminal_status.is_terminal:
     halt=stop_reason(plan,tick,attempts)
     if halt:break
     if len(game['queries'])>=plan['per_game_turn_cap']:
      halt='per_game_caller_cap';break
     seat=s.state.position.side_to_move;policy='long'if seat==long_seat else'short';budget=plan['policies'][policy]['seconds'];before=s.to_record();qid=attempts;attempts+=1;u0=stamp();t0=time.perf_counter();cpu0=time.process_time()
     if measurement_start is None:measurement_start=u0
     try:
      decision=players[seat].choose_action(s,SearchLimits(max_depth=64,max_nodes=500000,max_time_seconds=budget,quiescence_max_depth=4,quiescence_hard_max_depth=8))
      u1=stamp();wall=time.perf_counter()-t0;cpu=time.process_time()-cpu0;call_cpu+=cpu;call_wall+=wall
      q={'query_id':qid,'game_id':game['game_id'],'case_id':row['id'],'ply_before':s.state.ply_count,'seat':seat,'policy':policy,'requested_seconds':budget,'record_before_sha256':record_hash(before),'decision':record_value(decision),'started_at':u0,'ended_at':u1,'choose_wall_seconds':wall,'choose_cpu_seconds':cpu,'timing_eligible':wall<=budget+max(.025,.10*budget)}
      # Preserve actual successful return before validation or executing its move.
      write_record(output/'returns'/f'{qid:04d}.json',q)
      assert s.to_record()==before,'query mutated session root'
      assert decision.action is not None,'missing action on ongoing state'
      assert decision.action in s.legal_actions(),'illegal decision'
      # Full PV is replayed on a separate session, not on the actual game path.
      pv=GameSession.replay(c,before)
      for a in decision.principal_variation:pv.submit(a)
      s.submit(decision.action)
      q.update(validated_root_unchanged=True,pv_legal=True,record_after_sha256=record_hash(s.to_record()))
      game['queries'].append(q)
      write_record(output/f'game-{game["game_id"]:02d}-queries.json',game['queries'])
      write_json(output/'progress.json',{'at':stamp(),'active_game':game['game_id'],'case_id':row['id'],'long_seat':long_seat,'attempts':attempts,'game_turns':len(game['queries']),'completed_games':len(games),'seconds':time.perf_counter()-tick,'Player_cpu_seconds':call_cpu,'Player_wall_seconds':call_wall,'first_query_started_at':measurement_start,'latest_query_ended_at':u1})
     except Exception as exc:
      error={'query_id':qid,'game_id':game['game_id'],'started_at':u0,'ended_at':stamp(),'error_type':type(exc).__name__,'error':str(exc),'choose_or_validation_seconds':time.perf_counter()-t0}
      write_record(output/f'failure-{qid:04d}.json',error);game['failure']=error;halt='query_or_recorder_failure';break
    game.update(status='TERMINAL'if s.state.terminal_status.is_terminal else'UNFINISHED',reason=halt,final_record=record_value(s.to_record()),Core_terminal=record_value(s.state.terminal_status),Session_result=record_value(s.result),ended_at=stamp(),outer_seconds=time.perf_counter()-tgame,cpu_seconds=time.process_time()-game_cpu,timing_eligible=all(q['timing_eligible']for q in game['queries']))
   except Exception as exc:
    game.update(status='GAME_SETUP_FAILED',error_type=type(exc).__name__,error=str(exc));halt='game_setup_failure'
   games.append(game);write_record(output/f'game-{game["game_id"]:02d}.json',game);write_record(output/'games.json',games)
 write_record(output/'games.json',games)
 summary={'started_at':started,'ended_at':stamp(),'seconds':time.perf_counter()-tick,'planned_games':24,'statuses':dict(Counter(g['status']for g in games)),'attempts':attempts,'Player_cpu_seconds':call_cpu,'Player_wall_seconds':call_wall,'halt':halt,'solver':0,'ordering_prototype_games':0}
 write_record(output/'summary.json',summary);print(json.dumps(summary))

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.inputs,a.plan,a.output)
