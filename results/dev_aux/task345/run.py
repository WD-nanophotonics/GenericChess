"""Fixed higher-budget endpoint transfer; no additional fitting or horizon choice."""
import json,time,math,importlib.util,os
from pathlib import Path
R=Path.cwd();sp=importlib.util.spec_from_file_location('G345',R/'results/dev_aux/task335/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task345';assert not (O/'declaration.json').exists();base=json.loads((R/'results/dev_aux/task342/declaration.json').read_bytes());ex=json.loads((R/'results/dev_aux/task342/execution.json').read_bytes());D=dict(task_id='345',question='Do frozenquantityendpoints retain developmentgains at8xnodebudget?',roots=base['roots'],profiles=ex['profiles'],unique_profiles=ex['unique_profiles'],aliases=ex['aliases'],unit=ex['unit'],colors=[True,False],cap=24,node_limit=8192,whole_fuse_seconds=600,estimated_seconds=60,endpoint_sha256=ex['endpoint_sha256'],goal=base['goal'],scope='ALLfrozen endpoints/initials onSAME8alreadyexposeddevelopmentroots. Onepredeclaredhigherbudget8192 for BOTHplayers, no re-fit/reselection/newroot/gen/horizon. Fixedmaturemode3/coldTT/readbacks/history. Compare3421024aspairedresourcecurve; nonlinear selectivealgorithm/evaluation/order effects remain, no isolatedpruningcausality/IIDconfidence. Usefuldecision: whether703negative andunit/semanticmixedtransfer arebudget-specific; either outcomechangesfuturecheaptrainingdesign, notcurrentmodelselection.')
Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,calls=rows);eu=None
try:
 eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
 with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
  for name in D['unique_profiles']:
   w=D['profiles'][name];ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
   try:
    for ri,f in enumerate(D['roots']):
     for color in D['colors']:
      journal.write(json.dumps(dict(event='game_start',name=name,root=ri,color=color,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(name=name,root=ri,**G.run_game(ec,eu,w,D['unit'],f,color,deadline,configure,journal,limit=8192));
      if row['termination'] not in ('CHECKMATE','UNKNOWN_CUTOFF'):row['fitness']='0'
      rows.append(row);journal.flush();os.fsync(journal.fileno())
   finally:ec.close()
   Q.write(O/'result.json',out);print(name,len(rows),round(time.monotonic()-start,3),flush=True)
 out['complete']=True
except BaseException as er:out['failure']=dict(type=type(er).__name__,message=str(er));raise
finally:
 if eu:eu.close()
 out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)