from pathlib import Path
import json,random,importlib.util,collections,hashlib,ast
R=Path.cwd();O=R/'results/dev_aux/task1688'
sp=importlib.util.spec_from_file_location('T',O/'rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def ref(s):
 d={a:(p.upper(),p.islower()) for a,p in enumerate(s[:64]) if p!='.'};c=bool(s[64]);out=[]
 def reaches(d,a,b):
  p,col=d[a];x,y=a%8,a//8;u,v=b%8,b//8;dx,dy=u-x,v-y
  if p=='P':return abs(dx)==1 and dy==(-1 if col else 1)
  if p=='K':return max(abs(dx),abs(dy))==1
  if p=='N':return abs(dx)*abs(dy)==2 and abs(dx)+abs(dy)==3
  if not(p=='R' and ((dx==0)!=(dy==0)) or p=='B' and abs(dx)==abs(dy) and dx!=0):return False
  sx=(dx>0)-(dx<0);sy=(dy>0)-(dy<0);x+=sx;y+=sy
  while (x,y)!=(u,v):
   if x+8*y in d:return False
   x+=sx;y+=sy
  return True
 def check(d,col):
  k=next(a for a,(p,z) in d.items() if p=='K' and z==col)
  return any(z!=col and reaches(d,a,k) for a,(p,z) in d.items())
 for a,(p,col) in d.items():
  if col!=c:continue
  for b in range(64):
   if b==a or b in d and (d[b][1]==c or d[b][0]=='K'):continue
   if p=='P':ok=(b not in d and b==a+8*(-1 if c else 1)) or (b in d and reaches(d,a,b))
   else:ok=reaches(d,a,b)
   if not ok:continue
   for suffix in ('r','n','b') if p=='P' and b//8==(0 if c else 7) else ('',):
    q=dict(d);del q[a];q[b]=(suffix.upper() if suffix else p,c)
    if check(q,c):continue
    arr=['.']*64
    for z,(k,t) in q.items():arr[z]=k.lower() if t else k
    out.append((chr(97+a%8)+str(1+a//8)+chr(97+b%8)+str(1+b//8)+suffix,tuple(arr+[int(not c)])))
 return sorted(out)
rng=random.Random(2026692600);cases={};attempts=0
while len(cases)<1024:
 attempts+=1;s=['.']*64;positions=rng.sample(range(64),rng.choice([3,4,5,6]));s[positions[0]]='K';s[positions[1]]='k'
 for z in positions[2:]:s[z]=rng.choice('RNBPrnbp')
 s=tuple(s+[rng.randrange(2)])
 if not T.valid(s):continue
 assert T.moves(s)==ref(s);cases[s]=T.moves(s)
 for u,t in T.moves(s):assert T.valid(t);assert T.moves(t)==ref(t)
cc=collections.Counter();records=[]
for s,ll in cases.items():
 cc['roots']+=1;cc['moves']+=len(ll);cc['checked']+=T.attacked(s,T.king(s,s[64]),1-s[64]);cc['promotion_roots']+=any(len(u)==5 for u,t in ll);cc['promotion_moves']+=sum(len(u)==5 for u,t in ll);cc['duplicate_kind_roots']+=any(s[:64].count(k)+s[:64].count(k.lower())>1 for k in 'RNB');records.append({'state':s,'fen':T.fen(s),'moves':ll})
(O/'literal_cases.json').write_text(json.dumps(records));(O/'literal_result.json').write_text(json.dumps({'status':'PASS_INDEPENDENT_SQUARE_AND_ACTOR_MODELS_ALL1024ROOTS_AND_ALLCHILDREN','counts':dict(cc),'attempts':attempts,'model_sha256':hashlib.sha256((O/'rules.py').read_bytes()).hexdigest(),'scope':'8x8 single-stepPawn mandatoryRNBpromotion/noEP/ordinaryroyallegality; dynamicduplicatepromotedstocks; nooldno-mate proof.'},indent=2));print(dict(cc))
