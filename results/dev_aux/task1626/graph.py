from pathlib import Path
import json,itertools,collections,time,importlib.util,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1627';O.mkdir(exist_ok=False);P={'max_seconds':180,'state_cap':1000000,'rules':'4x4 royalK R N B, globally one each nonking, mate/stale/infinitecycle, no history draws'};start=time.monotonic();deadline=start+P['max_seconds']
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
states=[];index={};raw=0
for owners in itertools.product([-1,0,1],repeat=3):
 actors=[0,4]+[k+1+4*c for k,c in enumerate(owners) if c>=0]
 if len(actors)>4:continue
 for positions in itertools.permutations(range(16),len(actors)):
  base=[16]*8
  for i,pos in zip(actors,positions):base[i]=pos
  for turn in [0,1]:
   raw+=1;s=tuple(base+[turn])
   if T.valid(s):index[s]=len(states);states.append(s)
  if raw%4096==0:assert time.monotonic()<deadline and len(states)<=P['state_cap']
assert len(index)==len(states);(O/'states.json').write_text(json.dumps(states,separators=(',',':')))
adj=[];pred=[[] for _ in states];checked=[];edges=0
with (O/'edges.jsonl').open('w',encoding='utf8') as f:
 for i,s in enumerate(states):
  assert time.monotonic()<deadline;ll=T.moves(s);row=[(u,index[v]) for u,v in ll];adj.append(row);c=T.attacked(s,s[4*s[8]],1-s[8]);checked.append(c)
  for u,j in row:pred[j].append(i);edges+=1
  f.write(json.dumps({'id':i,'moves':row,'checked':c},separators=(',',':'))+'\n')
  if i%20000==0:print('GRAPH',i,edges,flush=True)
# Side-to-move negamax exact retrograde; terminal checkmate is loss, stalemate is draw.
value=[None]*len(states);rank=[None]*len(states);remaining=[len(x) for x in adj];queue=collections.deque()
for i,ll in enumerate(adj):
 if not ll:
  value[i]=-1 if checked[i] else 0;rank[i]=0
  if value[i]==-1:queue.append(i)
while queue:
 j=queue.popleft()
 for i in pred[j]:
  if value[i] is not None:continue
  if value[j]==-1:value[i]=1;rank[i]=rank[j]+1;queue.append(i)
  else:
   remaining[i]-=1
   if remaining[i]==0:value[i]=-1;rank[i]=max(rank[k] for _,k in adj[i])+1;queue.append(i)
for i in range(len(states)):
 if value[i] is None:value[i]=0
# Bellman and strictly decreasing mate ranks certify all decisive labels; draw subgraph is closed enough for perpetual safe play.
for i,ll in enumerate(adj):
 if not ll:assert value[i]==(-1 if checked[i] else 0);continue
 child=[value[j] for _,j in ll];assert value[i]==max(-x for x in child)
 if value[i]==1:assert any(value[j]==-1 and rank[j]<rank[i] for _,j in ll)
 elif value[i]==-1:assert all(value[j]==1 and rank[j]<rank[i] for _,j in ll)
 else:assert all(value[j]!=-1 for _,j in ll) and any(value[j]==0 for _,j in ll)
(O/'values.json').write_text(json.dumps({'value':value,'rank':rank},separators=(',',':')));out={'status':'COMPLETE_GRAPH_CLOSED_EXACT_WDL','raw_candidates':raw,'states':len(states),'edges':edges,'WLD':dict(collections.Counter(value)),'maximum_mate_rank':max(x for x in rank if x is not None),'seconds':time.monotonic()-start,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rules_sha256':hashlib.sha256((R/'results/dev_aux/task1626/rules.py').read_bytes()).hexdigest(),'new_go':0,'scope':P['rules']};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
