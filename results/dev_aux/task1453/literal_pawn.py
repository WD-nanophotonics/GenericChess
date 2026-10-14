"""Independent finite8x8 royal K/R/N/B/P/Q legality; no castling/drops."""
import chess
def reaches(d,s,t):
 p,c=d[s];dx=t%8-s%8;dy=t//8-s//8
 if p==1:return abs(dx)==1 and dy==(1 if c else -1)
 if p==6:return max(abs(dx),abs(dy))==1
 if p==2:return sorted([abs(dx),abs(dy)])==[1,2]
 diagonal=abs(dx)==abs(dy) and dx!=0;straight=(dx==0)!=(dy==0)
 if not (p==3 and diagonal or p==4 and straight or p==5 and (diagonal or straight)):return False
 stepx=(dx>0)-(dx<0);stepy=(dy>0)-(dy<0);x=s%8+stepx;y=s//8+stepy
 while (x,y)!=(t%8,t//8):
  if x+8*y in d:return False
  x+=stepx;y+=stepy
 return True
def attacked(d,king,enemy):return any(c==enemy and reaches(d,s,king) for s,(pt,c) in d.items())
def literal(b):
 assert not b.castling_rights
 d={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};side=b.turn;result=[]
 for s,(pt,c) in d.items():
  if c!=side:continue
  for t in range(64):
   if s==t or t in d and (d[t][1]==side or d[t][0]==6):continue
   ep=None
   if pt==1:
    sign=1 if side else -1;dx=t%8-s%8;dy=t//8-s//8
    if dx==0:
     if t in d:continue
     if dy==sign:pass
     elif dy==2*sign and s//8==(1 if side else 6) and s+8*sign not in d:pass
     else:continue
    elif abs(dx)==1 and dy==sign:
     if t not in d:
      ep=t-8*sign
      if t!=b.ep_square or d.get(ep)!=(1,not side):continue
    else:continue
   elif not reaches(d,s,t):continue
   promote=pt==1 and t//8==(7 if side else 0)
   for suffix,newpt in ([('q',5),('r',4),('b',3),('n',2)] if promote else [('',pt)]):
    q=dict(d);del q[s]
    if ep is not None:del q[ep]
    q[t]=(newpt,side);king=next(sq for sq,(p,col) in q.items() if p==6 and col==side)
    if not attacked(q,king,not side):result.append(chess.square_name(s)+chess.square_name(t)+suffix)
 return sorted(result)
