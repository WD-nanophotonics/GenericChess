"""Royal K/R/N/B 3x4; at most one globally of each nonking kind."""
W=3;H=4;ABSENT=12;KINDS=('K','R','N','B','k','r','n','b');GROUP=4

def xy(s):return s%W,s//W

def hit(s,i,target):
 a=s[i];x,y=xy(a);u,v=xy(target);dx,dy=u-x,v-y;k=i%GROUP
 if k==0:return max(abs(dx),abs(dy))==1
 if k==2:return sorted((abs(dx),abs(dy)))==[1,2]
 if k==1:
  if (dx==0)==(dy==0):return False
 elif abs(dx)!=abs(dy) or not dx:return False
 step=(1 if dx>0 else -1 if dx<0 else 0)+W*(1 if dy>0 else -1 if dy<0 else 0)
 occupied=set(s[:8])-{ABSENT};q=a+step
 while q!=target:
  if q in occupied:return False
  q+=step
 return True

def attacked(s,target,by):return any(s[i]!=ABSENT and hit(s,i,target) for i in range(4*by,4*by+4))

def valid(s):
 occupied=[x for x in s[:8] if x!=ABSENT]
 return s[0]!=ABSENT and s[4]!=ABSENT and len(set(occupied))==len(occupied) and all(s[k]==ABSENT or s[k+4]==ABSENT for k in (1,2,3)) and not attacked(s,s[4*(1-s[8])],s[8])

def moves(s):
 turn=s[8];out=[];own=range(4*turn,4*turn+4);occupied={v:i for i,v in enumerate(s[:8]) if v!=ABSENT}
 for i in own:
  if s[i]==ABSENT:continue
  for target in range(12):
   j=occupied.get(target)
   if j is not None and (j in own or j%4==0):continue
   if not hit(s,i,target):continue
   a=list(s);a[i]=target
   if j is not None:a[j]=ABSENT
   a[8]=1-turn;a=tuple(a)
   if attacked(a,a[4*turn],1-turn):continue
   x,y=xy(s[i]);u,v=xy(target);out.append((chr(97+x)+str(y+1)+chr(97+u)+str(v+1),a))
 return sorted(out)

def fen(s,width=3,height=4):
 board={v:KINDS[i] for i,v in enumerate(s[:8]) if v!=ABSENT};rows=[]
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
 return '/'.join(rows)+(' w ' if s[8]==0 else ' b ')+'- - 0 1'
