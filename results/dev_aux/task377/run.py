import sys,json,time,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task377';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task364/declaration.json').read_text(encoding='utf-8'));ends=json.loads((R/'results/dev_aux/task370/endpoints.json').read_text(encoding='utf-8'));profiles=[]
for p in ends['endpoints']:
 for stage,w in [('initial',p['initial']),('endpoint',p['endpoint'])]:
  if not any(x['weights']==w for x in profiles):profiles.append({'weights':w,'names':[p['family']+'-'+stage]})
  else:next(x for x in profiles if x['weights']==w)['names'].append(p['family']+'-'+stage)
roots=[x for x in d['roots'] if x['phase']=='development'];decl={'all_frozen_profiles':profiles,'roots':roots,'cap':24,'nodes':1024,'opponent':d['profiles'][0]['weights'],'goal':d['goal'],'selection':'allendpointpairs, no model/horizon/budget reselect, allrootcolorcells; untouchedby370fit','executable_sha256':hashlib.sha256(A.EXE.read_bytes()).hexdigest(),'endpoints_file_sha256':hashlib.sha256((R/'results/dev_aux/task370/endpoints.json').read_bytes()).hexdigest()};(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');rows=[];t0=time.monotonic()
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(d['profiles'][0]['weights'],qj)
 try:
  for p in profiles:
   ec=A.Engine(p['weights'],qj)
   try:
    for f in roots:
     for c in (0,1):
      g=G.game(ec,eu,p['weights'],f,c,gj,deadline=t0+600);rows.append({'weights':g['weights'],'root_index':f['index'],'color':c,'goal':g['goal'],'quantity':g['raw_quantity'],'termination':g['termination'],'plies':len(g['actions']),'seconds':g['seconds']});print(p['names'],f['index'],c,g['goal'],flush=True)
   finally:ec.close()
 finally:eu.close()
result={'seconds':time.monotonic()-t0,'games':len(rows),'go':sum(x['plies'] for x in rows),'rows':rows};(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print({k:v for k,v in result.items() if k!='rows'})