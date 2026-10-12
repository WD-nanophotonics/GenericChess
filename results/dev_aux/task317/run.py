"""Finish declared panel with fresh process per weight; reuse18 real prior calls."""
import json,time,sys,math,os
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task313'));import run as Q
O=R/'results/dev_aux/task317';O.mkdir(exist_ok=False);Q.P.stop();d=json.loads((R/'results/dev_aux/task315/declaration.json').read_bytes());d.update(task_id='317',calls_new=158,calls_reused=18,recovery='316actualreadbacks/source show same-name immutable VariantMap. Freshprocessperweight; reuse2valid315P-rows and16bases313, neverreruncompletequeries.',source317='OwnfrozenFairy c378... unchanged; config267 unchanged; scope315 unchanged.');Q.write(O/'declaration.json',d);prior=json.loads((R/'results/dev_aux/task315/result.json').read_bytes())['rows'];start=time.monotonic();deadline=start+300;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task267/configure.py').read_text(),'configure267','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,actual_new_queries=0,reused315_queries=2,reused313_queries=16,rows=rows);e=None
try:
 with (O/'queries.jsonl').open('x',encoding='utf-8') as log:
  for ri,f in enumerate(d['roots']):
   for name in (list(d['profiles']) if ri%2==0 else list(reversed(d['profiles']))):
    for variant in (d['variants'] if ri%2==0 else list(reversed(d['variants']))):
     w=d['profiles'][name].copy();w[variant[0]]+=8 if variant[1]=='+' else -8
     e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
     try:
      for limit in (d['node_limits'] if ri%2==0 else list(reversed(d['node_limits']))):
       old=next((z for z in prior if (z['root'],z['profile'],z['variant'],z['nodes_limit'])==(f['id'],name,variant,limit)),None)
       if old is not None:row=dict(old,historical=True,source='315');rows.append(row);continue
       probes,ack=configure(e,w);b=Q.board(f);ts=time.monotonic();m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=limit);row=dict(root=f['id'],profile=name,variant=variant,weights=w,nodes_limit=limit,move=m.uci(),metadata=meta,leaf_probes=probes,table_ack=ack,wall_seconds=time.monotonic()-ts,historical=False);log.write(json.dumps(row,separators=(',',':'))+'\n');log.flush();os.fsync(log.fileno());out['actual_new_queries']+=1;row['score']=Q.score(meta);rows.append(row)
     finally:e.close();e=None
    print(f['id'],name,out['actual_new_queries'],round(time.monotonic()-start,3),flush=True)
 out['complete']=True
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
finally:
 if e:e.close()
 out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)