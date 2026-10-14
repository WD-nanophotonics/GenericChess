"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1302';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1301/plan.json').read_bytes())

import random
from fractions import Fraction as F
BINARY=R/'.local_agent/leaf-4096-43/fairy-leaf-4096.exe'
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

def tradeoff(b):
 color=b.turn;tree={}
 def leaf():
  legal=legal5(b)
  if not legal:return dict(terminal=(-1 if b.turn==color else 1) if b.is_check() else 0)
  if b.is_insufficient_material():return dict(terminal=0)
  return dict(R=len(b.pieces(4,color))-len(b.pieces(4,not color)),N=len(b.pieces(2,color))-len(b.pieces(2,not color)))
 for u in legal5(b):
  b.push_uci(u);ll=legal5(b)
  if not ll or b.is_insufficient_material():tree[u]=[leaf()]
  else:
   tree[u]=[]
   for v in ll:b.push_uci(v);tree[u].append(leaf());b.pop()
  b.pop()
 aff={(q['R'],q['N']) if 'terminal' not in q else (0,0) for ls in tree.values() for q in ls if 'terminal' not in q or q['terminal']==0}
 low,high=F(1,2),F(256,45);cuts={low,high}
 for a,bb in aff:
  for c,d in aff:
   if a!=c:
    x=F(d-bb,a-c)
    if low<x<high:cuts.add(x)
 cuts=sorted(cuts);cells=[];common=set(tree)
 def val(q,x):return F(q['terminal']*1000000) if 'terminal' in q else q['R']*x+q['N']
 for a,bb in zip(cuts,cuts[1:]):
  x=(a+bb)/2;score={u:min(val(q,x) for q in ls) for u,ls in tree.items()};mx=max(score.values());best={u for u,v in score.items() if v==mx};common &= best
  cells.append(dict(interval=[str(a),str(bb)],opt=sorted(best)))
 return dict(tree=tree,cells=cells,universal_optimal_actions=sorted(common),has_tradeoff=not common)
roots=[];trace=[];families=[]
types=[6,4,4,2,2,6,4,4,2,2];colors=[1]*5+[0]*5
for i,seed in enumerate(D['seeds']):
 sq=contactdraw(seed,types,colors);b=chess.Board(None)
 for pos,typ,col in zip(sq,types,colors):b.set_piece_at(pos,chess.Piece(typ,bool(col)))
 b.turn=not(i%2);legal=legal5(b);cap=[u for u in legal if b.is_capture(chess.Move.from_uci(u))];failure=None;symbolic=None
 if not b.is_valid():failure='invalid'
 elif term5(b):failure='terminal'
 elif len(legal)<2:failure='too_few_legal'
 elif {b.piece_at(chess.Move.from_uci(u).to_square).piece_type for u in cap} < {2,4}:failure='missing_both_R_N_capture_targets'
 else:
  for u in legal:
   actor=b.turn;b.push_uci(u);t=term5(b);b.pop()
   if t and t['winner']==actor:failure='immediate_win';break
  if failure is None:
   symbolic=tradeoff(b)
   if not symbolic['has_tradeoff']:failure='no_D2_symbolic_exchange_conflict'
 row=dict(seed=seed,index=i,squares=sq,types=types,colors=colors,variant='exchange_conflict',beneficiary=None,composition='KRRNNvKRRNN',fen8=b.fen(),fen5=b.fen(),legal=legal,captures=cap,failure=failure,symbolic=symbolic)
 trace.append(row)
 if failure is None and len(families)<D['first_families']:
  family_ordinal=len(families);families.append(seed);roots.append(dict(row,ordinal=len(roots),family_ordinal=family_ordinal,composition_ordinal=family_ordinal,phase='TRAIN' if family_ordinal<16 else 'DEV'))
assert len(families)==D['first_families']
(O/'roots.json').write_text(json.dumps(dict(roots=roots,trace=trace,families=families),indent=2));print('EXCHANGE_CONFLICT_INPUTS',len(roots),sum(x['failure'] is None for x in trace))
