"""Royal8x8 K/R/N/B/P, single pawn step, mandatory R/N/B promotion.
State:16 square piece characters plus side0/1. No castle/drop/EP/historydraw.
Duplicate promoted pieces retained. No oldstock shortcut. Barekings draw only.
"""
W=8;H=8
KINDS='KRNBPkrnbp'
def side(p):return int(p.islower())
def king(s,c):return s[:64].index('k' if c else 'K')
def hit(s,a,b):
 p=s[a].upper();dx=b%8-a%8;dy=b//8-a//8
 if p=='K':return max(abs(dx),abs(dy))==1
 if p=='N':return sorted((abs(dx),abs(dy)))==[1,2]
 if p=='P':return abs(dx)==1 and dy==(-1 if side(s[a]) else 1)
 if p=='R':
  if (dx==0)==(dy==0):return False
 elif p=='B':
  if abs(dx)!=abs(dy) or not dx:return False
 else:return False
 step=(dx>0)-(dx<0)+8*((dy>0)-(dy<0));q=a+step
 while q!=b:
  if s[q]!='.':return False
  q+=step
 return True
def attacked(s,b,c):return any(p!='.' and side(p)==c and hit(s,a,b) for a,p in enumerate(s[:64]))
def valid(s):
 if len(s)!=65 or s[64] not in (0,1) or s[:64].count('K')!=1 or s[:64].count('k')!=1:return False
 if any(p!='.' and p not in KINDS for p in s[:64]):return False
 if any(p=='P' and a//8 in (0,7) or p=='p' and a//8 in (0,7) for a,p in enumerate(s[:64])):return False
 return not attacked(s,king(s,1-s[64]),s[64])
def moves(s):
 c=s[64];out=[]
 for a,p in enumerate(s[:64]):
  if p=='.' or side(p)!=c:continue
  for b,q in enumerate(s[:64]):
   if a==b or q!='.' and (side(q)==c or q.upper()=='K'):continue
   if p.upper()=='P':
    dy=(-1 if c else 1)
    ok=(q=='.' and b%8==a%8 and b//8-a//8==dy) or (q!='.' and hit(s,a,b))
   else:ok=hit(s,a,b)
   if not ok:continue
   promote=p.upper()=='P' and b//8==(0 if c else 7)
   for suffix in ('b','n','r') if promote else ('',):
    child=list(s);child[a]='.';child[b]=(suffix if c else suffix.upper()) if suffix else p;child[64]=1-c;child=tuple(child)
    if attacked(child,king(child,c),1-c):continue
    u=chr(97+a%8)+str(1+a//8)+chr(97+b%8)+str(1+b//8)+suffix;out.append((u,child))
 return sorted(out)
def fen(s):
 rows=[]
 for y in range(7,-1,-1):
  row='';empty=0
  for p in s[8*y:8*y+8]:
   if p=='.':empty+=1
   else:
    if empty:row+=str(empty);empty=0
    row+=p
  if empty:row+=str(empty)
  rows.append(row)
 return '/'.join(rows)+(' w ' if s[64]==0 else ' b ')+'- - 0 1'
def bare(s):return sum(p!='.' for p in s[:64])==2
