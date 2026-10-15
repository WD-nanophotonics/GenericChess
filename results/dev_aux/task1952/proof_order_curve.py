"""Fresh all-child/all-target full-rule proof budget curve, not continued oldcap."""
from pathlib import Path
from dataclasses import asdict
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from results.dev_aux.task1951.check_first import prove_check_first
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_session_certificate_json import export_session_certificate
from scripts.generic_session_native_material import _load_transport
O=Path('results/dev_aux/task1952')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (O/n).open('x') as f:json.dump(d,f,indent=2)
def run():
 plan=json.loads((O/'plan.json').read_text());assert all(sha(p)==h for p,h in plan['source_sha'].items());c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));transport=_load_transport();start=time.perf_counter();done=0;status='COMPLETE';physical=0
 def cancelled():return time.perf_counter()-start>=plan['seconds_cap']
 with (O/'queries.jsonl').open('x') as f:
  for case in plan['queries']:
   transport.stop_check(Path.cwd())
   if cancelled():status='GLOBAL_CAP';break
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(case['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==case['state_sha'];solver=prove_session_win_batch_pn if case['method']=='ordinal' else prove_check_first;result=solver(s,target=case['target'],max_nodes=case['max_nodes'],seconds=case['seconds'],max_depth=64,cancel=cancelled)
   row={k:v for k,v in case.items() if k!='record'};row.update(status=result.status,reason=result.reason,nodes=result.nodes,seconds_used=result.seconds,stats={k:getattr(result,k) for k in ['frontiers','transitions','iterations','peak_depth','eager_board_successors','claims_assessed']},usable=False,verification=None,actual_final_record=None)
   if result.status=='PROVEN_WIN':
    try:cursor=SessionStrategyCursor(s,result.certificate,max_nodes=262144,seconds=5.,cancel=cancelled)
    except Exception as error:
     row['verification_error']=type(error).__name__+':'+str(error)
     if hasattr(error,'receipt'):row['verification']=error.receipt
    else:
     row['verification']=cursor.receipt;assert cursor.receipt['verified'];row['usable']=True;row['root_rank']=cursor.node.rank;row['physical_ranks']=[]
     certificate=export_session_certificate(s,result.certificate,max_nodes=262144);write(f"certificate-{case['query']}.json",certificate)
     while s.result.status is SessionStatus.ONGOING:
      assert cursor.node.rank>0;rank=cursor.node.rank;choice=cursor.choose(s) if s.state.position.side_to_move==case['target'] else cursor.node.edges[0][0];assert choice is not None;cursor.commit(s,choice);assert cursor.node.rank<rank;row['physical_ranks'].append(cursor.node.rank)
     assert s.result.winner==case['target'];row['actual_final_record']=json.loads(serialize_game_record(s.to_record()));row['actual_result']={**asdict(s.result),'status':s.result.status.value};physical+=1
   f.write(json.dumps(row)+'\n');f.flush();done+=1
   if done%24==0:print(json.dumps(dict(done=done,expected=len(plan['queries']),verified_physical_wins=physical,seconds=time.perf_counter()-start)),flush=True)
 write('completion.json',dict(status=status,completed=done,expected=len(plan['queries']),actual_strategy_wins=physical,seconds=time.perf_counter()-start,source_unchanged=all(sha(p)==h for p,h in plan['source_sha'].items())))
if __name__=='__main__':run()
