"""Frozen mature deployment on exposed development roots, same true fastmate goal."""
import json,time,sys,os,math,importlib.util
from pathlib import Path
R=Path.cwd();sp=importlib.util.spec_from_file_location('g327',R/'results/dev_aux/task320/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task327'
def execute():
 O.mkdir(exist_ok=False);Q.P.stop();E=json.loads((R/'results/dev_aux/task322/endpoints.json').read_bytes());assert E['complete'];D0=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());old=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes());roots=old['roots'][2:];profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':v['weights'] for k,v in E['endpoints'].items()}};unique={};aliases={}
 for name,w in profiles.items():
  kk=tuple(w[k] for k in 'PNBRQK')
  if kk not in unique:unique[kk]=name
  aliases[name]=unique[kk]
 D=dict(task_id='327',question='Do everyfrozen322 endpoint improve same-mature1024randommate goal onotheroldroots/newfixedseeds?',roots=roots,profiles=profiles,unique_profiles=list(unique.values()),aliases=aliases,seeds=list(range(2026102391,2026102395)),colors=[True,False],node_limit=1024,cap=48,source_endpoint_sha256=Q.sha(R/'results/dev_aux/task322/endpoints.json'),scope='Allendpoints frozenbeforedevelopment; nobestendpoint/humanfit/newtraining. Theseoldheldpositions alreadyexposedhistorically, notnewroot holdout. Newseeds predeclared322, sameuniformlegalrandrange/coldTTpergo. CompleteD3comparison325 differsbackend/work/evaluatorclamp/terminalscope, overallreferenceonly.',whole_fuse_seconds=600)
 Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(),'configure272','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,calls=rows)
 try:
  with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
   for name in unique.values():
    w=profiles[name];e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     for ri,f in enumerate(roots):
      for color in D['colors']:
       for seed in D['seeds']:
        journal.write(json.dumps(dict(event='game_start',profile=name,root=ri,color=color,seed=seed,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(profile=name,root=ri,**G.run_game(e,w,f,color,seed,1024,deadline,configure,journal=journal));rows.append(row)
    finally:e.close()
    print(name,len(rows),round(time.monotonic()-start,3),flush=True)
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
if __name__=='__main__':execute()