"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1126';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1112/plan.json').read_bytes())

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
 f=ack[0].split();assert int(f[4])==3;assert {int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]}=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 probes=[]
 for piece in 'NR':
  e.send('position fen 4k/5/2'+piece+'2/5/K4 w - - 0 1');e.send('eval');r=e.ready();v=[x for x in r if x.startswith('Final evaluation')];assert len(v)==1;measured=float(v[0].split()[2]);assert abs(measured-w[piece]/208)<=.011;probes.append(dict(piece=piece,measured=measured,expected=w[piece]/208,raw=r))
 return dict(raw=ack[0],probes=probes,weights=w)

roots=json.loads((R/'results/dev_aux/task1125/roots.json').read_bytes())['roots'];start=time.monotonic();deadline=start+60;rows=[];acks=[]
for price in [90,164,671]:
 e=M.start(BINARY,3,deadline,P.stop)
 try:
  acks.append(config5(e,dict(P=208,N=90,B=208,R=price,Q=208,K=0),O))
  for r in roots:
   e.send('position fen '+r['fen5']);e.send('go perft 1');raw=e.until(lambda x:'Nodes searched:' in x,max_lines=200);moves=sorted(m.group(1) for line in raw if (m:=__import__('re').fullmatch(r'([a-h][1-8][a-h][1-8][qrbn]?):\s*(\d+)',line.strip())));assert moves==r['legal'];assert [int(line.split(':')[-1]) for line in raw if line.startswith('Nodes searched:')]==[len(moves)];rows.append(dict(price=price,seed=r['seed'],native_legal=moves,raw=raw))
 finally:e.close()
(O/'qualification.json').write_text(json.dumps(dict(status='PASS_ALL192_NEW64_NATIVE_FULL_FRONTIERS_AND_PRICE_READBACKS',actual_perft_go=len(rows),rows=rows,acks=acks,seconds=time.monotonic()-start,binary_sha256=hashlib.sha256(BINARY.read_bytes()).hexdigest(),new_games=0),indent=2),encoding='utf-8');print('NEXT_NATIVE',len(rows))
