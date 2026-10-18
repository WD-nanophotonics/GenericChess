"""Prospective paid Free6 TD versus bound-aware mean TreeStrap; research only."""
from pathlib import Path
from collections import Counter
import json,random,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv,replay_bound
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.learning import TreeStrap
from results.dev_aux.task2558.clock import rate
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2558')
CHANNELS=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'))
def run():
 assert not(D/'started.json').exists();p=json.loads((D/'plan.json').read_text());s=json.loads(Path('.local_agent/session.json').read_text());assert s['id']==p['session_id']and s['state']=='active'
 paths=[Path(__file__),D/'plan.json',Path('results/dev_aux/task2492/episode.py'),D/'clock.py',Path('results/dev_aux/task2492/learning.py'),Path('results/dev_aux/task2532/free_model.py'),Path('results/dev_aux/task2504/search.py'),Path('results/dev_aux/task2525/run.py'),Path('results/dev_aux/task2511/generic.py')]+[Path(f'results/dev_aux/task2525/rules-{g}.json')for g in p['generator_seeds']]
 (D/'pins.json').write_text(json.dumps(dict(pins={x.as_posix()if not x.is_absolute()else x.relative_to(Path.cwd()).as_posix():hashlib.sha256(x.read_bytes()).hexdigest()for x in paths}),indent=2));(D/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest())))
 stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();arms=[];counts=Counter();status='COMPLETE';gid=0
 with(D/'queries.jsonl').open('x')as qf,(D/'games.jsonl').open('x')as gf,(D/'updates.jsonl').open('x')as uf:
  for gs in p['generator_seeds']:
   cc=compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())))
   for method,seed in p['arms_order']:
    rng=random.Random(seed);initial=[1.]+[rng.uniform(.5,1.5)for _ in range(5)];model=FreeModel(initial);foe=FreeModel(p['foe']);used=0;games=0;updates=0;queryupdates=0;last_observed_nodes=0;armbegan=time.perf_counter()
    for index in range(p['max_games']):
     if used>=p['nodes_per_arm']or time.perf_counter()-began>=p['cap_seconds']:break
     gid+=1;color=index%2;family=p['training_family_offset']+index//2;env=RecordedSessionEnv(GameSession(cc),CHANNELS);rr=random.Random(gs*1000000+family)
     for _ in range(p['prefix_plies']):
      if env.terminal()is not None:break
      env.push(rr.choice(sorted(env.actions(),key=repr)))
     prefix=env.record();td=TDLeafEpisode(p['eta'],p['lam']);ts=TreeStrap(p['eta']);before=list(model.weights);before_nodes=used;nq=0;observed=0;changedqueries=0;ending='HORIZON_UNKNOWN';gamebegan=time.perf_counter()
     for ply in range(p['H']):
      stop()
      if env.terminal()is not None:ending='ACTUAL_TERMINAL';break
      left=p['nodes_per_arm']-used;wall=p['cap_seconds']-(time.perf_counter()-began)
      if left<=0 or wall<=0:ending='AGGREGATE_CAP_UNKNOWN';break
      actor=env.player();current=model if actor==color else foe;w=list(current.weights);record=env.record();state=env.session.state;effective_depth=p['depth']if actor==color else p['opponent_depth'];limit=min(left,p['nodes_per_query']if actor==color else p['opponent_nodes_per_query']);seconds=min(wall,p['seconds_per_query']);orderseed=gs*100000000+family*1000+ply+p['ordering_seed_offset']
      r=TrainingSearch(effective_depth,quiet=False).search(env,current,nodes=limit,seconds=seconds,seed=orderseed,cancel=stop);used+=r.nodes;nq+=1;assert env.record()==record and env.session.state==state
      observe=actor==color and r.complete;stats=None;clock=None
      if observe:
       clock=rate(p['eta'],used,last_observed_nodes,method);ts.eta=clock['eta'];stats=ts.update(model,r);last_observed_nodes=used;observed+=1;changedqueries+=stats['changed'];queryupdates+=stats['changed']
      if r.complete:env.push(r.action)
      q=dict(clock=clock,effective_depth=effective_depth,gameid=gid,generator_seed=gs,method=method,seed=seed,family=family,color=color,index=index,ply=ply,actor=actor,weights=w,weights_after=list(current.weights),record_before=record,record_after=env.record(),complete=r.complete,observed=observe,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,samples=[dict(phi=a.phi,lower=str(a.lower),upper=str(a.upper),depth=a.depth)for a in r.samples],learning=stats,nodes=r.nodes,total_nodes=used,seconds=r.seconds,effective_nodes=limit,effective_seconds=seconds,reason=r.reason,ordering_seed=orderseed)
      qf.write(json.dumps(q,separators=(',',':'))+'\n');qf.flush()
      if not r.complete:ending='SEARCH_RESOURCE_UNKNOWN';break
     actual=env.terminal()
     if actual is not None:ending='ACTUAL_TERMINAL'
     replay_bound(env);stats=td.finish(model,actual)if method=='TD'else None;changed=before!=model.weights;updates+=changed
     row=dict(gameid=gid,generator_seed=gs,method=method,seed=seed,family=family,color=color,index=index,initial_weights=before,after_weights=list(model.weights),stats=stats,changed_queries=changedqueries,initial_record=prefix,record=env.record(),channels=CHANNELS,outcome=actual,reward=None if actual is None else actual*(1 if color==0 else-1),ending=ending,nodes=used-before_nodes,total_nodes=used,queries=nq,observed=observed,seconds=time.perf_counter()-gamebegan)
     gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush();uf.write(json.dumps(dict(generator_seed=gs,method=method,seed=seed,index=index,nodes=used,before=before,after=list(model.weights),gameids=[gid],changed=changed),separators=(',',':'))+'\n');uf.flush();games+=1
     for k,v in dict(games=1,actual_terminal=actual is not None,unknown=actual is None,queries=nq,observed=observed,query_updates=changedqueries).items():counts[k]+=v
    arm=dict(generator_seed=gs,method=method,seed=seed,channels=CHANNELS,initial=initial,weights=list(model.weights),nodes=used,games=games,updates=updates,query_updates=queryupdates,seconds=time.perf_counter()-armbegan,cause='TOTAL_NODES'if used==p['nodes_per_arm']else'GLOBAL_CAP'if time.perf_counter()-began>=p['cap_seconds']else'MAX_GAMES');arms.append(arm);print(json.dumps(arm),flush=True)
    if time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
   if status!='COMPLETE':break
 result=dict(status=status,expected_arms=32,arms=arms,nodes=sum(a['nodes']for a in arms),seconds=time.perf_counter()-began,counts=dict(counts),scope=p['scope']);(D/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='arms'}))
if __name__=='__main__':run()
