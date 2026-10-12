"""Finite UCI-score response pilot; no games, learning, or PV-gradient assumption."""
import json,time,sys,importlib.util,hashlib,math,re,os
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task313'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load('p313',R/'results/dev_aux/task166/run.py')
def write(path,v):P.A.atomic_json(path,v)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def score(meta):
 rows=[]
 for line in meta['uci_info']:
  f=line.split()
  if f[:1]!=['info'] or 'score' not in f or 'pv' not in f:continue
  i=f.index('score');kind=f[i+1];value=int(f[i+2]);assert kind in ('cp','mate')
  rows.append(dict(kind=kind,value=value,depth=int(f[f.index('depth')+1]),bound=('lowerbound' if 'lowerbound' in f else 'upperbound' if 'upperbound' in f else 'exact_report'),pv=f[f.index('pv')+1:],line=line))
 assert rows;return rows[-1]
def board(f):
 b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 assert b.fen()==f['fen'];return b

def execute():
 O.mkdir(exist_ok=False);P.stop();roots=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes())['roots'];prof=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes())['profiles'];binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert sha(binary)=='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460'
 d=dict(task_id='313',roots=roots,profiles={k:prof[k] for k in ('unit','semantic')},node_limits=[1024,16384],calls=16,binary_sha256=sha(binary),alignment=3,threads=1,hash_mib=16,NNUE=False,tablebase=False,cold_per_query=True,whole_fuse_seconds=300,question='Qualify actual finite-budget score format, readbacks and cp quantization before +/-8 price panel.',scope='Experimental Fairy; prices affect leaf and SEE/order; fixed selective pruning remains. Four old exposed related roots; not exact minimax derivative or human price learning.',dependencies={str(p.relative_to(R)):sha(p) for p in [R/'results/dev_aux/task267/configure.py',R/'results/dev_aux/task258/declaration.json',R/'results/dev_aux/task312/next_work.json']})
 write(O/'declaration.json',d);start=time.monotonic();deadline=start+300;env=dict(P=P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task267/configure.py').read_text(),'configure267','exec'),env);configure=env['configure'];out=dict(complete=False,rows=[],actual_queries=0);e=None
 try:
  for ri,f in enumerate(roots):
   for name in (list(d['profiles']) if ri%2==0 else list(reversed(d['profiles']))):
    w=d['profiles'][name];e=P.M.start(binary,3,deadline,P.stop)
    try:
     for limit in (d['node_limits'] if ri%2==0 else list(reversed(d['node_limits']))):
      probes,ack=configure(e,w);b=board(f);ts=time.monotonic();m,meta=P.M.M.search(e,b.copy(stack=True),deadline,P.stop,limit=limit);row=dict(root=f['id'],profile=name,weights=w,nodes_limit=limit,move=m.uci(),metadata=meta,leaf_probes=probes,table_ack=ack,wall_seconds=time.monotonic()-ts);out['rows'].append(row);out['actual_queries']+=1;write(O/'result.json',out);row['score']=score(meta);pvboard=b.copy(stack=True)
      for u in row['score']['pv']:assert chess.Move.from_uci(u) in pvboard.legal_moves;pvboard.push_uci(u)
      assert row['score']['pv'][0]==row['move'];row['PV_leaf_vector']=[len(pvboard.pieces(i+1,b.turn))-len(pvboard.pieces(i+1,not b.turn)) for i in range(5)];write(O/'result.json',out)
      print(f['id'],name,limit,row['score']['kind'],row['score']['value'],meta['reported_depth'],flush=True)
    finally:e.close();e=None
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:
  if e:e.close()
  out['seconds']=time.monotonic()-start;write(O/'result.json',out)
if __name__=='__main__':execute()