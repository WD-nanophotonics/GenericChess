import json,time,sys,os,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task871';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+180
for n in [360,364,381,509,583,835,851]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from game_barrier_engine import GameBarrierEngine
from controller_reduced import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';d=json.loads((R/'results/dev_aux/task869/plan.json').read_bytes());roots=json.loads((R/'results/dev_aux/task870/roots_frozen.json').read_bytes())['roots'];unit=[0]+[90]*7+[0]+[90]*6+[0];ends=[e for e in json.loads((R/'results/dev_aux/task855/endpoints.json').read_bytes())['endpoints'] if e['start']=='unit'];profiles=[dict(name=v+'_initial_unit',variant=v,weights=unit) for v in ['NR','NRB']]+[dict(name=e['name'],variant=e['variant'],weights=e['endpoint']) for e in ends];n=go=0;acks=[]
(O/'execution_inputs.json').write_text(json.dumps(dict(profiles=profiles,roots=roots,fixed_opponent=unit,nodes=256,cap=24,seed_base=d['seed_base'],scope=d['changed_premise'],frozen_endpoints_sha256=hashlib.sha256((R/'results/dev_aux/task855/endpoints.json').read_bytes()).hexdigest()),indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for p in profiles:
  ec=GameBarrierEngine(p['weights'],qj,'warm_game');eu=GameBarrierEngine(unit,qj,'warm_game');acks.extend([dict(weights=ec.w,prices=ec.prices),dict(weights=eu.w,prices=eu.prices)])
  try:
   for opp in d['opponents']:
    for f in roots:
     if f['variant']!=p['variant']:continue
     for color in [0,1]:
      ec.begin_game();eu.begin_game();g=native_game(ec,eu if opp=='unit_search' else None,ec.w,f,color,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(profile=p['name'],opponent=opp,pool=f['phase'],cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());n+=1;go+=len(g['queries'])
  finally:qj.flush();os.fsync(qj.fileno());ec.close();eu.close()
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');out=dict(status='ALL232_CHECKED_GRAMMAR_TRANSFER_GAMES_CLOSED',actual_games=n,actual_go=go,seconds=time.monotonic()-start,scope='Allfixedfrozenunitmodel/initial2variants29eligiblefamilies2colors2opponents; newdistributionafteroldmethodselection, notindependentconfirmation/restoredholdout. No newfit orlabelpricechoice.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out);assert n==232
