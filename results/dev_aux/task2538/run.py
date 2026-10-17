"""Frozen TRAIN-only candidate-turn TD / paid-WDL interface pilot."""
from pathlib import Path
from math import tanh,isclose
import json,random,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv,replay_bound
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2538')
def run():
 assert not(D/'started.json').exists();p=json.loads((D/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();used=0;rows=[];status='COMPLETE'
 pins={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [D/'run.py',Path('results/dev_aux/task2492/episode.py'),Path('results/dev_aux/task2532/free_model.py'),Path('results/dev_aux/task2504/search.py')]+[Path(f'results/dev_aux/task2525/rules-{gs}.json')for gs in p['generator_seeds']]};(D/'pins.json').write_text(json.dumps(dict(pins=pins),indent=2));(D/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest())))
 with(D/'queries.jsonl').open('x')as qf,(D/'games.jsonl').open('x')as gf:
  for gs in p['generator_seeds']:
   cc=compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())));names=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'));rng=random.Random(p['initial_seed']);initial=[1.]+[rng.uniform(.5,1.5)for _ in range(5)]
   for color in(0,1):
    for treatment in('baseline','proposal'):
     if used>=p['total_nodes']or time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
     w=list(initial)
     if treatment=='proposal':w[p['proposal_coordinate']]+=p['proposal_delta']
     model=FreeModel(w);foe=FreeModel(p['foe']);env=RecordedSessionEnv(GameSession(cc),names);rng=random.Random(gs*1000000+p['family'])
     for _ in range(p['prefix_plies']):
      if env.terminal()is not None:break
      env.push(rng.choice(sorted(env.actions(),key=repr)))
     prefix=env.record();td=TDLeafEpisode(p['eta'],p['lam']);records=[];ending='HORIZON_UNKNOWN';n0=used
     for ply in range(p['H']):
      stop()
      if env.terminal()is not None:ending='ACTUAL_TERMINAL';break
      left=p['total_nodes']-used;wall=p['cap_seconds']-(time.perf_counter()-began)
      if left<=0 or wall<=0:ending='AGGREGATE_CAP_UNKNOWN';status='PARTIAL_CAP';break
      actor=env.player();current=model if actor==color else foe;before=env.record();state=env.session.state;r=TrainingSearch(p['depth'],quiet=False).search(env,current,nodes=min(left,p['nodes_per_query']),seconds=min(wall,p['seconds_per_query']),seed=gs*100000000+p['family']*1000+ply+91380000,cancel=stop);used+=r.nodes;assert env.record()==before and env.session.state==state
      observe=treatment=='baseline'and actor==color and r.complete
      if observe:td.observe(model,r)
      if r.complete:env.push(r.action)
      q=dict(rule=gs,color=color,treatment=treatment,ply=ply,record_before=before,record_after=env.record(),weights=list(current.weights),actor=actor,observed_by_TD=observe,complete=r.complete,nodes=r.nodes,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,effective_nodes=min(left,p['nodes_per_query']),effective_seconds=min(wall,p['seconds_per_query']))
      qf.write(json.dumps(q,separators=(',',':'))+'\n');qf.flush();records.append(q)
      if not r.complete:ending='SEARCH_RESOURCE_UNKNOWN';break
     actual=env.terminal()
     if actual is not None:ending='ACTUAL_TERMINAL'
     replay_bound(env);stats=td.finish(model,actual)if treatment=='baseline'else None
     row=dict(rule=gs,color=color,treatment=treatment,initial_weights=w,after_TD_weights=list(model.weights),stats=stats,initial_record=prefix,record=env.record(),channels=names,outcome=actual,reward=None if actual is None else actual*(1 if color==0 else-1),ending=ending,nodes=used-n0,queries=len(records),candidate_TD_observations=sum(x['observed_by_TD']for x in records));rows.append(row);gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush()
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 def interval(r):return(-1,1)if r is None or r['reward']is None else(r['reward'],r['reward'])
 paired=[]
 for gs in p['generator_seeds']:
  lo=hi=0
  for color in(0,1):
   aa=next((x for x in rows if(x['rule'],x['color'],x['treatment'])==(gs,color,'baseline')),None);bb=next((x for x in rows if(x['rule'],x['color'],x['treatment'])==(gs,color,'proposal')),None);a=interval(aa);b=interval(bb);lo+=b[0]-a[1];hi+=b[1]-a[0]
  paired.append(dict(rule=gs,bounds=[lo/2,hi/2],strict_accept_would_be=lo>0,applied=False))
 result=dict(status=status,expected=16,actual=len(rows),missing=16-len(rows),nodes=used,seconds=time.perf_counter()-began,queries=sum(x['queries']for x in rows),actual_terminal=sum(x['outcome']is not None for x in rows),unknown=sum(x['outcome']is None for x in rows),candidate_TD_observations=sum(x['candidate_TD_observations']for x in rows),paired=paired,scope=p['scope']);(D/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
