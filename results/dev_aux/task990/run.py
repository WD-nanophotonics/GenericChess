"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task993';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task990/plan.json').read_bytes())
def configure(e,w,deadline):
 assert set(w)==set('PNBRQK') and w['K']==0 and all(isinstance(w[k],int) and 1<=w[k]<=3328 for k in 'PNBRQ')
 config=O/'variant.ini';line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config.write_bytes(('[aux_short:chess]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n').encode())
 names={x.split('option name ',1)[1].split(' type ',1)[0] for x in e.handshake if x.startswith('option name ')}
 for name,v in (('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_short')):
  assert name in names;A.guard(deadline,P.stop);e.send('setoption name '+name+' value '+str(v));reply=e.ready()
  if name=='UCI_Variant':assert any(x.startswith('info string variant aux_short files 8 ranks 8 ') for x in reply)
 probes=[]
 for k in 'PNBRQ':
  fen='7k/8/8/3'+k+'4/8/8/8/K7 w - - 0 1';e.send('position fen '+fen);e.send('eval');reply=e.ready();value=[x for x in reply if x.startswith('Final evaluation')];assert len(value)==1;measured=float(value[0].split()[2]);assert abs(measured-w[k]/208)<=.011
  probes.append(dict(type=k,fen=fen,measured=measured,expected=w[k]/208))
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready();acks=[x for x in reply if x.startswith('info string DEV_AUX alignment ')];assert len(acks)==1
 f=acks[0].split();assert int(f[4])==3;prices={int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]};assert prices=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 e.send('ucinewgame');e.ready();return probes,dict(raw=acks[0],prices=prices,alignment=3)
def search(e,b,arm,deadline):
 A.guard(deadline,P.stop);history=[m.uci() for m in b.move_stack];e.send('position fen '+b.root().fen()+' moves '+' '.join(history));e.send('go '+arm['kind']+' '+str(arm['limit']));lines=e.until(lambda t:t.startswith('bestmove '));chosen=chess.Move.from_uci(lines[-1].split()[1]);assert chosen in b.legal_moves;e.ready()
 nodes=depth=None;score=None
 for text in lines[:-1]:
  f=text.split()
  if 'nodes' in f:nodes=int(f[f.index('nodes')+1])
  if 'depth' in f:depth=int(f[f.index('depth')+1])
  if 'score' in f:
   idx=f.index('score');score=dict(kind=f[idx+1],value=int(f[idx+2]))
 return chosen.uci(),dict(root_fen=b.root().fen(),full_history=history,reported_nodes=nodes,reported_depth=depth,last_score=score,uci_info=lines[:-1],backend=e.backend,search_arm=arm)

if __name__=='__main__':
 binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';digest=hashlib.sha256(binary.read_bytes()).hexdigest();assert digest=='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460'
 roots=json.loads((R/'results/dev_aux/task991/roots.json').read_bytes())['roots'];start_time=time.monotonic();deadline=start_time+180;rows=[];complete=False;error=None
 try:
  for limit in [16,64,256]:
   for price in [90,180,360,1448]:
    w=dict(P=208,N=90,B=208,R=price,Q=208,K=0);e=M.start(binary,3,deadline,P.stop)
    try:
     for root in roots:
      probes,ack=configure(e,w,deadline);b=chess.Board(root['fen']);move,meta=search(e,b,dict(kind='nodes',limit=limit),deadline)
      pv=[]
      for line in meta['uci_info']:
       f=line.split()
       if 'pv' in f:
        bb=b.copy();linepv=f[f.index('pv')+1:]
        for text in linepv:assert chess.Move.from_uci(text) in bb.legal_moves;bb.push_uci(text)
        pv.append(linepv)
      row=dict(limit=limit,price=price,root=root,move=move,metadata=meta,leaf_probes=probes,table_ack=ack,validated_pv=pv)
      with (O/'queries.jsonl').open('a',encoding='utf-8') as j:j.write(json.dumps(row)+'\n');j.flush()
      rows.append(dict(limit=limit,price=price,seed=root['seed'],phase=root['phase'],move=move))
    finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 (O/'result.json').write_text(json.dumps(dict(complete=complete,error=error,actual_go=len(rows),seconds=time.monotonic()-start_time,rows=rows,binary_sha256=digest),indent=2),encoding='utf-8');print(dict(complete=complete,error=error,go=len(rows)))
