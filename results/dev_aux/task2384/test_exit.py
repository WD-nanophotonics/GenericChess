from pathlib import Path
import json,pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task109.adapter import PersistentStop
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader,StopObservationFailure
from scripts.generic_win_proof import _Interrupted
from results.dev_aux.task2382 import incremental as old
from results.dev_aux.task2384 import incremental as new

def scenario(module,exception):
 row=json.loads(Path('results/dev_aux/task2381/contexts.json').read_text())[0];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text())),deserialize_game_record(json.dumps(row['record'])));real=EvidenceStopReader(Path.cwd());flag=[False];clock=[0.];observed=[];saved=module._select_frontier
 def cancel():
  real()
  if flag[0]:observed.append(True);raise PersistentStop('isolatedpersistentstop')
  return False
 def inside(*args):
  flag[0]=True;clock[0]=1.
  if exception=='deadline':args[8].poll()
  elif exception=='value':raise ValueError('isolatedconvertederror')
  elif exception=='unsupported':raise NotImplementedError('isolatedunsupported')
  else:raise StopObservationFailure('isolateddirecterror')
 module._select_frontier=inside
 try:return module.prove_incremental_graph(s,max_nodes=512,max_edges=4096,seconds=1.,cancel=cancel,_clock=lambda:clock[0]),observed
 finally:module._select_frontier=saved

@pytest.mark.parametrize('exception',['deadline','value','unsupported'])
def test_old_missing_exit_check_is_observed(exception):
 r,observed=scenario(old,exception);assert r.status=='UNKNOWN'and r.certificate is None and observed==[]

@pytest.mark.parametrize('exception',['deadline','value','unsupported'])
def test_corrected_converted_exits_observe_persistentstop(exception):
 with pytest.raises(PersistentStop):scenario(new,exception)

def test_direct_invalidstop_observation_is_not_retried():
 with pytest.raises(StopObservationFailure):scenario(new,'direct')

def test_rank_core_and_selector_body_unchanged():
 import ast
 oldtree=ast.parse(Path('results/dev_aux/task2382/incremental.py').read_text(encoding='utf-8-sig'));newtree=ast.parse(Path('results/dev_aux/task2384/incremental.py').read_text(encoding='utf-8-sig'));oldnodes={n.name:n for n in oldtree.body if hasattr(n,'name')};newnodes={n.name:n for n in newtree.body if hasattr(n,'name')}
 for name,n in oldnodes.items():
  if name!='select_frontier':assert ast.dump(n)==ast.dump(newnodes[name]),name
