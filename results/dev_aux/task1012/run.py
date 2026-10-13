"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1013';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1012/plan.json').read_bytes())
def configure(e,w,deadline):
 assert set(w)==set('PNBRQK') and w['K']==0 and all(isinstance(w[k],int) and 1<=w[k]<=3328 for k in 'PNBRQ')
 config=O/'variant.ini';line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config.write_bytes(('[aux_short:chess]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n').encode())
 names={x.split('option name ',1)[1].split(' type ',1)[0] for x in e.handshake if x.startswith('option name ')}
 for name,v in (('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_short')):
  assert name in names;A.guard(deadline,P.stop);e.send('setoption name '+name+' value '+str(v));reply=e.ready()
  if name=='UCI_Variant':assert any(x.startswith('info string variant aux_short files 8 ranks 8 ') for x in reply)
 probes=[]
 for k in 'PNBRQ':
  fen='7k/8/8/3'+k+'4/8/8/8/K7 w - - 0 1';e.send('position fen '+fen);e.send('eval');reply=e.ready();value=[x for x in reply if x.startswith('Final evaluation')];assert len(value)==1;measured=float(value[0].split()[2]);assert abs(measured-w[k]/208)<=.011
  probes.append(dict(type=k,fen=fen,measured=measured,expected=w[k]/208))
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready();acks=[x for x in reply if x.startswith('info string DEV_AUX alignment ')];assert len(acks)==1
 f=acks[0].split();assert int(f[4])==3;prices={int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]};assert prices=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 e.send('ucinewgame');e.ready();return probes,dict(raw=acks[0],prices=prices,alignment=3)
def search(e,b,arm,deadline):
 A.guard(deadline,P.stop);history=[m.uci() for m in b.move_stack];e.send('position fen '+b.root().fen()+' moves '+' '.join(history));e.send('go '+arm['kind']+' '+str(arm['limit']));lines=e.until(lambda t:t.startswith('bestmove '));chosen=chess.Move.from_uci(lines[-1].split()[1]);assert chosen in b.legal_moves;e.ready()
 nodes=depth=None;score=None
 for text in lines[:-1]:
  f=text.split()
  if 'nodes' in f:nodes=int(f[f.index('nodes')+1])
  if 'depth' in f:depth=int(f[f.index('depth')+1])
  if 'score' in f:
   idx=f.index('score');score=dict(kind=f[idx+1],value=int(f[idx+2]))
 return chosen.uci(),dict(root_fen=b.root().fen(),full_history=history,reported_nodes=nodes,reported_depth=depth,last_score=score,uci_info=lines[:-1],backend=e.backend,search_arm=arm)


import random,os
plan=D;roots=[r for r in json.loads((R/'results/dev_aux/task1008/roots.json').read_bytes())['roots'] if r['composition_ordinal']<8];assert len(roots)==32
start_time=time.monotonic();deadline=start_time+600;closed=go=0;complete=False;error=None;rows=[];acks=[]
with (O/'queries.jsonl').open('x',encoding='utf-8') as qj,(O/'games.jsonl').open('x',encoding='utf-8') as gj:
 try:
  for price in plan['profiles']:
   w=dict(plan['candidate_other'],R=price)
   for opponent in plan['opponents']:
    e=M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,P.stop);eu=None
    try:
     probes,ack=configure(e,w,deadline);acks.append(dict(player='candidate',price=price,weights=w,probes=probes,ack=ack))
     if opponent=='unit_search':
      eu=M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,P.stop);up,ua=configure(eu,plan['opponent_weights'],deadline);acks.append(dict(player='unit',price=price,weights=plan['opponent_weights'],probes=up,ack=ua))
     for root in roots:
      for color in [False,True]:
       for engine in [e,eu]:
        if engine:engine.send('ucinewgame');engine.ready()
       b=chess.Board(root['fen']);actions=[];queries=[];random_turn=0;name=f'{price}-{opponent}-{root["seed"]}-{int(color)}'
       for ply in range(16):
        A.guard(deadline,P.stop)
        if b.outcome(claim_draw=False) is not None:break
        actor=b.turn;before=b.fen();draw=None
        if actor==color or eu is not None:
         engine=e if actor==color else eu;move,meta=search(engine,b.copy(stack=True),dict(kind='nodes',limit=64),deadline);query=dict(game=name,ply=ply,player='candidate' if actor==color else 'unit',weights=w if actor==color else plan['opponent_weights'],move=move,metadata=meta);qj.write(json.dumps(query)+'\n');qj.flush();os.fsync(qj.fileno());go+=1;queries.append(query)
        else:
         legal=sorted(m.uci() for m in b.legal_moves);seed=(plan['random_seed_base']+2*root['seed']+int(color))*100+random_turn;idx=random.Random(seed).randrange(len(legal));move=legal[idx];draw=dict(seed=seed,index=idx,legal=legal,opponent_turn=random_turn);random_turn+=1
        assert chess.Move.from_uci(move) in b.legal_moves;b.push_uci(move);actions.append(dict(move=move,actor=actor,before=before,after=b.fen(),draw=draw))
       out=b.outcome(claim_draw=False);termination=dict(kind='cap16',winner=None) if out is None else dict(kind=out.termination.name,winner=out.winner);label='C' if out is None else 'D' if out.winner is None else 'W' if out.winner==color else 'L';g=dict(game=name,root=root,price=price,opponent=opponent,color=color,weights=w,actions=actions,queries=queries,termination=termination,label=label,final_fen=b.fen(),cap=16);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());closed+=1;rows.append(dict(game=name,price=price,opponent=opponent,seed=root['seed'],color=color,label=label,plies=len(actions)))
       if closed%32==0:print('GAMES',closed,'GO',go,'SEC',round(time.monotonic()-start_time,2),flush=True)
    finally:
     e.close()
     if eu:eu.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');(O/'result.json').write_text(json.dumps(dict(complete=complete,error=error,closed_games=closed,actual_go=go,seconds=time.monotonic()-start_time,rows=rows,scope='Actualshortfullpolicy trueW-L,noquantity/oraclecutoffreward; coldgame warmwithinfullhistory; standardautomaticdrawsnooptionalclaims'),indent=2),encoding='utf-8');print('CLOSED',closed,go,complete,error)
