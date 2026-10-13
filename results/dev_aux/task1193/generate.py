"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1194';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1193/plan.json').read_bytes())

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


def contactdraw(seed,types,colors):
 rng=random.Random(seed);wk=next(i for i,(t,c) in enumerate(zip(types,colors)) if t==6 and c);bk=next(i for i,(t,c) in enumerate(zip(types,colors)) if t==6 and not c);a=rng.randrange(64)
 dist=lambda s,t:max(abs(s%8-t%8),abs(s//8-t//8))
 b=rng.choice([s for s in range(64) if 2<=dist(s,a)<=3]);pool=[s for s in range(64) if s not in [a,b] and min(dist(s,a),dist(s,b))<=2];sample=iter(rng.sample(pool,len(types)-2));return [a if i==wk else b if i==bk else next(sample) for i in range(len(types))]

roots=[];trace=[];families=[]
types=[6,4,2,6,4,2,2];colors=[1,1,1,0,0,0,1]
for i,seed in enumerate(D['seeds']):
 sq=contactdraw(seed,types,colors);profiles=[];failures=[]
 for variant in D['variants']:
  add=variant!='none';t=4 if variant.endswith('R') else 2;beneficiary=variant.startswith('white') if add else None
  tt=types[:6]+([t] if add else []);cc=colors[:6]+([int(beneficiary)] if add else []);ss=sq[:6]+([sq[6]] if add else [])
  b=chess.Board(None)
  for pos,typ,col in zip(ss,tt,cc):b.set_piece_at(pos,chess.Piece(typ,bool(col)))
  b.turn=not(i%2);legal=legal5(b);cap=[u for u in legal if b.is_capture(chess.Move.from_uci(u))];failure=None
  if not b.is_valid():failure='invalid'
  elif term5(b):failure='terminal'
  elif len(legal)<2:failure='too_few_legal'
  elif not cap:failure='no_capture'
  else:
   for u in legal:
    actor=b.turn;b.push_uci(u);t0=term5(b);b.pop()
    if t0 and t0['winner']==actor:failure='immediate_win';break
  row=dict(seed=seed,index=i,squares=ss,extrasquare=sq[6],types=tt,colors=cc,variant=variant,beneficiary=beneficiary,composition='MATCHED_KRN',fen8=b.fen(),fen5=b.fen(),legal=legal,captures=cap,failure=failure);profiles.append(row);failures.append(failure)
 trace.append(dict(seed=seed,index=i,squares=sq,profiles=profiles,eligible=all(x is None for x in failures)))
 if all(x is None for x in failures) and len(families)<D['first_families']:
  family_ordinal=len(families);families.append(seed)
  for row in profiles:roots.append(dict(row,ordinal=len(roots),family_ordinal=family_ordinal,composition_ordinal=family_ordinal,phase='matched_stock'))
assert len(families)==D['first_families']
(O/'roots.json').write_text(json.dumps(dict(roots=roots,trace=trace,families=families),indent=2));print('MATCHED_INPUTS',len(families),len(roots),sum(x['eligible'] for x in trace))
