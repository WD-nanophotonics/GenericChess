"""Exact closed KRK WDL + mate-distance retrograde, no material oracle labels."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,heapq,array,hashlib,random,ast,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1741';O.mkdir(exist_ok=False);start=time.perf_counter();deadline=time.monotonic()+600;results=[];error=None
sp=importlib.util.spec_from_file_location('STOP',R/'results/dev_aux/task166/run.py');STOP=importlib.util.module_from_spec(sp);sp.loader.exec_module(STOP)
(O/'plan.json').write_text(json.dumps(dict(status='FROZEN_KRK_RULE_RETROGRADE_BEFORE_ENUMERATION',question='Are cold material-policy cycles failures to convert exact forced wins after exchange, rather than absence of physical winning continuations?',widths=[4,8],stock='WhiteR +bothKings, normalizedblackR bycolor-exchange, bothturns. Rcapture goes tocomplete1706bareDraw. NoPawn/drop/castle/history.',seconds_cap=600,expected_seconds=90,max_array_slots=600000,labels='Complete finite directed rule graph, mateLOSSseeds, existentialWIN/universalLOSS propagation, remaininginfiniteplayDraw. DTMminwinner/maxloser. No Nativeeval/humanprices labels ortraining.',cost='Array IDs, predecessor generation on demand, nofull edge objects; build+ALLBellmanrecheck, independentactor sample. Existing games only analyzed afterward.'),indent=2))
for W,model,qual in [(4,'results/dev_aux/task1675/rules.py','results/dev_aux/task1675/qualify_literal.py'),(8,'results/dev_aux/task1688/rules.py','results/dev_aux/task1688/qualify_literal_fixed.py')]:
 if error:break
 try:
  A=W*W;size=2*A*A*A;assert size<=600000
  kingneighbors={z:[x+W*y for x in range(max(0,z%W-1),min(W,z%W+2)) for y in range(max(0,z//W-1),min(W,z//W+2)) if x+W*y!=z] for z in range(A)}
  def far(a,b):return max(abs(a%W-b%W),abs(a//W-b//W))>1
  def hit(r,b,k):
   if r%W==b%W:return not(k%W==r%W and min(r//W,b//W)<k//W<max(r//W,b//W))
   if r//W==b//W:return not(k//W==r//W and min(r%W,b%W)<k%W<max(r%W,b%W))
   return False
  def valid(k,b,r,c):return k!=b and k!=r and b!=r and far(k,b) and (c==1 or not hit(r,b,k))
  def idx(k,b,r,c):return (((k*A+b)*A+r)*2+c)
  def decode(i):
   c=i%2;i//=2;r=i%A;i//=A;b=i%A;k=i//A;return k,b,r,c
  def moves(k,b,r,c):
   if c==0:
    for z in kingneighbors[k]:
     if z not in (r,b) and far(z,b):yield k,z,idx(z,b,r,1)
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
     x,y=r%W+dx,r//W+dy
     while 0<=x<W and 0<=y<W:
      z=x+W*y
      if z in (k,b):break
      yield r,z,idx(k,b,z,1);x+=dx;y+=dy
   else:
    for z in kingneighbors[b]:
     if z==k or not far(k,z):continue
     if z==r:yield b,z,-1
     elif not hit(r,z,k):yield b,z,idx(k,z,r,0)
  def preds(k,b,r,c):
   if c==1:
    for oldk in kingneighbors[k]:
     if valid(oldk,b,r,0):yield idx(oldk,b,r,0)
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
     x,y=r%W+dx,r//W+dy
     while 0<=x<W and 0<=y<W:
      oldr=x+W*y
      if oldr in (k,b):break
      if valid(k,b,oldr,0):yield idx(k,b,oldr,0)
      x+=dx;y+=dy
   else:
    for oldb in kingneighbors[b]:
     if valid(k,oldb,r,1):yield idx(k,oldb,r,1)
  wdl=bytearray([255])*size;rank=array.array('H',[0])*size;remaining=bytearray(size);maxchild=array.array('H',[0])*size;heap=[];cc=collections.Counter()
  for k in range(A):
   STOP.stop();assert time.monotonic()<deadline
   for b in range(A):
    if not far(k,b):continue
    for r in range(A):
     for c in (0,1):
      if not valid(k,b,r,c):continue
      i=idx(k,b,r,c);ll=list(moves(k,b,r,c));wdl[i]=0;remaining[i]=len(ll);cc['valid']+=1;cc['edges']+=len(ll);cc['bare_capture_edges']+=sum(j<0 for a,z,j in ll)
      if not ll and c==1 and hit(r,b,k):wdl[i]=2;heapq.heappush(heap,(0,i));cc['mate_seeds']+=1
      elif not ll:cc['stalemate_seeds']+=1
  print('ENUMERATED',W,dict(cc),round(time.perf_counter()-start,3),flush=True)
  while heap:
   d,i=heapq.heappop(heap);assert rank[i]==d;cc['propagated']+=1
   if cc['propagated']%4096==0:STOP.stop();assert time.monotonic()<deadline
   for parent in preds(*decode(i)):
    assert wdl[parent]!=255
    if wdl[parent]!=0:continue
    if wdl[i]==2:wdl[parent]=1;rank[parent]=d+1;heapq.heappush(heap,(d+1,parent))
    else:
     remaining[parent]-=1;maxchild[parent]=max(maxchild[parent],d)
     if remaining[parent]==0:wdl[parent]=2;rank[parent]=maxchild[parent]+1;heapq.heappush(heap,(rank[parent],parent))
  # Every valid state, ALL legal children: independent fixed-point certificate check.
  validids=[]
  for i,v in enumerate(wdl):
   if v==255:continue
   if i%4096==0:STOP.stop();assert time.monotonic()<deadline
   k,b,r,c=decode(i);ll=list(moves(k,b,r,c));children=[(0,0) if j<0 else(wdl[j],rank[j]) for a,z,j in ll];assert all(x!=255 for x,d in children)
   if v==1:assert any(x==2 for x,d in children) and rank[i]==1+min(d for x,d in children if x==2)
   elif v==2:
    if not ll:assert c==1 and hit(r,b,k) and rank[i]==0
    else:assert all(x==1 for x,d in children) and rank[i]==1+max(d for x,d in children)
   else:assert not any(x==2 for x,d in children) and(not ll or any(x==0 for x,d in children))
   cc[{0:'DRAW',1:'WIN',2:'LOSS'}[v]]+=1;validids.append(i)
  # Independent actor map legality cross-check on frozen random samples/all children.
  tree=ast.parse((R/qual).read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'literalKRK','exec'),ns);ref=ns['ref'];rng=random.Random(2026701542+W);cases=[]
  for i in rng.sample(validids,min(1024,len(validids))):
   k,b,r,c=decode(i);s=['.']*A;s[k]='K';s[b]='k';s[r]='R';s=tuple(s+[c]);actual={}
   for u,t in ref(s):
    if 'R' not in t:actual[u]=-1
    else:actual[u]=idx(t[:-1].index('K'),t[:-1].index('k'),t[:-1].index('R'),t[-1])
   expect={chr(97+a%W)+str(1+a//W)+chr(97+z%W)+str(1+z//W):j for a,z,j in moves(k,b,r,c)};assert actual==expect
   cases.append(dict(id=i,state=s,moves=actual,wdl=wdl[i],rank=rank[i]))
  (O/f'wdl{W}.bin').write_bytes(wdl);(O/f'rank{W}.bin').write_bytes(rank.tobytes());(O/f'literal{W}.json').write_text(json.dumps(cases))
  result=dict(width=W,model=model,model_sha256=hashlib.sha256((R/model).read_bytes()).hexdigest(),status='PASS_COMPLETE_KRK_WDL_DTM_ALL_BELLMAN_AND_LITERAL',array_slots=size,counts=dict(cc),max_DTM=max(rank),wdl_sha256=hashlib.sha256(wdl).hexdigest(),rank_sha256=hashlib.sha256(rank.tobytes()).hexdigest(),literal_cases=len(cases),color_normalization='Swapallcolors andturn forblackR, geometryunchanged. Closednonpawnrule movementcolorblind.',meaning='WDLside-to-move(1win,2loss,0draw,255invalid);mateDTMminwinner/maxloser, infiniteplayDraw, nofinitehorizonlabels. Nativequalificationseparate.')
  results.append(result);(O/f'proof{W}.json').write_text(json.dumps(result,indent=2));print('PROVED',W,dict(cc),'DTM',max(rank),flush=True)
 except BaseException as ex:error=type(ex).__name__+':'+str(ex)
out=dict(status='PASS_COMPLETE_BOTH_KRK_PROOFS' if error is None else 'PARTIAL_PRESERVED',error=error,results=results,seconds=time.perf_counter()-start,actual_native_go=0)
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

