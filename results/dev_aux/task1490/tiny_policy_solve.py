from pathlib import Path
import json,collections,random,sys,importlib.util
from fractions import Fraction as F
R=Path.cwd();P=R/sys.argv[1];O=R/sys.argv[2];O.mkdir(exist_ok=False);producer=json.loads((P/'result.json').read_bytes());assert producer['status']=='COMPLETE' and producer['all_owned_engines_closed'];plan=json.loads((P/'plan.json').read_bytes());G=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));original=json.loads((G/'values.json').read_bytes())['value'];erows=[json.loads(x) for x in (G/'edges.jsonl').read_text().splitlines()];edges=[x['moves'] for x in erows];checked=[x['checked'] for x in erows];policies={}
for line in (P/'choices.jsonl').open():
 x=json.loads(line);key=(x.get('node_budget',16),x['leafR']);dd=policies.setdefault(key,{ });sid=x['state_id'];assert sid not in dd;assert (x['move'] is None and not edges[sid]) or (x['move'],x['child_id']) in [(u,j) for u,j in edges[sid]];dd[sid]=x['child_id']
for d in policies.values():assert len(d)==len(states)
study=json.loads((R/'results/dev_aux/task1503/study.json').read_bytes());dev=[x for x in study['families'] if x['phase']=='DEV'];results={};summary=[]
for (budget,price),policy in sorted(policies.items()):
 for color in [0,1]:
  adj=[([(next(u for u,j in edges[i] if j==policy[i]),policy[i])] if edges[i] else []) if s[6]==color else edges[i] for i,s in enumerate(states)];pred=[[] for s in states];remaining=[len(x) for x in adj];value=[None]*len(states);rank=[None]*len(states);q=collections.deque()
  for i,ll in enumerate(adj):
   for u,j in ll:pred[j].append(i)
   if not ll:value[i]=-1 if checked[i] else 0;rank[i]=0
   if value[i]==-1:q.append(i)
  while q:
   j=q.popleft()
   for i in pred[j]:
    if value[i] is not None:continue
    if value[j]==-1:value[i]=1;rank[i]=rank[j]+1;q.append(i)
    else:
     remaining[i]-=1
     if remaining[i]==0:value[i]=-1;rank[i]=max(rank[k] for u,k in adj[i])+1;q.append(i)
  for i in range(len(states)):
   if value[i] is None:value[i]=0
  for i,ll in enumerate(adj):
   if ll:
    assert value[i]==max(-value[j] for u,j in ll)
    if value[i]==1:assert any(value[j]==-1 and rank[j]<rank[i] for u,j in ll)
    elif value[i]==-1:assert all(value[j]==1 and rank[j]<rank[i] for u,j in ll)
    else:assert all(value[j]!=-1 for u,j in ll) and any(value[j]==0 for u,j in ll)
   sign=1 if states[i][6]==color else -1;assert value[i]*sign<=original[i]*sign
   if states[i][6]==color and ll:assert value[i]<=-original[policy[i]]
  name=f'B{budget}_R{price}_C{color}';(O/(name+'.json')).write_text(json.dumps({'value':value,'rank':rank},separators=(',',':')));results[budget,price,color]=value;summary.append({'budget':budget,'price':price,'candidatecolor':color,'candidateWLD_allgraph':dict(collections.Counter(value[i]*(1 if states[i][6]==color else -1) for i in range(len(states)))),'oracle_win_retained_but_not_realized_ownstates':sum(original[i]==1 and edges[i] and -original[policy[i]]==1 and value[i]!=1 for i,s in enumerate(states) if s[6]==color),'maximum_actual_policy_mate_rank':max(x for x in rank if x is not None)})
rows=[];vectors={}
for budget in sorted({b for b,p in policies}):
 fd={f['family']:F(sum(results[budget,1728,states[i][6]][i]-results[budget,720,states[i][6]][i] for i in f['state_ids']),2) for f in dev};vals=list(map(float,fd.values()));vectors[budget]=vals;rng=random.Random(2026630500+budget);bs=sorted(sum(rng.choices(vals,k=64))/64 for _ in range(10000));rows.append({'budget':budget,'primary':'TRAIN selected1728 minus720, fullpolicy vsperfectbestresponse','mean':str(sum(fd.values())/64),'bootstrap95':[bs[249],bs[9749]],'family_deltas':{f:str(x) for f,x in fd.items()},'selected_WLD':dict(collections.Counter(results[budget,1728,states[i][6]][i] for f in dev for i in f['state_ids'])),'baseline_WLD':dict(collections.Counter(results[budget,720,states[i][6]][i] for f in dev for i in f['state_ids']))})
out={'status':'COMPLETE_FIXED_POLICY_EXACT_BEST_RESPONSE_WDL','rows':rows,'allgraph_descriptive':summary,'states_per_policy':len(states),'scope':'Candidate cold deterministic16/64/256node policies; opponent ALLlegaladaptivebestresponse, exact checkmate/stalemate/infinitecycle game. This is whole-policy actual WDL not single-choice perfect continuation. Frozen DEV64fullorbits, no furthertraining or humanfit. No warmTT/history-policy claim.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k!='family_deltas'} for x in rows]);print(summary)
