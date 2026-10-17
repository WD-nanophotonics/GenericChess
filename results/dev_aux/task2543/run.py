"""Prospective TRAIN-only D3 cost probe, not a learned-price strength test."""
from pathlib import Path
import json,random,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv,replay_bound
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2543')
def run():
 assert not(D/'started.json').exists();p=json.loads((D/'plan.json').read_text());assert Path('results/dev_aux/task2539/result.json').exists()and Path('results/dev_aux/task2540/result.json').exists(),'Serial after original producers close';stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();rows=[];nodes=0
 (D/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest(),source_sha=hashlib.sha256((D/'run.py').read_bytes()).hexdigest())))
 for g in p['generator_seeds']:
  stop();cc=compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{g}.json').read_text())));names=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'));env=RecordedSessionEnv(GameSession(cc),names);rng=random.Random(g*1000000+p['family'])
  for _ in range(p['prefix_plies']):
   if env.terminal()is not None:break
   env.push(rng.choice(sorted(env.actions(),key=repr)))
  replay_bound(env);before=env.record();state=env.session.state;left=p['cap_seconds']-(time.perf_counter()-began);r=None
  if env.terminal()is None and left>0:r=TrainingSearch(p['depth'],quiet=False).search(env,FreeModel(p['weights']),nodes=p['nodes_per_query'],seconds=min(left,p['seconds_per_query']),seed=g*100000000+p['family']*1000+p['ordering_seed_offset'],cancel=stop)
  assert env.record()==before and env.session.state==state
  if r is not None:nodes+=r.nodes
  rows.append(dict(rule=g,record=before,actual_root_terminal=env.terminal(),query_omission_reason=('ACTUAL_TERMINAL'if env.terminal()is not None else'AGGREGATE_CAP_UNKNOWN')if r is None else None,query=None if r is None else dict(complete=r.complete,reason=r.reason,nodes=r.nodes,seconds=r.seconds,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal),scope='INITIALuniformmodel/currentTRAIN-onlyroot; no action committed/learning/heldoutquery.'))
 out=dict(status='COMPLETE_PROSPECTIVE_COST_PROBE',planned=4,rows=rows,nodes=nodes,seconds=time.perf_counter()-began,scope=p['scope']);(D/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
