import json,random,time,os
from fractions import Fraction
import cshogi as C
import run as G
import audit as V
PY_DROP={1:1,2:2,3:3,4:4,7:5,5:6,6:7}
HAND=[1,2,3,4,7,5,6]
SYM={1:'p',2:'l',3:'n',4:'s',5:'b',6:'r',7:'g',8:'k',9:'+p',10:'+l',11:'+n',12:'+s',13:'+b',14:'+r'}
def piece(pc):
 if not pc:return None
 s=SYM[pc%16];return s.upper() if pc<16 else s

from pathlib import Path
R=Path.cwd()
ls=(R/'results/dev_aux/task381/audit.py').read_text(encoding='utf-8-sig')
ls=ls[ls.index('def literal('):ls.index('def query(')].replace('sum(owned)==38','sum(owned) in [4,6,8]')
MAP=V.MAP
exec(compile(ls,'reduced_literal','exec'))
V.literal=literal

def native_game(ec,eu,w,f,color,journal,d,deadline=None):
 G.stop();t=time.monotonic();b=C.Board(f['initial_sfen']);states=[' '.join(b.sfen().split()[:3])];movers=[];gave=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,gave) is None;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 assert b.sfen().split()[:3]==f['expected_sfen'].split()[:3];h=list(f['history']);acts=[];queries=[];term=V.terminal(b,states,movers,gave);random_turn=0
 for ply in range(d['cap']):
  if term:break
  if deadline:assert time.monotonic()<deadline,'frozen callerfuse'
  G.stop();actor=b.turn;draw=None
  if actor==color or eu:
   e=ec if actor==color else eu;q=e.search(f['initial_sfen'],h,d['nodes']);V.query(q);assert q['weights']==(w if actor==color else eu.w);q['player']='candidate' if actor==color else 'unit';q['ply']=ply;queries.append(q);u=q['bestmove']
  else:
   legal=sorted(C.move_to_usi(m) for m in b.legal_moves);seed=(d['seed_base']+2*f['index']+color+(100 if f['phase']=='development' else 0))*100+random_turn;rng=random.Random(seed);idx=rng.randrange(len(legal));u=legal[idx];draw=dict(legal=legal,index=idx,seed=seed,opponent_turn=random_turn);random_turn+=1
  m=b.move_from_usi(u);assert b.is_legal(m);before=b.sfen();captured=piece(b.piece(C.move_to(m)));moving=None if C.move_is_drop(m) else piece(b.piece(C.move_from(m)));drop=PY_DROP[HAND[C.move_drop_hand_piece(m)]] if C.move_is_drop(m) else None;movers.append(actor);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));h.append(u);a=dict(move=u,actor=actor,captured=captured,moving=moving,promotion=bool(C.move_is_promotion(m)),drop=drop,before_sfen=before,after_sfen=b.sfen())
  if eu is None:a['random_draw']=draw
  acts.append(a);term=V.terminal(b,states,movers,gave)
 counts=[0,0]
 for pc in b.pieces:
  if pc and pc%16!=8:counts[0 if pc<16 else 1]+=1
 for side,hand in enumerate(b.pieces_in_hand):counts[side]+=sum(hand)
 assert sum(counts)==f["inventory"];qty=counts[color]-counts[1-color];goal=Fraction(qty,19) if term is None else Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==color else -32)
 g=dict(weights=list(w),root=f,color=color,actions=acts,queries=queries,termination=term or dict(kind=f"cap{d['cap']}",winner=None),final_sfen=b.sfen(),raw_quantity=qty,goal=str(goal),seconds=time.monotonic()-t,reset_policy='warm_game',controller='native_rules')
 if journal:journal.write(json.dumps(g)+'\n');journal.flush();os.fsync(journal.fileno())
 return g

