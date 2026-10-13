import sys,json,time,hashlib,os,itertools
from pathlib import Path
R=Path.cwd();D=R/'results/dev_aux/task574/declaration.json';d=json.loads(D.read_bytes());O=R/'results/dev_aux/task576';assert not(O/'games.jsonl').exists();P=json.loads((R/'results/dev_aux/task575/result.json').read_bytes());assert P['status']=='PASS'
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task575'));from controller_pair import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];pref=[json.loads(x) for x in (R/'results/dev_aux/task575/games.jsonl').open()];execution=dict(question=d['question'],frozen_study_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),profiles=len(d['profiles']),family_count=len(d['roots']),logical_games=900,prefirstrepetition_cache='firstrootpair0/1 bothcolors source575 lines1/3; samefullinputs/executable/reset/price/history, notnewphysicalgo',expected_cost='under4min/600totalwall fromactualexecution start; nopricefit/additionalroots/modelselection',scope='Actualfinitepopulation comparison ofALL10ownprices, no fixedhuman/sourcepriceopponent orparameterfitness. Fullfamily/color/paircells preserved; noElo/globalvalue/learningclaim.');(O/'execution_plan.json').write_text(json.dumps(execution,indent=2),encoding='utf-8');t0=time.monotonic();rows=[];acks=[];actualgames=0;go=0;case=0
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for i,j in itertools.combinations(range(len(d['profiles'])),2):
  G.stop();assert time.monotonic()-t0<600;ec=ControlledEngine(d['profiles'][i]['weights'],qj,'warm_game');eu=ControlledEngine(d['profiles'][j]['weights'],qj,'warm_game');acks.extend([dict(pair=[i,j],role=role,profile=k,weights=e.w,prices=e.prices) for role,k,e in [('candidate',i,ec),('opponent',j,eu)]]);(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
  try:
   for f in d['roots']:
    for c in [0,1]:
     G.stop();assert time.monotonic()-t0<600
     if i==0 and j==1 and f['index']==0:
      g=pref[2*c];assert g['weights']==ec.w and g['opponent_weights']==eu.w and g['root']==f and g['color']==c;source=dict(file='results/dev_aux/task575/games.jsonl',line=2*c+1);cached=True
     else:
      ec.begin_game();eu.begin_game();g=native_game(ec,eu,ec.w,f,c,None,d,t0+600);g.update(candidate_profile=i,opponent_profile=j);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());actualgames+=1;go+=len(g['queries']);source=dict(file='results/dev_aux/task576/games.jsonl',line=actualgames);cached=False
     rows.append(dict(candidate_profile=i,opponent_profile=j,root_index=f['index'],root_seed=f['seed'],color=c,source=source,cached=cached,termination=g['termination'],goal=g['goal'],quantity=g['raw_quantity'],plies=len(g['actions']),query_count=len(g['queries'])));case+=1
  finally:ec.close();eu.close()
  (O/'progress.json').write_text(json.dumps(dict(logical_games=len(rows),actual_games=actualgames,actual_go=go,seconds=time.monotonic()-t0)),encoding='utf-8');print('pair',i,j,case,actualgames,round(time.monotonic()-t0,1),flush=True)
out=dict(status='COMPLETE',logical_games=len(rows),actual_games=actualgames,cached_games=2,actual_go=go,rows=rows,seconds=time.monotonic()-t0,price_acks=acks,scope=execution['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');assert len(rows)==900 and actualgames==898;print({k:v for k,v in out.items() if k not in ['rows','price_acks']})
