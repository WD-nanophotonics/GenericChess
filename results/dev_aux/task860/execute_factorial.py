import json,sys,time,os,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task862';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+300
for n in [360,364,381,509,583,835,851,860]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from dual_engine import DualEngine
from controller_reduced import native_game
assert json.loads((R/'results/dev_aux/task861/result.json').read_bytes())['status']=='PASS_ALL32_DUAL_NO_OVERRIDE_VS_QUALIFIED_ORIGINAL';A.EXE=R/'.local_agent/dualprice38/dual.exe';d=json.loads((R/'results/dev_aux/task850/plan.json').read_bytes());d['seed_base']=2026142500;roots=json.loads((R/'results/dev_aux/task850/roots_frozen.json').read_bytes())['roots'];eps=json.loads((R/'results/dev_aux/task855/endpoints.json').read_bytes())['endpoints'];unit=[0]+[90]*7+[0]+[90]*6+[0];configs=[dict(endpoint=e['name'],variant=e['variant'],mode=o+l,ordering=e['endpoint'] if o=='L' else e['initial'],leaf=e['endpoint'] if l=='L' else e['initial']) for e in eps for o in ['I','L'] for l in ['I','L']];acks=[];games=go=0
(O/'execution_inputs.json').write_text(json.dumps(dict(configs=configs,roots=roots,opponents=d['opponents'],fixed_opponent=unit,nodes=256,cap=24,seed_base=d['seed_base'],scope='DiagnosticALL4originallearnedpairpricefactorials, all19eligiblefamilies, notnewunexposedholdout;608actualgames. I=initial L=learned, modefirstnativepriceconsumers secondleafeval.'),indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for config in configs:
  ec=DualEngine(config['ordering'],config['leaf'],qj);eu=DualEngine(unit,unit,qj);acks.extend([dict(weights=ec.w,prices=ec.prices,leaf_weights=ec.leaf_weights),dict(weights=eu.w,prices=eu.prices,leaf_weights=eu.leaf_weights)])
  try:
   for opp in d['opponents']:
    for f in roots:
     if f['variant']!=config['variant']:continue
     for color in [0,1]:
      ec.begin_game();eu.begin_game();g=native_game(ec,eu if opp=='unit_search' else None,ec.w,f,color,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(endpoint=config['endpoint'],mode=config['mode'],leaf_weights=config['leaf'],opponent=opp,pool=f['phase'],cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());games+=1;go+=len(g['queries'])
  finally:qj.flush();os.fsync(qj.fileno());ec.close();eu.close()
  print('DUAL_CLOSED',config['endpoint'],config['mode'],games,go,round(time.monotonic()-start,2),flush=True)
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');result=dict(status='ALL608_LEAF_NATIVE_PRICE_FACTORIAL_GAMES_CLOSED',actual_games=games,actual_go=go,seconds=time.monotonic()-start,executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest(),scope='No newfit; separatesleafweightsfromallremainingnativepriceconsumers, NOTSEEalone, sameordinaryconcurrentmachine/256node/H24. Fullqueryleafreadbacks andnative/PVvalidation; independentauditnext.');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');assert games==608;print(result)
