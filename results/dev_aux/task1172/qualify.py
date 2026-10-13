"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1175';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1172/plan.json').read_bytes())

import random
BINARY=R/'.local_agent/leaf-native41/fairy-leaf-native.exe'
def inside(s):return chess.square_file(s)<8 and chess.square_rank(s)<8
def legal5(b):return sorted(m.uci() for m in b.legal_moves if inside(m.from_square) and inside(m.to_square))
def fen5(b):return b.fen()
def term5(b):
 legal=legal5(b)
 if not legal:return dict(kind='CHECKMATE' if b.is_check() else 'STALEMATE',winner=not b.turn if b.is_check() else None)
 if b.is_insufficient_material():return dict(kind='SUFFICIENT_MATERIAL_INSUFF_DRAW',winner=None)
 if b.is_repetition(3):return dict(kind='THREEFOLD_AUTO',winner=None)
 if b.halfmove_clock>=100:return dict(kind='FIFTY_MOVE_AUTO',winner=None)
 return None
def config5(e,w,out):
 line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config=out/'variant.ini';config.write_text('[aux_full:chess]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n',encoding='utf-8')
 for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_full')]:
  e.send('setoption name '+name+' value '+str(value));reply=e.ready()
  if name=='UCI_Variant':assert any(x.startswith('info string variant aux_full files 8 ranks 8 ') for x in reply);ack=[x for x in reply if x.startswith('info string DEV_AUX alignment ')];assert len(ack)==1
 f=ack[0].split();assert int(f[4])==3;assert {int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]}=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 probes=[]
 for piece in 'NR':
  e.send('position fen 4k3/8/8/8/2'+piece+'5/8/8/K7 w - - 0 1');e.send('eval');r=e.ready();v=[x for x in r if x.startswith('Final evaluation')];assert len(v)==1;measured=float(v[0].split()[2]);assert abs(measured-w[piece]/208)<=.011;probes.append(dict(piece=piece,measured=measured,expected=w[piece]/208,raw=r))
 return dict(raw=ack[0],probes=probes,weights=w)


roots=json.loads((R/'results/dev_aux/task1173/roots.json').read_bytes())['roots'];start=time.monotonic();deadline=start+60;rows=[];acks=[]
for price in D['prices']:
 e=M.start(BINARY,3,deadline,P.stop)
 try:
  ack=config5(e,dict(P=1664,N=720,B=1664,R=price,Q=1664,K=0),O);acks.append(dict(price=price,ack=ack))
  for r in roots:
   e.send('position fen '+r['fen5']);e.send('go perft 1');raw=e.until(lambda x:'Nodes searched:' in x,max_lines=200);moves=sorted(m.group(1) for line in raw if (m:=__import__('re').fullmatch(r'([a-h][1-8][a-h][1-8][qrbn]?):\s*(\d+)',line.strip())));assert moves==r['legal'];rows.append(dict(seed=r['seed'],price=price,native_legal=moves,raw=raw))
 finally:e.close()
(O/'qualification.json').write_text(json.dumps(dict(status='PASS_ALL32_NEW_UNIFORM_ROOTS_AT3_NATIVE_PRICES',actual_perft_go=len(rows),acks=acks,rows=rows,seconds=time.monotonic()-start,scope='Before replicationgames; literal1174eligibilityrecord retained; profileleafACKverifiedduringgameconfiguration.'),indent=2));print('QUALIFIED',len(rows))
