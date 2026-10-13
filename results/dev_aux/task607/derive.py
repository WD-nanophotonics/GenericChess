import json,hashlib,time,sys,collections,re,statistics
from pathlib import Path
from fractions import Fraction as F
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task607';O.mkdir(exist_ok=True);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());audit=json.loads((R/'results/dev_aux/task600/result.json').read_bytes());assert audit['status']=='PASS';axes=d['axes'];handtypes=[1,2,3,4,7,5,6];symbols={s:i for i,s in enumerate(['','p','l','n','s','b','r','g','k','+p','+l','+n','+s','+b','+r'])};dropmap={1:1,2:2,3:3,4:4,5:7,6:5,7:6};sources={};rows=[];group={};total=collections.Counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import run as G
def vec(b,color):
 v=[0]*16
 for pc in b.pieces:
  if pc:v[pc%16]+=1 if (0 if pc<16 else 1)==color else -1
 for owner,hand in enumerate(b.pieces_in_hand):
  for a,cnt in zip(handtypes,hand):v[a]+=cnt if owner==color else -cnt
 return v
for task,stage in [(597,'terminal_train'),(598,'mixed_train'),(599,'development')]:
 P=R/f'results/dev_aux/task{task}/games.jsonl';sha=hashlib.sha256(P.read_bytes()).hexdigest();assert sha==audit['source_sha256'][str(task)]['games.jsonl'];sources[task]=sha
 for line,text in enumerate(P.open(encoding='utf-8'),1):
  G.stop();g=json.loads(text);f=g['root'];b=C.Board(f['initial_sfen'])
  for u in f['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
  assert b.sfen()==f['expected_sfen'];q=0;features=[vec(b,g['color'])];counts=collections.Counter();moved=collections.Counter();captured=collections.Counter();drops=collections.Counter();promos=collections.Counter();nodes=[];depths=[];scoremates=0;qs=[]
  for ply,a in enumerate(g['actions']):
   assert b.sfen()==a['before_sfen'];role='candidate' if b.turn==g['color'] else 'random';counts[role+'_actions']+=1
   if a['moving'] is not None:moved[(role,symbols[a['moving'].lower()])]+=1
   if a['captured'] is not None:captured[(role,symbols[a['captured'].lower()])]+=1
   if a['drop'] is not None:drops[(role,dropmap[a['drop']])]+=1
   if a['promotion']:promos[(role,symbols[a['moving'].lower()])]+=1
   if role=='candidate':
    query=g['queries'][q];q+=1;assert query['ply']==ply and query['weights']==g['weights'];v=vec(b,0);material=sum(v[i]*g['weights'][i] for i in range(16));state=query['state'].split(' ',7);assert int(state[3])==int(state[4])==material and int(state[5])==(material if b.turn==0 else -material);info=[x for x in query['lines'] if re.search(r'\bnodes \d+',x)];assert info;last=info[-1];nn=int(re.search(r'\bnodes (\d+)',last)[1]);dd=int(re.search(r'\bdepth (\d+)',last)[1]);nodes.append(nn);depths.append(dd);mate=bool(re.search(r'\bscore mate ',last));scoremates+=mate;qs.append(dict(ply=ply,nodes=nn,depth=dd,score_mate=mate));counts['queries']+=1
   m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m);assert b.sfen()==a['after_sfen'];features.append(vec(b,g['color']))
  assert q==len(g['queries']) and b.sfen()==g['final_sfen'];var=[any(v[a]!=features[0][a] for v in features[1:]) for a in axes];row=dict(stage=stage,source=dict(file=f'results/dev_aux/task{task}/games.jsonl',line=line),family=f['source_family'],root=f['index'],offset=f['offset'],color=g['color'],weights=g['weights'],goal=g['goal'],termination=g['termination'],queries=q,actions=len(g['actions']),initial_signed_counts=features[0],final_signed_counts=features[-1],signed_type_varies=dict(zip(map(str,axes),var)),moving={f'{role}:{a}':n for (role,a),n in moved.items()},captures={f'{role}:{a}':n for (role,a),n in captured.items()},drops={f'{role}:{a}':n for (role,a),n in drops.items()},promotions={f'{role}:{a}':n for (role,a),n in promos.items()},query_work=qs);rows.append(row);total.update(dict(games=1,queries=q,actions=len(g['actions']),candidate_actions=counts['candidate_actions'],random_actions=counts['random_actions'],nodes=sum(nodes),mate_scored_queries=scoremates))
  key=(stage,tuple(g['weights']));a=group.setdefault(key,dict(games=0,queries=0,actions=0,nodes=[],depths=collections.Counter(),families=collections.Counter(),moving=collections.Counter(),captures=collections.Counter(),drops=collections.Counter(),promotions=collections.Counter(),vary=collections.Counter(),mates=0,unfinished=0));a['games']+=1;a['queries']+=q;a['actions']+=len(g['actions']);a['nodes']+=nodes;a['depths'].update(depths);a['families'][f['source_family']]+=1;a['moving'].update(row['moving']);a['captures'].update(row['captures']);a['drops'].update(row['drops']);a['promotions'].update(row['promotions']);a['vary'].update({str(axis):int(v) for axis,v in zip(axes,var)});a['mates']+=g['termination']['kind']=='checkmate';a['unfinished']+=g['termination']['kind']=='cap12'
  if line%1000==0:print('coverage',task,line,round(time.perf_counter()-start,1),flush=True)
profiles=[]
for (stage,w),a in group.items():
 ns=a.pop('nodes');a.update(nodes_sum=sum(ns),nodes_min=min(ns),nodes_median=statistics.median(ns),nodes_max=max(ns));profiles.append(dict(stage=stage,weights=w,**a))
assert total['games']==10560 and total['queries']==51510 and total['actions']==102939
out=dict(status='PASS_ALL_SAVED_PATH_COVERAGE',totals=dict(total),profiles=profiles,rows=rows,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALLactual597598599savedphysicalpaths andtheiractualfullroot/checkpointinventory/readback; lastUSIinfo node/depth counters, actions andsignedtypevariation byALLprices/family. Prior600 independentPython/PV/RNG/terminal audit sourcehashes unchanged. NativeC replay here derives features, notnewindependentcomplete gameaudit/holdout/training. Presence/featurevariation/querydepth isnotvalueidentifiability or causalpruning/quality; duplicatedobjective physicalfits keptdistinct andnotindependentfamilies. No sourceprices/selectedbad-axis tuning.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],totals=out['totals'],profiles=len(profiles),seconds=out['seconds'],new_go=0)))