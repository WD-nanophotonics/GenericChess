"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1212';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1211/plan.json').read_bytes())

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


def search5(e, b):
    e.send('position fen ' + fen5(b.root()) + ' moves ' + ' '.join((m.uci() for m in b.move_stack)))
    e.send('go nodes 256')
    lines = e.until(lambda x: x.startswith('bestmove '))
    move = lines[-1].split()[1]
    assert move in legal5(b)
    e.ready()
    return (move, dict(root_fen5=fen5(b.root()), root_fen8=b.root().fen(), full_history=[m.uci() for m in b.move_stack], command='go nodes 256', uci_info=lines[:-1]))
import re
roots=json.loads((R/'results/dev_aux/task1186/roots.json').read_bytes())['roots'][:12];start=time.monotonic();deadline=start+90;rows=[];acks=[];probes=[]
binaries=[R/'.local_agent/leaf-native41/fairy-leaf-native.exe',R/'.local_agent/leaf-4096-43/fairy-leaf-4096.exe']
for profile in D['profiles']:
 w=dict(P=1664,N=720,B=1664,R=profile['nativeR'],Q=1664,K=0);xx=[]
 for binary in binaries:
  e=M.start(binary,3,deadline,P.stop);one=[]
  try:
   ack=config5(e,w,O);acks.append(dict(binary=binary.name,profile=profile,ack=ack))
   if profile['leafR'] is not None:
    e.send('devauxleafr '+str(profile['leafR']));read=e.ready();assert f"info string DEV_AUX leafR {profile['leafR']} nativeR {profile['nativeR']} captureR {profile['nativeR']}" in read
   for r in roots:
    e.send('ucinewgame');e.ready();move,meta=search5(e,chess.Board(r['fen8']));rows.append(dict(binary=binary.name,profile=profile,seed=r['seed'],move=move,metadata=meta))
    one.append(dict(move=move,info=[re.sub(r'\b(time|nps) \d+','',v) for v in meta['uci_info']]))
  finally:e.close()
  xx.append(one)
 assert xx[0]==xx[1]
e=M.start(binaries[1],3,deadline,P.stop)
try:
 ack=config5(e,dict(P=1664,N=720,B=1664,R=720,Q=1664,K=0),O)
 for price in [3407,4096]:
  e.send('devauxleafr '+str(price));read=e.ready();assert f"info string DEV_AUX leafR {price} nativeR 720 captureR 720" in read;e.send('position fen 4k3/8/8/8/2R5/8/8/K7 w - - 0 1');e.send('eval');ev=e.ready();value=float(next(v for v in ev if v.startswith('Final evaluation')).split()[2]);assert abs(value-price/208)<=.011;probes.append(dict(price=price,raw=read+ev,value=value))
 for price in [0,4097]:
  e.send('devauxleafr '+str(price));read=e.ready();assert 'info string DEV_AUX leafR invalid' in read;e.send('eval');ev=e.ready();value=float(next(v for v in ev if v.startswith('Final evaluation')).split()[2]);assert abs(value-4096/208)<=.011;probes.append(dict(invalid_price=price,raw=read+ev,unchanged_leaf=4096))
finally:e.close()
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL36_OLD_NEW_COLD_DECISION_PAIRS_AND_NEW_BOUND_READBACK',actual_search_go=len(rows),pairs=len(rows)//2,acks=acks,rows=rows,probes=probes,seconds=time.monotonic()-start,no_primary_default_changes=True),indent=2));print('BOUND_PASS',len(rows),len(probes))
