"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1019';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1016/plan.json').read_bytes())

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

import os,random
plan=D;roots=json.loads((R/'results/dev_aux/task1017/roots.json').read_bytes())['roots'][:8];assert len(roots)==8
start_time=time.monotonic();deadline=start_time+120;closed=go=0;rows=[];acks=[];complete=False;error=None

def search5(e,b):
 e.send('position fen '+fen5(b.root())+' moves '+' '.join(m.uci() for m in b.move_stack));e.send('go nodes 64');lines=e.until(lambda x:x.startswith('bestmove '));move=lines[-1].split()[1];assert move in legal5(b);e.ready();return move,dict(root_fen5=fen5(b.root()),root_fen8=b.root().fen(),full_history=[m.uci() for m in b.move_stack],command='go nodes 64',uci_info=lines[:-1])
with (O/'queries.jsonl').open('x',encoding='utf-8') as qj,(O/'games.jsonl').open('x',encoding='utf-8') as gj:
 try:
  for price in plan['prices']:
   w=dict(P=208,N=90,B=208,R=price,Q=208,K=0)
   for opp in ['unit_search','uniform_random']:
    e=M.start(BINARY,3,deadline,P.stop);eu=None
    try:
     ack=config5(e,w,O);acks.append(dict(price=price,player='candidate',ack=ack))
     if opp=='unit_search':eu=M.start(BINARY,3,deadline,P.stop);acks.append(dict(price=price,player='unit',ack=config5(eu,dict(w,R=90),O)))
     for root in roots:
      for color in [False,True]:
       for eng in [e,eu]:
        if eng:eng.send('ucinewgame');eng.ready()
       b=chess.Board(root['fen8']);acts=[];queries=[];rt=0;name=f'{price}-{opp}-{root["seed"]}-{int(color)}'
       for ply in range(16):
        A.guard(deadline,P.stop)
        if term5(b):break
        actor=b.turn;before=b.fen();draw=None
        if actor==color or eu is not None:
         move,meta=search5(e if actor==color else eu,b.copy(stack=True));q=dict(game=name,ply=ply,player='candidate' if actor==color else 'unit',weights=w if actor==color else dict(w,R=90),move=move,metadata=meta);qj.write(json.dumps(q)+'\n');qj.flush();os.fsync(qj.fileno());queries.append(q);go+=1
        else:
         legal=legal5(b);seed=(2026159000+2*root['seed']+int(color))*100+rt;idx=random.Random(seed).randrange(len(legal));move=legal[idx];draw=dict(seed=seed,index=idx,legal=legal,opponent_turn=rt);rt+=1
        assert move in legal5(b);b.push_uci(move);acts.append(dict(actor=actor,move=move,before=before,after=b.fen(),draw=draw))
       term=term5(b);label='C' if term is None else 'D' if term['winner'] is None else 'W' if term['winner']==color else 'L';g=dict(game=name,root=root,price=price,opponent=opp,color=color,weights=w,actions=acts,queries=queries,termination=term or dict(kind='cap16',winner=None),label=label,final_fen=b.fen());gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());closed+=1;rows.append(dict(game=name,price=price,opponent=opp,seed=root['seed'],color=color,label=label,plies=len(acts)))
    finally:e.close();
    if eu:eu.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');(O/'result.json').write_text(json.dumps(dict(complete=complete,error=error,closed_games=closed,actual_go=go,seconds=time.monotonic()-start_time,rows=rows),indent=2),encoding='utf-8');print('MINI_PILOT',closed,go,complete,error,round(time.monotonic()-start_time,3))
