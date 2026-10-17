"""Frozen actual Generic learningcurve; SAME learner and full rule histories."""
from pathlib import Path
from math import tanh
from collections import Counter
import json,random,time,hashlib,datetime
from generic_chess.generation.config import GeneratorConfig,GenerationError
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from results.dev_aux.task2511.generic import ScoringSessionEnv,NonScoringTerminal
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2534')
class RecordedSessionEnv(ScoringSessionEnv):
 def record(self):return json.loads(serialize_game_record(self.session.to_record()))
def replay_bound(env):
 clone=GameSession.replay(env.session.compiled,deserialize_game_record(json.dumps(env.record())));assert clone.state==env.session.state and clone.result==env.session.result and clone.to_record()==env.session.to_record();return clone

def run():
 assert not(D/'started.json').exists()
 p=json.loads((D/'registration.json').read_text());session=json.loads(Path('.local_agent/session.json').read_text());assert session['id']==p['session_id']and session['state']=='active';assert(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(session['started_at'])).total_seconds()<75*60
 source_paths=['results/dev_aux/task2534/run.py','results/dev_aux/task2511/generic.py','results/dev_aux/task2492/learning.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2492/adapters.py','results/dev_aux/task2504/search.py','generic_chess/generation/generator.py','generic_chess/generation/config.py','generic_chess/rules/compiler.py','generic_chess/session/session.py','results/dev_aux/task2532/free_model.py']
 pins={s:hashlib.sha256(Path(s).read_bytes()).hexdigest()for s in source_paths};(D/'pins.json').write_text(json.dumps(dict(pins=pins),indent=2));began=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());stop();rows=[];arms=[];failures=[];status='COMPLETE';counters=Counter();(D/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha=hashlib.sha256((D/'registration.json').read_bytes()).hexdigest())))
 with(D/'queries.jsonl').open('x')as qf,(D/'episodes.jsonl').open('x')as ef:
  for gs in p['generator_seeds']:
   if time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
   stop()
   try:
    from types import SimpleNamespace
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_ruleset
    raw=json.loads(Path('results/dev_aux/task2525',f'rules-{gs}.json').read_text()); rule=ruleset_from_dict(raw); g=SimpleNamespace(ruleset=rule,compiled_ruleset=compile_ruleset(rule))
   except GenerationError as e:failures.append(dict(generator_seed=gs,error=str(e)));continue
   (D/('rules-'+str(gs)+'.json')).write_text(json.dumps(ruleset_to_dict(g.ruleset),indent=2));channels=tuple((kind,t)for kind in('board','hand')for t in sorted(x.type_id for x in g.ruleset.piece_types if not x.is_anchor));assert channels[0]==('board','A')or channels[0]==('board','P')
   # Fix P's BOARD coefficient, no P movement/human value is assumed.
   channels=(('board','P'),)+tuple(x for x in channels if x!=('board','P'))
   for method,seed in p['arms_order']:
    rng=random.Random(seed);m=(Model if method=='fixed5'else FreeModel)([1.]+[rng.uniform(.5,1.5)for _ in channels[1:]]);initial=list(m.weights);used=0;completed=0;snapshots=[];previous_closed=dict(nodes=0,game=-1,weights=initial)
    for game in range(p['max_games']):
     if used>=p['nodes_per_arm']:break
     env=RecordedSessionEnv(GameSession(g.compiled_ruleset),channels);rng=random.Random(gs*1000000+p['training_family_offset']+game)
     for _ in range(p['prefix_plies']):
      if env.terminal()is not None:break
      env.push(rng.choice(sorted(env.actions(),key=repr)))
     replay_bound(env);prefix=env.record();before=list(m.weights);td=TDLeafEpisode(p['eta'],p['lambda']);outcome=None;reason='HORIZON_UNKNOWN';start_nodes=used;nq=0
     for ply in range(p['H']):
      stop();outcome=env.terminal()
      if outcome is not None:reason='ACTUAL_TERMINAL';break
      left=p['nodes_per_arm']-used;wall=p['cap_seconds']-(time.perf_counter()-began)
      if left<=0:reason='TOTAL_NODE_UNKNOWN';break
      if wall<=0:reason='GLOBAL_CAP_UNKNOWN';status='PARTIAL_CAP';break
      record=env.record();state=env.session.state;features=list(env.features());limit=min(left,p['nodes_per_query']);seconds=min(wall,p['seconds_per_query']);weights=list(m.weights)
      try:r=TrainingSearch(p['depth'],quiet=False).search(env,m,nodes=limit,seconds=seconds,seed=gs*100000000+seed+game*1000+ply+91100000,cancel=stop)
      except NonScoringTerminal as e:reason='NON_SCORING_UNKNOWN';status='ABORT_NON_SCORING';failures.append(dict(generator_seed=gs,method=method,seed=seed,game=game,non_scoring=str(e)));break
      assert env.record()==record and env.session.state==state;used+=r.nodes;nq+=1;counters['queries']+=1
      pred=tanh(r.value/10)if r.complete else None;gradient=None if not r.complete else[0.]*len(channels)if r.pv_terminal else list(m.gradient(r.pv_phi))
      if r.complete:
       td.observe(m,r);env.push(r.action);counters['commits']+=1;counters['promotion_commits']+=getattr(r.action.action,'promotion_target_id',None)is not None;counters['drop_commits']+=type(r.action.action).__name__ in('DropMove','SemanticDropMove')
      q=dict(generator_seed=gs,method=method,seed=seed,game=game,ply=ply,channels=channels,record_before=record,record_after=env.record(),features=features,weights=weights,complete=r.complete,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,prediction=pred,gradient=gradient,nodes=r.nodes,total_nodes=used,effective_node_limit=limit,effective_wall_limit=seconds,reason=r.reason)
      qf.write(json.dumps(q,separators=(',',':'))+'\n');qf.flush()
      if not r.complete:reason='SEARCH_RESOURCE_UNKNOWN';counters['failed_queries']+=1;break
     replay_bound(env);actual=env.terminal()
     if actual is not None:outcome=actual;reason='ACTUAL_TERMINAL'
     stats=td.finish(m,outcome)
     for target in p['checkpoints']:
      if used>=target and not any(x['target_nodes']==target for x in snapshots):
       selected=dict(nodes=used,game=game,weights=list(m.weights))if used==target else dict(previous_closed);snapshots.append(dict(target_nodes=target,**selected))
     previous_closed=dict(nodes=used,game=game,weights=list(m.weights))
     row=dict(generator_seed=gs,method=method,seed=seed,game=game,channels=channels,initial_weights=before,weights=list(m.weights),initial_record=prefix,record=env.record(),outcome=outcome,ending=reason,nodes=used-start_nodes,total_nodes=used,queries=nq,stats=stats);ef.write(json.dumps(row,separators=(',',':'))+'\n');ef.flush();rows.append(row);completed+=1
     if status!='COMPLETE':break
    arms.append(dict(generator_seed=gs,method=method,seed=seed,channels=channels,initial=initial,weights=list(m.weights),nodes=used,games=completed,snapshots=snapshots,cause='GLOBAL_ABORT'if status!='COMPLETE'else'TOTAL_NODES'if used==p['nodes_per_arm']else'MAX_GAMES'));print(json.dumps(arms[-1]),flush=True)
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 result=dict(status=status,expected_arms=len(p['generator_seeds'])*len(p['arms_order']),arms=arms,episodes=len(rows),actual_terminal=sum(r['outcome']is not None for r in rows),unknown=sum(r['outcome']is None for r in rows),nonzero_updates=sum(r['initial_weights']!=r['weights']for r in rows),nodes=sum(a['nodes']for a in arms),seconds=time.perf_counter()-began,counters=dict(counters),failures=failures,scope=p['scope']);(D/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='arms'}))
if __name__=='__main__':run()
