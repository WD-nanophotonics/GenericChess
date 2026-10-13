import json,sys,time,os,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task857';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+180
for n in [360,364,381,509,583,835,851]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from game_barrier_engine import GameBarrierEngine
from controller_reduced import native_game
assert json.loads((R/'results/dev_aux/task856/result.json').read_bytes())['status']=='PASS_ALL_REDUCED_TRUE_TERMINAL_FIT_GAMES_AND_SELECTION';A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';d=json.loads((R/'results/dev_aux/task850/plan.json').read_bytes());d['seed_base']=2026142500;roots=[r for r in json.loads((R/'results/dev_aux/task850/roots_frozen.json').read_bytes())['roots'] if r['phase']!='train'];originals=json.loads((R/'results/dev_aux/task853/execution_inputs.json').read_bytes())['profiles'];ep=json.loads((R/'results/dev_aux/task855/endpoints.json').read_bytes());profiles=[dict(name=v+'_initial_'+p['name'],variant=v,weights=p['weights']) for v in ['NR','NRB'] for p in originals]+[dict(name=e['name'],variant=e['variant'],weights=e['endpoint']) for e in ep['endpoints']];unit=originals[0]['weights'];n=go=0;acks=[]
(O/'execution_inputs.json').write_text(json.dumps(dict(profiles=profiles,roots=roots,fixed_opponent=unit,nodes=256,cap=24,seed_base=d['seed_base'],endpoint_sha256=hashlib.sha256((R/'results/dev_aux/task855/endpoints.json').read_bytes()).hexdigest(),scope='All8variantprofiles11newheldoutfamilies2colors2opponents, matchedvariant. Artificialsmallinventory, allfailureseedskept noresample, newH24trueevalnotfullgame.'),indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for p in profiles:
  e=GameBarrierEngine(p['weights'],qj,'warm_game');eu=GameBarrierEngine(unit,qj,'warm_game');acks.extend([dict(weights=e.w,prices=e.prices),dict(weights=eu.w,prices=eu.prices)])
  try:
   for opp in d['opponents']:
    for f in roots:
     if f['variant']!=p['variant']:continue
     for c in [0,1]:
      e.begin_game();eu.begin_game();g=native_game(e,eu if opp=='unit_search' else None,e.w,f,c,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(profile=p['name'],opponent=opp,pool=f['phase'],cap=24);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());n+=1;go+=len(g['queries'])
  finally:qj.flush();os.fsync(qj.fileno());e.close();eu.close()
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');out=dict(status='ALL176_REDUCED_HELDOUT_GAMES_CLOSED',actual_games=n,actual_go=go,seconds=time.monotonic()-start);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out);assert n==176
