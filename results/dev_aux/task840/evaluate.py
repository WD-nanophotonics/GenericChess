import json,time,sys,os,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task846';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+300
for n in [360,364,381,509,583,835]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from game_barrier_engine import GameBarrierEngine
from controller_curriculum import native_game
assert json.loads((R/'results/dev_aux/task845/result.json').read_bytes())['status']=='PASS_ALL_EXACT_FEATURE_LABEL_LOGGRAD_AND4_ENDPOINTS';A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';plan=json.loads((R/'results/dev_aux/task840/plan.json').read_bytes());originals=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes())['initial_profiles'];ep=json.loads((R/'results/dev_aux/task844/endpoints.json').read_bytes());profiles=[dict(name='original_'+p['name'],weights=p['weights']) for p in originals]+[dict(name=e['name'],weights=e['weights']) for e in ep['endpoints']]+[ep['initial_projection_controls'][1]];assert len({tuple(p['weights']) for p in profiles})==len(profiles)==7;roots=[r for r in json.loads((R/'results/dev_aux/task841/roots_frozen.json').read_bytes())['roots'] if r['phase']!='train'];acks=[];n=go=0
execution=dict(profiles=profiles,opponents=originals,roots=roots,nodes=256,cap=24,expected_games=672,endpoints_sha256=hashlib.sha256((R/'results/dev_aux/task844/endpoints.json').read_bytes()).hexdigest(),scope='ALL7uniqueprofiles2fixedopponents24newdev/validationfamilies2colors both256/H24. Includes untrainedprojectedrandom control (projectedunitidenticaloriginal). Endpointfreezebeforeanyvalidation/sourceprice, noresultselectedextension.')
(O/'execution_inputs.json').write_text(json.dumps(execution,indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for p in profiles:
  for opp in originals:
   e=GameBarrierEngine(p['weights'],qj,'warm_game');eu=GameBarrierEngine(opp['weights'],qj,'warm_game');acks.extend([dict(role='candidate',name=p['name'],weights=e.w,prices=e.prices),dict(role='opponent',name=opp['name'],weights=eu.w,prices=eu.prices)])
   try:
    for f in roots:
     for color in [0,1]:
      e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,f,color,None,plan,deadline);qj.flush();os.fsync(qj.fileno());g.update(profile=p['name'],opponent=opp['name'],pool=f['phase'],cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());n+=1;go+=len(g['queries'])
   finally:qj.flush();os.fsync(qj.fileno());e.close();eu.close()
  print('EVAL_CLOSED',p['name'],n,go,round(time.monotonic()-start,2),flush=True)
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');(O/'result.json').write_text(json.dumps(dict(status='ALL672_NEW_MC_PROBES_CLOSED',actual_games=n,actual_go=go,seconds=time.monotonic()-start,source_executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest()),indent=2),encoding='utf-8');assert n==672
