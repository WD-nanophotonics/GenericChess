"""Fixed TD endpoints onbothtrain/development; initialcasesreusedexactly, no re-fitting."""
import json,time,math,importlib.util,os
from pathlib import Path
R=Path.cwd();sp=importlib.util.spec_from_file_location('G352',R/'results/dev_aux/task335/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task352';assert not (O/'declaration.json').exists();D0=json.loads((R/'results/dev_aux/task350/declaration.json').read_bytes());E=json.loads((R/'results/dev_aux/task350/endpoints.json').read_bytes());assert E['complete'];DEV=json.loads((R/'results/dev_aux/task335/declaration.json').read_bytes())['development_roots'];profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':ep['weights'] for k,ep in E['endpoints'].items()}};cache={}
def key(w,phase,ri,color):return tuple(w[k] for k in 'PNBRQK'),phase,ri,color
for t,phase in [(335,'train'),(342,'development')]:
 X=json.loads((R/f'results/dev_aux/task{t}/result.json').read_bytes());assert X['complete']
 for z in X['calls']:
  if z['name'].startswith('endpoint-'):continue
  assert t!=335 or z['termination']in('CHECKMATE','UNKNOWN_CUTOFF');cache[key(z['weights'],phase,z['root'],z['color'])]=dict(z,source=str(t))
D=dict(task_id='352',question='Do allfrozenTD-directed endpoints actuallyimprove SAMEfinitegoal ontrain/development?',roots={'train':D0['roots'],'development':DEV},profiles=profiles,unit=D0['unit'],colors=[True,False],cap=24,node_limit=1024,whole_fuse_seconds=600,endpoint_sha256=Q.sha(R/'results/dev_aux/task350/endpoints.json'),reuse='ALLexactsameinitialprofiles from335train48and342development48, notnewphysicalgames.335actualno ruleDRAW verifies338/350drawzero compatibility. No temporaltraining episodes reusedasfixedendpoint tests.',scope='ALLthreeinitial/endpointtables, no human/model selection ornewepochs. Trainreuse/exposeddevelopment clearlylabeled; outcomesnotusedfor350updates. SameFairy1024/coldTT/leafpriceacks/fullhistory andfixedunitopponent. Candidatefreshprocesspereachprice. 192logicalcases, atmost96actualnewendpointgames, estimated30s.')
Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];actual=queries=reused=0;out=dict(complete=False,calls=rows);eu=None
try:
 eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
 with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
  for name,w in profiles.items():
   ec=None
   try:
    for phase,roots in D['roots'].items():
     for ri,f in enumerate(roots):
      for color in D['colors']:
       kk=key(w,phase,ri,color)
       if kk in cache:z=cache[kk];reused+=1
       else:
        if ec is None:ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
        journal.write(json.dumps(dict(event='game_start',name=name,phase=phase,root=ri,color=color,weights=w),separators=(',',':'))+'\n');journal.flush();z=dict(source='352',**G.run_game(ec,eu,w,D['unit'],f,color,deadline,configure,journal));
        if z['termination']not in('CHECKMATE','UNKNOWN_CUTOFF'):z['fitness']='0'
        cache[kk]=z;actual+=1;queries+=len(z['search_records']);journal.flush();os.fsync(journal.fileno())
       rows.append(dict(z,name=name,phase=phase,root=ri))
   finally:
    if ec:ec.close()
   Q.write(O/'result.json',dict(out,actual_games=actual,actual_queries=queries,reused_cases=reused));print(name,len(rows),actual,round(time.monotonic()-start,3),flush=True)
 out['complete']=True
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
finally:
 if eu:eu.close()
 out.update(actual_games=actual,actual_queries=queries,reused_cases=reused,seconds=time.monotonic()-start);Q.write(O/'result.json',out)