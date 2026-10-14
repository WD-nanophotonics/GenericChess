"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1357';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1353/plan.json').read_bytes())

import random
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

import os,random
assert json.loads((R/'results/dev_aux/task1356/qualification.json').read_bytes())['actual_perft_go']==128
plan=D;roots=json.loads((R/'results/dev_aux/task1354/roots.json').read_bytes())['roots'][:64];assert len(roots)==64
start_time=time.monotonic();deadline=start_time+plan["max_seconds"];closed=go=0;rows=[];acks=[];complete=False;error=None

def search5(e,b):
 e.send('position fen '+fen5(b.root())+' moves '+' '.join(m.uci() for m in b.move_stack));e.send('go nodes 4096');lines=e.until(lambda x:x.startswith('bestmove '));move=lines[-1].split()[1];assert move in legal5(b);e.ready();return move,dict(root_fen5=fen5(b.root()),root_fen8=b.root().fen(),full_history=[m.uci() for m in b.move_stack],command='go nodes 4096',uci_info=lines[:-1])
with (O/'queries.jsonl').open('x',encoding='utf-8') as qj,(O/'games.jsonl').open('x',encoding='utf-8') as gj:
 try:
  for arm,profile in plan['profiles'].items():
   price=profile['leafR']
   w=dict(P=1664,N=720,B=1664,R=price,Q=1664,K=0);nativeR=profile["nativeR"];nw=dict(w,R=nativeR);ow=dict(P=1664,N=720,B=1664,R=720,Q=1664,K=0)
   for opp in ['unit_search','uniform_random']:
    opponent_price=plan['opponents'][opp]
    e=M.start(BINARY,3,deadline,P.stop);eu=None
    try:
     ack=config5(e,nw,O);e.send('devauxleafr '+str(price));read=e.ready();leafack=next(x for x in read if x.startswith('info string DEV_AUX leafR '));assert leafack==f'info string DEV_AUX leafR {price} nativeR {nativeR} captureR {nativeR}'
     for piece,expect in [('N',720),('R',price)]:
      e.send('position fen 4k3/8/8/8/2'+piece+'5/8/8/K7 w - - 0 1');e.send('eval');read=e.ready();measured=float(next(x for x in read if x.startswith('Final evaluation')).split()[2]);assert abs(measured-expect/208)<=.011
     acks.append(dict(arm=arm,price=price,player='candidate',ack=ack,leafack=leafack))
     if opp!='uniform_random':eu=M.start(BINARY,3,deadline,P.stop);acks.append(dict(arm=arm,price=price,player='unit',ack=config5(eu,ow,O)))
     for root in roots:
      for color in ([False,True] if root['beneficiary'] is None else [root['beneficiary']]):
       for eng in [e,eu]:
        if eng:eng.send('ucinewgame');eng.ready()
       b=chess.Board(root['fen8']);acts=[];queries=[];rt=0;name=f'{arm}-{price}-{opp}-{root["seed"]}-{root["variant"]}-{int(color)}'
       for ply in range(24):
        A.guard(deadline,P.stop)
        if term5(b):break
        actor=b.turn;before=b.fen();draw=None
        if actor==color or eu is not None:
         move,meta=search5(e if actor==color else eu,b.copy(stack=True));q=dict(game=name,ply=ply,player='candidate' if actor==color else 'unit',weights=w if actor==color else ow,native_weights=nw if actor==color else ow,move=move,metadata=meta);qj.write(json.dumps(q)+'\n');qj.flush();os.fsync(qj.fileno());queries.append(q);go+=1
        else:
         legal=legal5(b);seed=(2026419000+2*root['seed']+int(color))*100+rt;idx=random.Random(seed).randrange(len(legal));move=legal[idx];draw=dict(seed=seed,index=idx,legal=legal,opponent_turn=rt);rt+=1
        assert move in legal5(b);b.push_uci(move);acts.append(dict(actor=actor,move=move,before=before,after=b.fen(),draw=draw))
       term=term5(b);label='C' if term is None else 'D' if term['winner'] is None else 'W' if term['winner']==color else 'L';g=dict(game=name,root=root,arm=arm,profile=arm,nativeR=nativeR,leafR=price,price=price,opponent=opp,color=color,weights=w,actions=acts,queries=queries,termination=term or dict(kind='cap24',winner=None),label=label,final_fen=b.fen());gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());closed+=1;rows.append(dict(game=name,arm=arm,price=price,opponent=opp,seed=root['seed'],color=color,label=label,plies=len(acts)))
    finally:e.close();
    if eu:eu.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');(O/'result.json').write_text(json.dumps(dict(complete=complete,error=error,closed_games=closed,actual_go=go,seconds=time.monotonic()-start_time,rows=rows),indent=2),encoding='utf-8');print('MINI_PILOT',closed,go,complete,error,round(time.monotonic()-start_time,3))
