"""Generic retrograde on a complete Core-produced finite graph; labels scoped."""
from pathlib import Path
from collections import Counter
import json,hashlib,time,heapq
ROOT=Path('results/dev_aux/task2056');OUT=Path('results/dev_aux/task2058')
def rawkey(raw):return ''.join(raw[:-1])+str(raw[-1])
def solve(rows):
 ids={rawkey(r['board']):i for i,r in enumerate(rows)};assert len(ids)==len(rows)
 children=[];pred=[[] for _ in rows];wdl=[None]*len(rows);rank=[None]*len(rows);policy=[None]*len(rows);heap=[];remaining=[];maxchild=[0]*len(rows)
 for i,r in enumerate(rows):
  edge=[(a,ids[rawkey(k)]) for a,k in r['children']];assert len(edge)==len({a for a,_ in edge})
  children.append(edge);remaining.append(len(edge))
  for a,j in edge:
   assert rows[j]['board'][-1]==1-r['board'][-1];pred[j].append((i,a))
  if r['status']!='ongoing':
   assert not edge
   wdl[i]=0 if r['winner'] is None else (1 if r['winner']==r['board'][-1] else -1);rank[i]=0
   if wdl[i]:heapq.heappush(heap,(0,i))
  else:assert edge and r['winner'] is None
 while heap:
  d,j=heapq.heappop(heap);assert rank[j]==d
  for i,a in pred[j]:
   if wdl[i] is not None:continue
   if wdl[j]==-1:
    wdl[i]=1;rank[i]=d+1;policy[i]=a;heapq.heappush(heap,(d+1,i))
   elif wdl[j]==1:
    remaining[i]-=1;maxchild[i]=max(maxchild[i],d)
    if remaining[i]==0:
     wdl[i]=-1;rank[i]=maxchild[i]+1;heapq.heappush(heap,(rank[i],i))
 for i in range(len(rows)):
  if wdl[i] is None:wdl[i]=0
 return children,wdl,rank,policy

def run():
 p=json.loads((OUT/'plan.json').read_text());completion=json.loads((ROOT/'result.json').read_text());assert completion['status']=='COMPLETE' and completion['complete_inventory_and_all_edges']
 raw=(ROOT/'states.jsonl').read_bytes();canonical=b'\n'.join(raw.splitlines())+b'\n';assert hashlib.sha256(canonical).hexdigest()==completion['records_sha'];start=time.perf_counter();rows=[json.loads(x) for x in raw.splitlines()];children,wdl,rank,policy=solve(rows)
 assert time.perf_counter()-start<p['seconds_cap'];counts={};maxrank=max(x or 0 for x in rank);ongoing=Counter();h=hashlib.sha256()
 for mode in ('KK','KKN','KKB','KKBN'):counts[mode]=dict(Counter('WIN' if wdl[i]==1 else 'LOSS' if wdl[i]==-1 else 'DRAW' for i,r in enumerate(rows) if r['inventory']==mode))
 with (OUT/'labels.jsonl').open('x',encoding='utf-8') as f:
  for i,r in enumerate(rows):
   label='WIN' if wdl[i]==1 else 'LOSS' if wdl[i]==-1 else 'DRAW'
   quality='EXACT_CANONICAL_FRESH_ROOT' if wdl[i]==0 or rank[i]<=96 else 'PROVED_POSITIONAL_BOUND_HORIZON_UNRESOLVED'
   if r['status']=='ongoing':ongoing[label]+=1
   item=dict(index=i,board=r['board'],inventory=r['inventory'],status=r['status'],label=label,quality=quality,rank=rank[i],winning_action=policy[i],actions=[dict(action=a,child=j,child_value=wdl[j]) for a,j in children[i]])
   text=json.dumps(item,separators=(',',':'));f.write(text+'\n');h.update(text.encode()+b'\n')
 result=dict(status='COMPLETE_GRAPH_RETROGRADE_PENDING_INDEPENDENT_AUDIT',states=len(rows),edges=sum(map(len,children)),by_inventory=counts,ongoing_WDL=dict(ongoing),maximum_decisive_rank=maxrank,ranks_over96=sum(v is not None and v>96 for v in rank),labels_sha=h.hexdigest(),seconds=time.perf_counter()-start,scope=p['scope'],no_new_Native_or_prover_or_reward_games=True)
 with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
