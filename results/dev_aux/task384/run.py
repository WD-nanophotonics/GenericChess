import sys,json,time,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task384';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task382/declaration.json').read_text(encoding='utf-8'));
for i,f in enumerate(d['roots']):f.update(index=i,seed=f['family']+'@'+str(f['distance']));
(O/'roots.json').write_text(json.dumps(d['roots'],indent=2),encoding='utf-8');ends=json.loads((R/'results/dev_aux/task370/endpoints.json').read_text(encoding='utf-8'));profiles=[]
for p in ends['endpoints']:
 for stage,w in [('initial',p['initial']),('endpoint',p['endpoint'])]:
  if not any(x['weights']==w for x in profiles):profiles.append({'weights':w,'names':[p['family']+'-'+stage]})
  else:next(x for x in profiles if x['weights']==w)['names'].append(p['family']+'-'+stage)
(O/'execution.json').write_text(json.dumps({'profiles':profiles,'allfrozen_beforepanel':True,'cap':24,'nodes':1024,'goal':'364fixedrulewin/loss32,draw0,quantity/19','source_sha':'c1b80eaa09fe13d5f12b1599d1ae4d53c224de30','prepared382_sha256':hashlib.sha256((R/'results/dev_aux/task382/declaration.json').read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(A.EXE.read_bytes()).hexdigest(),'scope':'ALL5exposedsourcefamilies/ALL15actuallegalrollbackroots2/6/10; all4frozenprofiles/bothcolors, nottraining/holdout/mate-distanceproof; preservegeneratorprice+unknowncuratedpreSFENhistory'},indent=2),encoding='utf-8');rows=[];t0=time.monotonic();unit=[0]+[90]*7+[0]+[90]*6+[0]
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(unit,qj)
 try:
  for p in profiles:
   ec=A.Engine(p['weights'],qj)
   try:
    for f in d['roots']:
     for c in (0,1):
      g=G.game(ec,eu,p['weights'],f,c,gj,deadline=t0+1200);rows.append({'weights':g['weights'],'root_index':f['index'],'color':c,'goal':g['goal'],'quantity':g['raw_quantity'],'termination':g['termination'],'plies':len(g['actions']),'seconds':g['seconds']});print(p['names'],f['index'],c,g['goal'],g['termination']['kind'],flush=True)
   finally:ec.close()
 finally:eu.close()
result={'seconds':time.monotonic()-t0,'games':len(rows),'go':sum(x['plies'] for x in rows),'actual_rule_terminal_games':sum(x['termination']['kind']!='cap24' for x in rows),'rows':rows};(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print({k:v for k,v in result.items() if k!='rows'})