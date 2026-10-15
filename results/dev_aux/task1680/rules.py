"""Royal4x4 K/R/N/B/P, single pawn step, promotion OFF: pawn remains P on last rank.
State:16 square piece characters plus side0/1. No castle/drop/EP/historydraw.
Duplicate promoted pieces retained. No oldstock shortcut. Barekings draw only.
"""
W=4;H=4
KINDS='KRNBPkrnbp'
def side(p):return int(p.islower())
def king(s,c):return s[:16].index('k' if c else 'K')
def hit(s,a,b):
 p=s[a].upper();dx=b%4-a%4;dy=b//4-a//4
 if p=='K':return max(abs(dx),abs(dy))==1
 if p=='N':return sorted((abs(dx),abs(dy)))==[1,2]
 if p=='P':return abs(dx)==1 and dy==(-1 if side(s[a]) else 1)
 if p=='R':
  if (dx==0)==(dy==0):return False
 elif p=='B':
  if abs(dx)!=abs(dy) or not dx:return False
 else:return False
 step=(dx>0)-(dx<0)+4*((dy>0)-(dy<0));q=a+step
 while q!=b:
  if s[q]!='.':return False
  q+=step
 return True
def attacked(s,b,c):return any(p!='.' and side(p)==c and hit(s,a,b) for a,p in enumerate(s[:16]))
def valid(s):
 if len(s)!=17 or s[16] not in (0,1) or s[:16].count('K')!=1 or s[:16].count('k')!=1:return False
 if any(p!='.' and p not in KINDS for p in s[:16]):return False
 return not attacked(s,king(s,1-s[16]),s[16])
def moves(s):
 c=s[16];out=[]
 for a,p in enumerate(s[:16]):
  if p=='.' or side(p)!=c:continue
  for b,q in enumerate(s[:16]):
   if a==b or q!='.' and (side(q)==c or q.upper()=='K'):continue
   if p.upper()=='P':
    dy=(-1 if c else 1)
    ok=(q=='.' and b%4==a%4 and b//4-a//4==dy) or (q!='.' and hit(s,a,b))
   else:ok=hit(s,a,b)
   if not ok:continue
   promote=p.upper()=='P' and b//4==(0 if c else 3)
   for suffix in ('',):
    child=list(s);child[a]='.';child[b]=(suffix if c else suffix.upper()) if suffix else p;child[16]=1-c;child=tuple(child)
    if attacked(child,king(child,c),1-c):continue
    u=chr(97+a%4)+str(1+a//4)+chr(97+b%4)+str(1+b//4)+suffix;out.append((u,child))
 return sorted(out)
def fen(s):
 rows=[]
 for y in range(3,-1,-1):
  row='';empty=0
  for p in s[4*y:4*y+4]:
   if p=='.':empty+=1
   else:
    if empty:row+=str(empty);empty=0
    row+=p
  if empty:row+=str(empty)
  rows.append(row)
 return '/'.join(rows)+(' w ' if s[16]==0 else ' b ')+'- - 0 1'
def bare(s):return sum(p!='.' for p in s[:16])==2
