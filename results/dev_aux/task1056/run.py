"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1057';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1041/plan.json').read_bytes())

import random
BINARY=R/'.local_agent/alignment-order/fairy-order-toggle.exe'
def inside(s):return chess.square_file(s)<5 and chess.square_rank(s)<5
def legal5(b):return sorted(m.uci() for m in b.legal_moves if inside(m.from_square) and inside(m.to_square))
def fen5(b):
 rows=[]
 for rank in range(4,-1,-1):
  text='';empty=0
  for file in range(5):
   pc=b.piece_at(chess.square(file,rank))
   if pc:
    if empty:text+=str(empty);empty=0
    text+=pc.symbol()
   else:empty+=1
  if empty:text+=str(empty)
  rows.append(text)
 return '/'.join(rows)+(' w ' if b.turn else ' b ')+'- - '+str(b.halfmove_clock)+' '+str(b.fullmove_number)
def term5(b):
 legal=legal5(b)
 if not legal:return dict(kind='CHECKMATE' if b.is_check() else 'STALEMATE',winner=not b.turn if b.is_check() else None)
 if len(b.piece_map())==2:return dict(kind='KING_ONLY',winner=None)
 if b.is_repetition(3):return dict(kind='THREEFOLD_AUTO',winner=None)
 if b.halfmove_clock>=100:return dict(kind='FIFTY_MOVE_AUTO',winner=None)
 return None
def config5(e,w,out):
 line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config=out/'variant.ini';config.write_text('[aux_mini:gardner]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n',encoding='utf-8')
 for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_mini')]:
  e.send('setoption name '+name+' value '+str(value));reply=e.ready()
  if name=='UCI_Variant':assert any(x.startswith('info string variant aux_mini files 5 ranks 5 ') for x in reply);ack=[x for x in reply if x.startswith('info string DEV_AUX alignment ')];assert len(ack)==1
 f=ack[0].split();assert int(f[4])==e.alignment;assert {int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]}==({i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')} if e.alignment else {i+1:[a,b] for i,(a,b) in enumerate(zip([126,781,825,1276,2538],[208,854,915,1380,2682]))})
 probes=[]
 for piece in 'NR':
  e.send('position fen 4k/5/2'+piece+'2/5/K4 w - - 0 1');e.send('eval');r=e.ready();v=[x for x in r if x.startswith('Final evaluation')];assert len(v)==1;measured=float(v[0].split()[2]);assert abs(measured-w[piece]/208)<=.011;probes.append(dict(piece=piece,measured=measured,expected=w[piece]/208,raw=r))
 return dict(raw=ack[0],probes=probes,weights=w)



plan=json.loads((R/'results/dev_aux/task1056/plan.json').read_bytes());binary=R/'.local_agent/leaf-native41/fairy-leaf-native.exe';start=time.monotonic();deadline=start+60;rows=[];acks=[];error=None
conditions=[(p,None) for p in [419,1718]]+[(n,l) for n in [419,1718] for l in [419,1718]]
try:
 for native,leaf in conditions:
  w=dict(P=208,N=90,B=208,R=native,Q=208,K=0);e=M.start(binary,3,deadline,P.stop)
  try:
   nativeack=config5(e,w,O);leafack=None
   if leaf is not None:
    e.send('devauxleafr '+str(leaf));r=e.ready();matches=[line for line in r if line.startswith('info string DEV_AUX leafR ')];assert len(matches)==1;assert matches[0]==f'info string DEV_AUX leafR {leaf} nativeR {native} captureR {native}';leafack=matches[0]
    for piece,expected in [('N',90),('R',leaf)]:
     e.send('position fen 4k/5/2'+piece+'2/5/K4 w - - 0 1');e.send('eval');r=e.ready();vv=[x for x in r if x.startswith('Final evaluation')];assert len(vv)==1;assert abs(float(vv[0].split()[2])-expected/208)<=.011
   acks.append(dict(native=native,leaf=leaf,nativeack=nativeack,leafack=leafack))
   for case in plan['cases']:
    e.send('ucinewgame');e.ready();b=chess.Board(case['fen8'])
    for m in case['history']:assert m in legal5(b);b.push_uci(m)
    e.send('position fen '+fen5(b.root())+' moves '+' '.join(case['history']));e.send('go nodes 64');lines=e.until(lambda x:x.startswith('bestmove '));move=lines[-1].split()[1];assert move in legal5(b);e.ready();PV=[];last=None
    for line in lines[:-1]:
     fs=line.split()
     if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0
     if 'pv' in fs:
      bb=b.copy();p=fs[fs.index('pv')+1:]
      for u in p:assert u in legal5(bb);bb.push_uci(u)
      PV.append(p)
     if 'score' in fs:i=fs.index('score');last=dict(kind=fs[i+1],value=int(fs[i+2]),depth=int(fs[fs.index('depth')+1]),nodes=int(fs[fs.index('nodes')+1]))
    rows.append(dict(case=case,native=native,leaf=leaf,actual_leaf=native if leaf is None else leaf,move=move,current_fen8=b.fen(),last=last,printed_PVs=PV,raw=lines))
  finally:e.close()
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
original=json.loads((R/'results/dev_aux/task1053/result.json').read_bytes());controls=[]
if error is None:
 for r in rows:
  if r['leaf'] is not None:continue
  old=next(x for x in original['rows'] if x['mode']==3 and x['price']==r['native'] and x['case']==r['case']);assert old['move']==r['move'] and old['last']==r['last'] and old['printed_PVs']==r['printed_PVs'];controls.append(dict(case=r['case']['id'],price=r['native'],bestmove_cp_depth_nodes_PVs_equal=True))
(O/'result.json').write_text(json.dumps(dict(complete=error is None,actual_go=len(rows),error=error,rows=rows,acks=acks,controls=controls,seconds=time.monotonic()-start,scope=plan['scope']),indent=2),encoding='utf-8');print('STRICT',len(rows),error,len(controls));print([{k:r[k] for k in ['case','native','leaf','move','last']} for r in rows if r['case']['id']=='exposed_changed_witness'])
