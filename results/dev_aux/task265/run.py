import json,time,sys,importlib.util,hashlib,math
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task265';assert not (O/'result.json').exists();D=json.loads((O/'declaration.json').read_bytes());s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+600;P.stop();rows=[];out=dict(complete=False,rows=rows)
def configure(e,w):
 assert set(w)==set('PNBRQK') and type(w['K']) is int and w['K']==0
 assert all(type(w[k]) is int and 32<=w[k]<=4096 for k in 'PNBRQ')
 P.A.guard(deadline,P.stop);line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config=O/'variant.ini';config.write_text('[aux_short:chess]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n',encoding='utf-8')
 for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_short')]:
  e.send('setoption name '+name+' value '+str(value));reply=e.ready()
  if name=='UCI_Variant':assert any(z.startswith('info string variant aux_short files 8 ranks 8 ') for z in reply)
 probes=[]
 for kind in 'PNBRQ':
  fen='7k/8/8/3'+kind+'4/8/8/8/K7 w - - 0 1';e.send('position fen '+fen);e.send('eval');rr=e.ready();v=[z for z in rr if z.startswith('Final evaluation')];assert len(v)==1;value=float(v[0].split()[2]);assert math.isfinite(value) and abs(value-w[kind]/208)<.011;probes.append(dict(type=kind,fen=fen,measured_white_pawns=value,expected_white_pawns=w[kind]/208))
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready();ack=[z for z in reply if z.startswith('info string DEV_AUX alignment ')];assert len(ack)==1;tokens=ack[0].split();assert int(tokens[4])==3;prices={int(z.split(':')[0]):tuple(map(int,z.split(':')[1:])) for z in tokens[5:]};assert prices=={i+1:(w[k],w[k]) for i,k in enumerate('PNBRQ')};e.send('ucinewgame');e.ready();return probes,dict(raw=ack[0],prices={str(k):list(v) for k,v in prices.items()},alignment=3)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for name,w in D['profiles'].items():
  e=P.M.start(binary,3,deadline,P.stop)
  try:
   for f in D['roots']:
    b=chess.Board(f['initial_fen'])
    for text in f['history']:b.push_uci(text)
    assert b.fen()==f['fen']
    for limit in (D['node_limits'] if len(rows)//3%2==0 else list(reversed(D['node_limits']))):
     probes,ack=configure(e,w);ts=time.monotonic();move,meta=P.M.M.search(e,b.copy(stack=True),deadline,P.stop,limit=limit);rows.append(dict(profile=name,weights=w,root=f['id'],move=move.uci(),metadata=meta,wall_seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack));save()
  finally:e.close()
  print(name,len(rows),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
