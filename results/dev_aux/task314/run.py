"""Frozen +/-8 response panel; 16 pilot bases reused, 160 new actual calls."""
import json,time,sys,math,os
from pathlib import Path
import chess
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task313'));import run as Q
O=R/'results/dev_aux/task314';O.mkdir(exist_ok=False);Q.P.stop();pilot=json.loads((R/'results/dev_aux/task313/result.json').read_bytes());baseD=json.loads((R/'results/dev_aux/task313/declaration.json').read_bytes());assert pilot['complete'] and len(pilot['rows'])==16
# All pilot scores numeric and unbounded, prices acknowledged. No outcome-dependent root expansion.
assert all(x['score']['kind']=='cp' and x['score']['bound']=='exact_report' for x in pilot['rows'])
d=dict(baseD,task_id='314',calls_new=160,calls_reused=16,step=8,variants=[k+s for k in 'PNBRQ' for s in ('-','+')],reason_for_panel='Pilot16 complete/scorecp/every5leafreadback+MG/EGack; +/-8raw is3.846cp for unit feature, observable above integer display bin. Still finite-budget response not gradient.',pilot_sha256=Q.sha(R/'results/dev_aux/task313/result.json'),source_score_cpp_sha256=Q.sha(R/'.local_agent/alignment-order/source/uci.cpp'),score_display='source uci.cpp v*100/PawnValueEg; types.h PawnValueEg=208, integertruncation. Fixeddisplaydenominator; notcandidatePnormalized.')
Q.write(O/'declaration.json',d);start=time.monotonic();deadline=start+300;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task267/configure.py').read_text(),'configure267','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,actual_new_queries=0,reused_pilot_queries=16,rows=rows);e=None
try:
 with (O/'queries.jsonl').open('x',encoding='utf-8') as log:
  for ri,f in enumerate(d['roots']):
   for name in (list(d['profiles']) if ri%2==0 else list(reversed(d['profiles']))):
    e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     variants=d['variants'] if ri%2==0 else list(reversed(d['variants']))
     for variant in variants:
      w=d['profiles'][name].copy();w[variant[0]]+=8 if variant[1]=='+' else -8
      for limit in (d['node_limits'] if ri%2==0 else list(reversed(d['node_limits']))):
       probes,ack=configure(e,w);b=Q.board(f);ts=time.monotonic();m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=limit);row=dict(root=f['id'],profile=name,variant=variant,weights=w,nodes_limit=limit,move=m.uci(),metadata=meta,leaf_probes=probes,table_ack=ack,wall_seconds=time.monotonic()-ts);log.write(json.dumps(row,separators=(',',':'))+'\n');log.flush();os.fsync(log.fileno());out['actual_new_queries']+=1;row['score']=Q.score(meta);rows.append(row)
    finally:e.close();e=None
    print(f['id'],name,out['actual_new_queries'],round(time.monotonic()-start,3),flush=True)
 out['complete']=True
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
finally:
 if e:e.close()
 out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)