"""Frozen heldout smoke evaluation; no selection/human labels/learning here."""
from pathlib import Path
import json,random,time,hashlib,datetime
from results.dev_aux.task2492.learning import Model,AlphaBeta
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2500')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists();source=Path(p['weights']);assert hashlib.sha256(source.read_bytes()).hexdigest()==p['weights_sha'];arms=json.loads(source.read_text())['arms'];stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())));done=[];status='COMPLETE'
 with(OUT/'games.jsonl').open('x')as f:
  for arm in arms:
   for prefix_seed in p['prefix_seeds']:
    for color in (0,1):
     for treatment in ('initial','learned'):
      env=ChessEnv();rng=random.Random(prefix_seed)
      for _ in range(p['opening_plies']):
       if env.terminal() is not None:break
       env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
      initial_record=env.record();candidate=Model(arm['initial']if treatment=='initial'else arm['weights']);foe=Model(p['foe_weights']);nodes=0;outcome=None;ending='HORIZON_UNKNOWN'
      for ply in range(p['H']):
       stop();outcome=env.terminal()
       if outcome is not None:ending='ACTUAL_TERMINAL';break
       if time.perf_counter()-start>=p['cap_seconds']:ending='GLOBAL_CAP_UNKNOWN';status='PARTIAL_GLOBAL_CAP';break
       r=AlphaBeta(p['depth'],p['qdepth']).search(env,candidate if env.player()==color else foe,nodes=p['nodes_per_search'],seconds=p['seconds_per_search'],seed=prefix_seed*10000+ply,cancel=stop);nodes+=r.nodes
       if not r.complete:ending='SEARCH_LIMIT_UNKNOWN';break
       env.push(r.action)
      actual=env.terminal()
      if actual is not None:outcome=actual;ending='ACTUAL_TERMINAL'
      reward=None if outcome is None else outcome*(1 if color==0 else-1)
      row=dict(seed=arm['seed'],method=arm['method'],prefix_seed=prefix_seed,color=color,treatment=treatment,nodes=nodes,ending=ending,reward=reward,initial_record=initial_record,record=env.record());done.append(row);f.write(json.dumps(row)+'\n');f.flush()
      if status!='COMPLETE':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 results=[]
 for arm in arms:
  rows=[x for x in done if x['seed']==arm['seed']and x['method']==arm['method']];tallies={}
  for treatment in ('initial','learned'):
   rr=[x for x in rows if x['treatment']==treatment];tallies[treatment]={k:sum(x['reward']==v for x in rr)for k,v in [('W',1),('L',-1),('D',0),('U',None)]}
  results.append(dict(seed=arm['seed'],method=arm['method'],tallies=tallies))
 result=dict(status=status,expected=len(arms)*len(p['prefix_seeds'])*4,actual=len(done),seconds=time.perf_counter()-start,nodes=sum(x['nodes']for x in done),results=results,scope='NEW8family replication, SAME uniform all1 foe for BOTHinitializations, frozen prices/roles/ties; real WDL only, U censored. Tiny pilot cannot establish convergence/strength. No price choice or learning uses these outcomes.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
