"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1125';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1123/plan.json').read_bytes())

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
if __name__=='__main__':
 roots=[];trace=[];counts=[0]*4;types=[[6,4,4,2,2,6,4,4,2,2],[6,4,2,2,2,6,4,2,2,2],[6,4,4,2,6,4,4,2],[6,4,2,6,4,2]];colors=[[1]*5+[0]*5,[1]*5+[0]*5,[1]*4+[0]*4,[1]*3+[0]*3]
 for i,seed in enumerate(D['seeds']):
  ci=i%4;sq=random.Random(seed).sample([chess.square(f,r) for r in range(5) for f in range(5)],len(types[ci]));b=chess.Board(None)
  for s,t,c in zip(sq,types[ci],colors[ci]):b.set_piece_at(s,chess.Piece(t,bool(c)))
  b.turn=not((i//4)%2);legal=legal5(b);capture=[u for u in legal if b.is_capture(chess.Move.from_uci(u))];failure=None
  if not b.is_valid():failure='invalid'
  elif term5(b):failure='terminal'
  elif len(legal)<2:failure='too_few_legal'
  elif {b.piece_type_at(chess.Move.from_uci(u).to_square) for u in capture}!={2,4}:failure='missing_R_or_N_capture'
  else:
   for u in legal:
    actor=b.turn;b.push_uci(u);t=term5(b);b.pop()
    if t and t['winner']==actor:failure='immediate_win';break
  row=dict(composition=D['compositions'][ci],types=types[ci],colors=colors[ci],index=i,seed=seed,squares=sq,fen8=b.fen(),fen5=fen5(b),legal=legal,captures=capture,failure=failure);trace.append(row)
  if failure is None and counts[ci]<16:
   n=counts[ci];roots.append(dict(row,ordinal=len(roots),composition_ordinal=n,phase='new_replication'));counts[ci]+=1
 assert counts==[16]*4
 (O/'roots.json').write_text(json.dumps(dict(roots=roots,trace=trace),indent=2),encoding='utf-8');print('NEXT_INPUTS',len(roots),counts)
