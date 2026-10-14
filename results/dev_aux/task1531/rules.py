"""Independent 3x4 royal K/R/N finite-game rules; no material or human prices."""
N=3;ABSENT=12;KINDS=('K','R','N','k','r','n')
def xy(s):return s%3,s//3
def hit(state,i,target):
 a=state[i];x,y=xy(a);u,v=xy(target);dx,dy=u-x,v-y
 if i%3==0:return max(abs(dx),abs(dy))==1
 if i%3==2:return sorted((abs(dx),abs(dy)))==[1,2]
 if (dx==0)==(dy==0):return False
 step=(1 if dx>0 else -1) if dx else (3 if dy>0 else -3);occupied=set(state[:6])-{ABSENT}
 s=a+step
 while s!=target:
  if s in occupied:return False
  s+=step
 return True
def attacked(state,target,by):return any(state[i]!=ABSENT and hit(state,i,target) for i in range(3*by,3*by+3))
def valid(s):
 p=s[:6];occupied=[x for x in p if x!=ABSENT]
 return p[0]!=ABSENT and p[3]!=ABSENT and len(set(occupied))==len(occupied) and not attacked(s,p[3*(1-s[6])],s[6])
def moves(s):
 turn=s[6];out=[];own=range(3*turn,3*turn+3);enemy=range(3*(1-turn),3*(1-turn)+3);occupied={v:i for i,v in enumerate(s[:6]) if v!=ABSENT}
 for i in own:
  if s[i]==ABSENT:continue
  for target in range(12):
   j=occupied.get(target)
   if j is not None and (j in own or j%3==0):continue
   if not hit(s,i,target):continue
   a=list(s);a[i]=target
   if j is not None:a[j]=ABSENT
   a[6]=1-turn;a=tuple(a)
   if attacked(a,a[3*turn],1-turn):continue
   x,y=xy(s[i]);u,v=xy(target);out.append((chr(97+x)+str(y+1)+chr(97+u)+str(v+1),a))
 return sorted(out)
def fen(s,width=3,height=4):
 board={v:KINDS[i] for i,v in enumerate(s[:6]) if v!=ABSENT};rows=[]
 for rank in range(height-1,-1,-1):
  row='';empty=0
  for file in range(width):
   idx=rank*3+file if file<3 and rank<4 else None;c=board.get(idx)
   if c is None:empty+=1
   else:
    if empty:row+=str(empty);empty=0
    row+=c
  if empty:row+=str(empty)
  rows.append(row)
 return '/'.join(rows)+(' w ' if s[6]==0 else ' b ')+'- - 0 1'
