"""Independent NEW8family actual-strength learning curves; no checkpoint selection."""
from pathlib import Path
import json,hashlib,random,time,datetime
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2510')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists();train=Path(p['training']);assert hashlib.sha256(train.read_bytes()).hexdigest()==p['training_sha'];done=json.loads(train.read_text());assert done['status']=='COMPLETE';assert json.loads(Path('results/dev_aux/task2507/result.json').read_text())['status']=='COMPLETE'
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 episodes=[json.loads(x)for x in Path(p['episodes']).read_text().splitlines()];arms={(a['seed'],a['quiet']):a for a in done['arms']};snapshots={};selection=[]
 for seed in p['seeds']:
  for q in(False,True):
   arm=arms[(seed,q)];gg=[e for e in episodes if e['seed']==seed and e['quiet']==q];cumulative=0;history=[(0,arm['initial'])]
   for g in gg:cumulative+=g['nodes'];history.append((cumulative,g['weights']))
   for target in p['node_checkpoints']:
    count,w=next(x for x in reversed(history)if x[0]<=target);tag=('q2'if q else'plain')+'_'+str(target);snapshots[(seed,tag)]=w;selection.append(dict(seed=seed,treatment=tag,target_nodes=target,actual_closed_episode_nodes=count,weights=w))
  snapshots[(seed,'initial')]=arms[(seed,False)]['initial']
 (OUT/'weights.json').write_text(json.dumps(selection,indent=2));stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())));rows=[];status='COMPLETE'
 with(OUT/'games.jsonl').open('x')as f:
  for seed in p['seeds']:
   for family in p['families']:
    for color in(0,1):
     tags=['initial']+[s+'_'+str(n)for n in p['node_checkpoints']for s in('plain','q2')]
     for tag in tags:
      env=ChessEnv();rng=random.Random(family)
      for _ in range(p['opening_plies']):
       if env.terminal()is not None:break
       env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
      prefix=env.record();m=Model(snapshots[(seed,tag)]);foe=Model(p['foe_weights']);nodes=0;reason='HORIZON_UNKNOWN';outcome=None
      for ply in range(p['H']):
       stop();outcome=env.terminal()
       if outcome is not None:reason='ACTUAL_TERMINAL';break
       left=p['cap_seconds']-(time.perf_counter()-start)
       if left<=0:status='PARTIAL_CAP';reason='GLOBAL_CAP_UNKNOWN';break
       r=TrainingSearch(p['depth'],quiet=False).search(env,m if env.player()==color else foe,nodes=p['nodes_per_query'],seconds=min(left,p['seconds_per_query']),seed=family*10000+ply,cancel=stop);nodes+=r.nodes
       if not r.complete:reason='SEARCH_LIMIT_UNKNOWN';break
       assert r.action is not None;env.push(r.action)
      actual=env.terminal()
      if actual is not None:outcome=actual;reason='ACTUAL_TERMINAL'
      reward=None if outcome is None else outcome*(1 if color==0 else -1);row=dict(seed=seed,family=family,color=color,treatment=tag,weights=snapshots[(seed,tag)],initial_record=prefix,record=env.record(),reward=reward,ending=reason,nodes=nodes);rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
      if status!='COMPLETE':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   print(json.dumps(dict(seed=seed,games=len(rows),seconds=time.perf_counter()-start)),flush=True)
   if status!='COMPLETE':break
 summary=[]
 for seed in p['seeds']:
  for tag in ['initial']+[s+'_'+str(n)for n in p['node_checkpoints']for s in('plain','q2')]:
   r=[x for x in rows if x['seed']==seed and x['treatment']==tag];summary.append(dict(seed=seed,treatment=tag,**{k:sum(x['reward']==v for x in r)for k,v in [('W',1),('L',-1),('D',0),('U',None)]}))
 result=dict(status=status,expected=p['expected_games'],actual=len(rows),nodes=sum(r['nodes']for r in rows),seconds=time.perf_counter()-start,results=summary,scope='ALLprefrozen checkpoints/all4seeds, NEW8families repeatedacrosscheckpoints; commonplain deployment. Baselinepaidonce/shared, NEVERindependentcopies. Curvesdescribe progression, cannot selectbestcheckpoint/seed orclaimmonotonicity/generalconvergence. Actualterminalonly,U/missingretained.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
