"""Before-cohort actual Native/phase qualification, no DEV result reading."""
from pathlib import Path
from dataclasses import asdict
from copy import copy
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_native_material import SessionKRNMaterialProvider,_load_transport
from scripts.generic_session_phase_player import SessionPhasePlayer,PhaseLimits
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_win_proof import _same_state
from results.dev_aux.task1848.study import eval_for
OUT=Path('results/dev_aux/task1847')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def run():
 p=json.loads(Path('results/dev_aux/task1848/plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items())
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));roots=json.loads(Path(p['roots']).read_text())['roots']
 write('plan.json',dict(study_plan_sha=sha('results/dev_aux/task1848/plan.json'),source_sha=sha(__file__),seconds_cap=180,scope='32root Native one-ply frontiers plus all first2root successors;8TRAIN-only R720 role/policy pilot games. No price/mu/horizon selection, source and384schedule already frozen.'))
 transport=_load_transport();provider=SessionKRNMaterialProvider({**p['native_plan'],'seconds_cap':180,'max_go':8*80},OUT/'run',stop=lambda:transport.stop_check(Path.cwd()))
 start=time.perf_counter();frontiers=actions=go=0;rows=[];error=None
 def cancel():return time.perf_counter()-start>=180
 try:
  provider.start()
  for root in roots:
   current=GameSession(c,root['setup']);actions+=provider.perft_one(current);frontiers+=1
   if root['family']<2:
    for action in current.legal_actions():
     child=copy(current);child.submit(action)
     if child.result.status is SessionStatus.ONGOING:actions+=provider.perft_one(child);frontiers+=1
  with (OUT/'moves.jsonl').open('x',encoding='utf-8') as log:
   for family in (0,1):
    for role in (0,1):
     for mode in (False,True):
      current=GameSession(c,roots[family]['setup']);players=[];tail=False
      for side in (0,1):
       candidate=side==role
       def normal(state,n,seconds,cancel):return provider.choose(current,state,720,n,seconds,cancel)
       players.append(SessionPhasePlayer(c,eval_for(720),normal_search=normal,proof_enabled=mode if candidate else True,proof_depth=64,limits=PhaseLimits(proof_nodes=16384 if candidate else16)))
      for ply in range(80):
       if current.result.status is not SessionStatus.ONGOING:break
       if cancel():raise TimeoutError('frozen qualification cap')
       if ply>=16:
        live=[x.cursor for x in players if x.cursor is not None and 0<x.cursor.node.rank<=64]
        if not live:break
        tail=True
       side=current.state.position.side_to_move;n=4096 if side==role else64
       d=players[side].choose(current,max_nodes=n,seconds=2.25,allow_new_proof=ply<16,cancel=cancel)
       assert d.choice is not None,(d.source,d.exit_cause)
       assert d.proof_nodes<=(16384 if side==role else16) and d.verification_nodes<=16384
       assert dict(d.phase_limits)['normal_nodes']==n and dict(d.phase_limits)['normal_seconds']==.1
       result=commit_session_decision(current,d,players,cancel=cancel)
       rebuilt=GameSession.replay(c,current.to_record());assert _same_state(rebuilt.state,current.state) and _same_state(rebuilt.result,current.result)
       row=dict(family=family,role=role,mode=mode,ply=ply,side=side,choice=action_to_dict(d.choice.action),source=d.source,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,normal_nodes=d.search_nodes,phase_limits=dict(d.phase_limits),proof_stats=dict(d.proof_stats),proof_seconds=d.proof_seconds,verification_seconds=d.verification_seconds,normal_seconds=d.normal_seconds,seconds=d.seconds)
       log.write(json.dumps(row)+'\n');log.flush()
      rows.append(dict(family=family,role=role,mode=mode,tail=tail,result=asdict(current.result),record=json.loads(serialize_game_record(current.to_record()))));rows[-1]['result']['status']=current.result.status.value
      print(json.dumps(dict(pilots=len(rows),seconds=round(time.perf_counter()-start,3))),flush=True)
 except BaseException as ex:
  error=type(ex).__name__+':'+str(ex);raise
 finally:
  provider.close()
  write('qualification.json',dict(status='PASS' if error is None and len(rows)==8 else 'FAIL_PRESERVED',error=error,study_plan_sha=sha('results/dev_aux/task1848/plan.json'),fingerprint=c.ruleset_fingerprint,frontiers=frontiers,actions=actions,pilot_games=len(rows),rows=rows,native_go=provider.queries,native_nodes=provider.reported_nodes,seconds=time.perf_counter()-start,source_unchanged=all(sha(f)==h for f,h in p['source_sha'].items())))
if __name__=='__main__':run()
