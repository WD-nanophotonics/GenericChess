from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1553';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1538';S=json.loads((G/'study.json').read_bytes());states=json.loads((G/'states.json').read_bytes());orig=json.loads((G/'values.json').read_bytes())['value'];es=[json.loads(z) for z in (G/'edges.jsonl').open()];edges=[z['moves'] for z in es];checked=[z['checked'] for z in es];boundary=[sum(x!=12 for x in s[:6])<=3 for s in states];P=R/'results/dev_aux/task1539';assert json.loads((P/'result.json').read_bytes())['status']=='COMPLETE';cache={}
for line in (P/'choices.jsonl').open():
 x=json.loads(line);cache.setdefault((x['node_budget'],x['leafR']),{})[x['state_id']]=x['child_id']
results={}
for (budget,price),policy in sorted(cache.items()):
 assert len(policy)==len(states)
 for color in [0,1]:
  adj=[[] if boundary[i] else ([policy[i]] if s[6]==color and edges[i] else [j for u,j in edges[i]]) for i,s in enumerate(states)];pred=[[] for s in states];v=[None]*len(states);rank=[None]*len(states);remaining=[len(a) for a in adj];q=collections.deque()
  for i,ll in enumerate(adj):
   for j in ll:pred[j].append(i)
   if boundary[i]:v[i]=orig[i];rank[i]=0
   elif not ll:v[i]=-1 if checked[i] else 0;rank[i]=0
   if v[i] in [-1,1]:q.append(i)
  while q:
   j=q.popleft()
   for i in pred[j]:
    if v[i] is not None:continue
    if v[j]==-1:v[i]=1;rank[i]=rank[j]+1;q.append(i)
    else:
     remaining[i]-=1
     if remaining[i]==0:v[i]=-1;rank[i]=max(rank[k] for k in adj[i])+1;q.append(i)
  for i in range(len(states)):
   if v[i] is None:v[i]=0
   ll=adj[i]
   if ll:
    assert v[i]==max(-v[j] for j in ll)
    if v[i]==1:assert any(v[j]==-1 and rank[j]<rank[i] for j in ll)
    elif v[i]==-1:assert all(v[j]==1 and rank[j]<rank[i] for j in ll)
    else:assert all(v[j]!=-1 for j in ll) and any(v[j]==0 for j in ll)
   else:assert v[i]==(orig[i] if boundary[i] else -1 if checked[i] else 0)
   sign=1 if states[i][6]==color else -1;assert v[i]*sign<=orig[i]*sign
  results[budget,price,color]=v;(O/f'B{budget}_R{price}_C{color}.json').write_text(json.dumps({'value':v,'rank':rank},separators=(',',':')))
A=json.loads((R/'results/dev_aux/task1555/result.json').read_bytes());rows=[]
for budget in S['nodes']:
 old=next(x for x in A['rows'] if x['budget']==budget);da=[F(old['family_deltas'][str(f['family'])]) for f in S['families']];db=[F(sum(results[budget,1728,states[i][6]][i]-results[budget,720,states[i][6]][i] for i in f['state_ids']),2) for f in S['families']];diff=[b-a for a,b in zip(da,db)];rr={}
 for name,dd in [('A',da),('B',db),('B_minus_A',diff)]:
  vv=list(map(float,dd));rng=random.Random(2026673000+budget);bs=sorted(sum(rng.choices(vv,k=128))/128 for k in range(10000));rr[name]={'mean':str(sum(dd)/128),'bootstrap95':[bs[249],bs[9749]],'family_deltas':list(map(str,dd))}
 ci=rr['B']['bootstrap95'];rr['B_near_zero_supported']=ci[0]>=-1/64 and ci[1]<=1/64;rows.append({'budget':budget,'contrasts':rr})
out={'status':'EXACT_SHARED_ENDGAME_BOUNDARY_ABLATION','rows':rows,'boundary_states':sum(boundary),'new_go':0,'scope':'Bothprices sameperfectcontinuation once<=3actors; all4actoractualcachedchoices retained, opponentALLlegal. NonboundaryinfinitecyclesDraw. Abstractranks distance to provenWDL boundary, NOT physicalmate distance. This partially separates conversionexecution, not soloRmateability/pureexchange/RNcooperation. Primary64,16/256resourcecontrols; pairedB-minusA directuncertainty.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{ 'budget':r['budget'],'contrasts':{k:{x:y for x,y in a.items() if x!='family_deltas'} if isinstance(a,dict) else a for k,a in r['contrasts'].items()}} for r in rows])
