"""Small frozen price/budget response panel on new train roots."""
import json,time,math,sys,importlib.util,chess
from pathlib import Path
R=Path.cwd();sp=importlib.util.spec_from_file_location('q337',R/'results/dev_aux/task313/run.py');Q=importlib.util.module_from_spec(sp);sp.loader.exec_module(Q);O=R/'results/dev_aux/task337';assert not (O/'declaration.json').exists();D0=json.loads((R/'results/dev_aux/task335/declaration.json').read_bytes());profiles=D0['initials'].copy();w=profiles['unit'].copy();w['N']*=2;w['B']*=2;profiles['unit-NB-double']=w;D=dict(task_id='337',roots=D0['train_roots'][:2],profiles=profiles,node_limits=[1024,8192],calls=16,question='Are prices responsive at low and higher fixedbudget before quantity optimization?',whole_fuse_seconds=300,scope='First2algorithmic roots fixedbeforequery; threeinitials pluspredeclaredjointN/Bdouble. Exactsamebinary/readbacks/fullhistory/coldmode3; actualdepth/bounds/choices recorded. Highbudget changesworkandselectivity, notexactpricegradient/control or human fitting. No secondhorizon/model choice.');Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+300;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,rows=rows)
try:
 for name,w in profiles.items():
  e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
  try:
   for ri,f in enumerate(D['roots']):
    for limit in D['node_limits']:
     probes,ack=configure(e,w);b=Q.P.board(f);m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=limit);score=Q.score(meta);assert score['pv'][0]==m.uci();c=b.copy(stack=True)
     for u in score['pv']:assert chess.Move.from_uci(u) in c.legal_moves;c.push_uci(u)
     row=dict(profile=name,root=ri,weights=w,node_limit=limit,move=m.uci(),metadata=meta,score=score,leaf_probes=probes,table_ack=ack);rows.append(row);Q.write(O/'result.json',out)
  finally:e.close()
 out['complete']=True
finally:out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
print(json.dumps(dict(complete=out['complete'],seconds=out['seconds'],rows=[{k:z[k] for k in ('profile','root','node_limit','move','score')} for z in rows]),indent=2))