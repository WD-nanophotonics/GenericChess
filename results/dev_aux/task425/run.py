from pathlib import Path
import json,sys,random,hashlib,time,os
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G;sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
A.EXE=R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe';A.validate_search=V.query
O=R/'results/dev_aux/task425';d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));d['seed_base']=d['random_seed_base'];profiles=[];cache={}
for arm,task in [('unit',418),('random',419)]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_text(encoding='utf-8'));assert ep['frozen_before_development']
 for e in ep['endpoints']:
  for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
   if not any(p['weights']==w for p in profiles):profiles.append(dict(weights=w,names=[]))
   next(p for p in profiles if p['weights']==w)['names'].append(arm+'-trained-'+e['family']+'-'+stage)
 for i,line in enumerate((R/f'results/dev_aux/task{task}/games.jsonl').read_text(encoding='utf-8').splitlines(),1):
  g=json.loads(line)
  if g['root']['phase']=='development':cache[(arm,tuple(g['weights']),g['root']['index'],g['color'])]=(g,dict(file=f'results/dev_aux/task{task}/games.jsonl',line=i))
src=(R/'results/dev_aux/task418/run.py').read_text(encoding='utf-8');a=src.index('src=(R/');b=src.index('contexts={}',a);exec(compile(src[a:b],'existing_random_function','exec'))
src=src.replace('out=dict(weights=w', "out=dict(opponent_arm='random',weights=w");exec(compile(src,'tagged_random_function','exec'))
allrows=[];new=0;hits=0;go=0;acks=[];t0=time.monotonic();assert not(O/'games.jsonl').exists()
with (O/'games.jsonl').open('w',encoding='utf-8') as gj,(O/'queries.jsonl').open('w',encoding='utf-8') as qj:
 for arm in ['unit','random']:
  eu=A.Engine(d['fixed_opponent'],qj) if arm=='unit' else None
  try:
   for p in profiles:
    missing=any((arm,tuple(p['weights']),f['index'],c) not in cache for f in d['roots'] for c in (0,1));ec=A.Engine(p['weights'],qj) if missing else None
    if ec:acks.append(dict(weights=ec.w,prices=ec.prices))
    try:
     for f in d['roots']:
      for c in (0,1):
       k=(arm,tuple(p['weights']),f['index'],c)
       if k in cache:g,ref=cache[k];hits+=1
       else:
        g=G.game(ec,eu,p['weights'],f,c,None,cap=d['cap'],nodes=d['nodes'],deadline=t0+300) if eu else random_game(ec,p['weights'],f,c,gj,t0+300)
        if eu:g['opponent_arm']=arm;gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno())
        new+=1;go+=len(g['queries']);ref=dict(file='results/dev_aux/task425/games.jsonl',line=new);cache[k]=(g,ref)
       allrows.append(dict(arm=arm,names=p['names'],weights=p['weights'],root_index=f['index'],color=c,goal=g['goal'],quantity=g['raw_quantity'],termination=g['termination'],plies=len(g['actions']),source=ref))
    finally:
     if ec:ec.close()
  finally:
   if eu:eu.close()
out=dict(seconds=time.monotonic()-t0,new_games=new,new_go=go,logical_games=len(allrows),cache_hits=hits,profiles=profiles,rows=allrows,price_acks=acks,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['rows','profiles','price_acks']})
