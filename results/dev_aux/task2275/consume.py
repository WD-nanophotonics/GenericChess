"""Closed new history-bound proofs and actual saved cursor continuations."""
from pathlib import Path
from copy import copy
import json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2275')
def run():
 assert not (OUT/'result.json').exists(); start=time.perf_counter(); stop=EvidenceStopReader(Path.cwd()); checked=[]; moves=0
 def cancel():
  stop(); return time.perf_counter()-start>=180
 newroots={r['family']:r for r in json.loads(Path('results/dev_aux/task2258/inputs.json').read_text())['roots']}
 oldroots={r['family']:r for r in json.loads(Path('results/dev_aux/task2228/inputs.json').read_text())['roots']}
 oldentries={r['slot']:r for r in map(json.loads,Path('results/dev_aux/task2246/queries.jsonl').read_text().splitlines())}
 panels=[(2260,'family','actual_conversions.json'),(2264,'slot','conversions.json')]
 for task,identifier,filename in panels:
  folder=Path(f'results/dev_aux/task{task}'); saved={r[identifier]:r for r in map(json.loads,(folder/'certificates.jsonl').read_text().splitlines())}; conversions=json.loads((folder/filename).read_text()); assert len(saved)==len(conversions)==(24 if task==2260 else 15)
  for row in conversions:
   if cancel():raise TimeoutError('closedproofconsumer_cap')
   idx=row[identifier]
   if task==2260:root=newroots[idx]; record=root['record']
   else:
    entry=oldentries[idx]; root=oldroots[entry['family']]; record=entry['root_record']
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')))
   s=GameSession.replay(c,deserialize_game_record(json.dumps(record))); cert=decode_graph(s,saved[idx]['certificate']); receipt=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel); assert receipt['verified']; cursor=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)
   final=deserialize_game_record(json.dumps(row['record'])); prefix=s.to_record().actions; assert final.actions[:len(prefix)]==prefix
   for action in final.actions[len(prefix):]:
    before=copy(s); choice=SessionChoice('ACTION',action=action)
    if s.state.position.side_to_move==cert.target:assert cursor.choose(s)==choice
    execute(s,choice); cursor.observe(before,choice,s); moves+=1
   assert s.result.status is not SessionStatus.ONGOING and s.result.winner==cert.target
   assert json.loads(serialize_game_record(s.to_record()))==row['record']
   checked.append(dict(task=task,id=idx,verified=receipt,target=cert.target))
 result=dict(status='PASS_39_NEW_HISTORY_PROOFS_AND_SAVED_CURSOR_EXECUTIONS',instances=len(checked),actual_continuation_moves=moves,checks=checked,seconds=time.perf_counter()-start,scope='ALL24newprefixWIN+ALL15actualopponentWIN completegraph/currentcursor andactualsavedpaths independentlyconsumed. Existingverifier reused, notsecondproverimplementation. No tablecandidatebuilder/solver/player/fit/newrewardgame call. Reference40DRAWremainactualunproved, notreward.')
 with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':run()
