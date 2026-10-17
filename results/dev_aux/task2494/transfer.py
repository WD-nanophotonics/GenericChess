"""Same learner/search transfer check on real full GameSession; no WDL teacher."""
from pathlib import Path
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from results.dev_aux.task2492.learning import Model,AlphaBeta,TreeStrap,TDLeaf
from results.dev_aux.task2492.adapters import SessionEnv
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2494')
def run():
 stop=SharedDeleteStopReader(Path.cwd());stop();root=json.loads(Path('results/dev_aux/task2480/inputs.json').read_text())[0];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())),deserialize_game_record(json.dumps(root['record'])));start=time.perf_counter();record=json.loads(serialize_game_record(s.to_record()));names=(('board','N'),('board','R'),('hand','N'),('hand','R'));model=Model([1,1,1,1]);env=SessionEnv(s,names);learner=TreeStrap(.05);rows=[]
 for ply in range(4):
  if env.terminal() is not None:break
  stop();before=list(model.weights);r=AlphaBeta(2,0).search(env,model,nodes=8192,seconds=10.,seed=2494+ply,cancel=stop)
  assert r.complete and r.action is not None
  stats=learner.update(model,r);row=dict(ply=ply,before=before,weights=list(model.weights),features=env.features(),samples=len(r.samples),search_nodes=r.nodes,score=r.value,stats=stats);env.push(r.action);row['after_record']=json.loads(serialize_game_record(env.session.to_record()));rows.append(row)
 assert json.loads(serialize_game_record(s.to_record()))==record
 result=dict(status='PASS_SAME_LEARNER_ON_REAL_GAMESESSION',source_root=root['index'],rules=root['rules'],features=names,fixed_scale='board N1, NOT handN constraint',steps=rows,terminal=env.terminal(),seconds=time.perf_counter()-start,claim='Interface/execution transfer only, exposed old TRAIN root; no generic strength or full-domain qualification. qdepth0, no generic tactical predicate or solver/table labels.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='steps'}))
if __name__=='__main__':run()
