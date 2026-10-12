import json,time,sys,importlib.util,hashlib,random,datetime
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task264';assert not (O/'result.json').exists();D=json.loads((O/'declaration.json').read_bytes());profiles=D['profiles'];s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+600;rows=[];out=dict(complete=False,rows=rows)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for name,w in profiles.items():
  e=P.M.start(binary,3,deadline,P.stop)
  try:
   for f in D['roots']:
    b=chess.Board(f['initial_fen'])
    for text in f['history']:b.push_uci(text)
    assert b.fen()==f['fen']
    for limit in (D['node_limits'] if len(rows)//3%2==0 else list(reversed(D['node_limits']))):
     probes,ack=P.M.configure(e,w,O/'variant.ini',deadline,P.stop);ts=time.monotonic();move,meta=P.M.M.search(e,b.copy(stack=True),deadline,P.stop,limit=limit);rows.append(dict(profile=name,weights=w,root=f['id'],move=move.uci(),metadata=meta,wall_seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack));save()
  finally:e.close()
  print(name,len(rows),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
