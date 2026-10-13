"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1110';O.mkdir(exist_ok=False)
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




start=time.monotonic();deadline=start+60;old=[json.loads(x) for x in (R/'results/dev_aux/task1100/games.jsonl').read_text().splitlines()];roots=json.loads((R/'results/dev_aux/task1098/roots.json').read_bytes())['roots'][:2];rows=[]
def canonical(line):
 f=line.split();out=[];i=0
 while i<len(f):
  if f[i] in ['time','nps']:i+=2
  else:out.append(f[i]);i+=1
 return ' '.join(out)
for price in [64,90]:
 e=M.start(R/'.local_agent/leaf-native41/fairy-leaf-native.exe',3,deadline,P.stop)
 try:
  ack=config5(e,dict(P=208,N=90,B=208,R=price,Q=208,K=0),O)
  for root in roots:
   e.send('ucinewgame');e.ready();b=chess.Board(root['fen8']);e.send('position fen '+root['fen5']);e.send('go nodes 64');raw=e.until(lambda x:x.startswith('bestmove '));e.ready();move=raw[-1].split()[1];g=next(g for g in old if g['price']==price and g['root']['seed']==root['seed'] and g['color']==b.turn and g['opponent']=='unit_search');prior=g['queries'][0];assert prior['player']=='candidate' and prior['metadata']['full_history']==[];assert prior['move']==move and [canonical(x) for x in raw[:-1]]==[canonical(x) for x in prior['metadata']['uci_info']];rows.append(dict(price=price,seed=root['seed'],ack=ack,raw=raw,exact_decision_fields=True))
 finally:e.close()
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL4_UNSET_NEWPRICE_CONTROLS',actual_go=4,rows=rows,seconds=time.monotonic()-start),indent=2),encoding='utf-8');print('DEFAULTCONTROLS',len(rows))
