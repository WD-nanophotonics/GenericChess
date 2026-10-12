"""Same-resource development of all frozen quantity endpoints."""
import json,time,sys,math,os,importlib.util
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();sp=importlib.util.spec_from_file_location('G342',R/'results/dev_aux/task335/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task342'
def execute():
 assert not (O/'execution.json').exists();Q.P.stop();D=json.loads((O/'declaration.json').read_bytes());D0=json.loads((R/'results/dev_aux/task338/declaration.json').read_bytes());E=json.loads((R/'results/dev_aux/task338/endpoints.json').read_bytes());assert E['complete'];profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':v['weights'] for k,v in E['endpoints'].items()}};unique={};aliases={}
 for name,w in profiles.items():
  kk=tuple(w[k] for k in 'PNBRQK')
  if kk not in unique:unique[kk]=name
  aliases[name]=unique[kk]
 Q.write(O/'execution.json',dict(profiles=profiles,unique_profiles=list(unique.values()),aliases=aliases,unit=D0['unit'],endpoint_sha256=Q.sha(R/'results/dev_aux/task338/endpoints.json')));start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,calls=rows);eu=None
 try:
  eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
  with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
   for name in unique.values():
    w=profiles[name];ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     for ri,f in enumerate(D['roots']):
      for color in D['colors']:
       journal.write(json.dumps(dict(event='game_start',name=name,root=ri,color=color,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(name=name,root=ri,**G.run_game(ec,eu,w,D0['unit'],f,color,deadline,configure,journal));
       if row['termination'] not in ('CHECKMATE','UNKNOWN_CUTOFF'):row['fitness']='0'
       rows.append(row);journal.flush();os.fsync(journal.fileno())
    finally:ec.close()
    Q.write(O/'result.json',out);print(name,len(rows),round(time.monotonic()-start,3),flush=True)
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:
  if eu:eu.close()
  out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
if __name__=='__main__':execute()