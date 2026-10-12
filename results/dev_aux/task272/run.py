import json,time,hashlib,importlib.util,math
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task272';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+180;env=dict(P=P,O=O,deadline=deadline,math=math);exec(compile((O/'configure.py').read_text(),str(O/'configure.py'),'exec'),env);configure=env['configure'];rows=[]
try:
 for name,pr in D['profiles'].items():
  e=P.M.start(binary,3,deadline,P.stop)
  try:
   for f in D['roots']:
    b=chess.Board(f['initial_fen'])
    for text in f['history']:b.push_uci(text)
    assert b.fen()==f['fen']
    for limit in D['node_limits']:
     probes,ack=configure(e,pr['weights']);ts=time.monotonic();m,v=P.M.M.search(e,b.copy(stack=True),deadline,P.stop,limit=limit);rows.append(dict(profile=name,weights=pr['weights'],root=f['id'],limit=limit,action=m.uci(),metadata=v,leaf_probes=probes,table_ack=ack,seconds=time.monotonic()-ts))
  finally:e.close()
  print(name,len(rows),round(time.monotonic()-start,3),flush=True)
 out=dict(complete=True,rows=rows,seconds=time.monotonic()-start);P.A.atomic_json(O/'result.json',out);print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:P.A.atomic_json(O/'result.json',dict(complete=False,rows=rows,seconds=time.monotonic()-start,failure=dict(type=type(ex).__name__,message=str(ex))));raise
