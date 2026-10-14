from pathlib import Path
import json,collections,random,importlib.util,time,os,hashlib
_job_start=time.monotonic();R=Path.cwd();O=R/'results/dev_aux/task1579';O.mkdir(exist_ok=False);import datetime
(O/'start.json').write_text(json.dumps({'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':json.loads((R/'.local_agent/session.json').read_bytes())['id'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_plan':'task1578','no_restart':True},indent=2))
plan=json.loads((R/'results/dev_aux/task1578/plan.json').read_bytes());assert json.loads((R/'results/dev_aux/task1555/result.json').read_bytes())['status']=='COMPLETE_FIXED_POLICY_EXACT_BEST_RESPONSE_WDL';assert json.loads((R/'results/dev_aux/task1556/result.json').read_bytes())['status'].startswith('PASS')
G=R/'results/dev_aux/task1532';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));original=json.loads((G/'values.json').read_bytes())['value'];edge={};checked={}
for line in (G/'edges.jsonl').open():
 e=json.loads(line);i=e['id']
 if sum(x!=12 for x in states[i][:6])==5:edge[i]=e['moves'];checked[i]=e['checked']
oldids=json.loads((R/'results/dev_aux/task1538/original_ids.json').read_bytes());oldindex={sid:i for i,sid in enumerate(oldids)};oldvalues={(p,c):json.loads((R/f'results/dev_aux/task1555/B64_R{p}_C{c}.json').read_bytes())['value'] for p in plan['prices'] for c in [0,1]};study=json.loads((R/'results/dev_aux/task1549/study.json').read_bytes());roots=[(f['family'],i) for f in study['families'] for i in f['state_ids']]
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
start=time.monotonic();deadline=min(start+plan['max_query_seconds'],_job_start+plan['max_total_seconds']);engines={};graphs={};queries=0;error=None;exits=[]
def owner(s):return 0 if s[1]!=12 and s[2]!=12 else 1
def add(g,sid,color):
 key=(sid,color)
 if key in g['index']:return g['index'][key]
 i=len(g['keys']);g['index'][key]=i;g['keys'].append(key);g['adj'].append(None)
 if sid in oldindex:g['basis'].append('SOLVED_4ACTOR_ACTUAL_POLICY');g['payoff'].append(oldvalues[g['price'],color][oldindex[sid]]*(1 if states[sid][6]==color else -1))
 else:g['basis'].append('UNKNOWN_FRONTIER');g['payoff'].append(None);g['queue'].append(i)
 return i
try:
 for price in plan['prices']:
  g={'price':price,'index':{},'keys':[],'adj':[],'basis':[],'payoff':[],'queue':collections.deque(),'roots':[]};graphs[price]=g
  for f,sid in roots:g['roots'].append((f,add(g,sid,owner(states[sid]))))
  e=P.M.start(R/study['binary'],3,deadline,P.stop);engines[price]=e
  assert hashlib.sha256((R/study['binary']).read_bytes()).hexdigest()==study['binary_sha256']
  for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/study['variant_ini'])),('UCI_Variant','aux_tiny')]:
   e.send(f'setoption name {name} value {val}');rr=e.ready()
   if name=='UCI_Variant':assert any(z.startswith('info string variant aux_tiny files 3 ranks 4 ') for z in rr)
  e.send(f'devauxleafrnbp {price} 720 720 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {price} 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack;g['ack']=ack
 with (O/'new_choices.jsonl').open('w') as f:
  while any(g['queue'] for g in graphs.values()):
   if P.stop():raise InterruptedError('newuserstop')
   if queries>=plan['max_query_go'] or time.monotonic()>deadline:break
   progressed=False
   for price,g in graphs.items():
    if g.get('capped') or not g['queue'] or len(g['keys'])>=plan['max_graph_states_per_profile']:continue
    if queries>=plan['max_query_go'] or time.monotonic()>deadline:break
    i=g['queue'].popleft();sid,color=g['keys'][i];s=states[sid];ll=edge[sid];e=engines[price]
    if not ll:g['basis'][i]='ACTUAL_TERMINAL';g['payoff'][i]=(-1 if s[6]==color else 1) if checked[sid] else 0;g['adj'][i]=[];progressed=True;continue
    if s[6]==color and len(ll)>1:
     e.send('ucinewgame');e.ready();position='position fen '+T.fen(s);e.send(position);
     with (O/'go_journal.jsonl').open('a') as journal:journal.write(json.dumps({'price':price,'state_id':sid,'event':'SEND_INTENT','elapsed':time.monotonic()-_job_start})+'\n')
     e.send('go nodes '+str(plan['nodes']))
     with (O/'go_journal.jsonl').open('a') as journal:journal.write(json.dumps({'price':price,'state_id':sid,'event':'SENT','elapsed':time.monotonic()-_job_start})+'\n')
     raw=e.until(lambda z:z.startswith('bestmove '));move=raw[-1].split()[1];e.ready();child=dict(ll)[move]
     for info in raw[:-1]:
      ss=info.split()
      if 'pv' in ss:
       q=s
       for u in ss[ss.index('pv')+1:]:mm=dict(T.moves(q));assert u in mm;q=mm[u]
     f.write(json.dumps({'state_id':sid,'color':color,'leafR':price,'move':move,'child_id':child,'position':position,'command':'go nodes '+str(plan['nodes']),'uci_info':raw[:-1]})+'\n');f.flush();queries+=1;chosen=[(move,child)]
    elif s[6]==color:chosen=ll
    else:chosen=ll
    prospective={(j,color) for u,j in chosen if (j,color) not in g['index']}
    if len(g['keys'])+len(prospective)>plan['max_graph_states_per_profile']:
     g['capped']=True;g['queue'].appendleft(i);continue
    g['adj'][i]=[add(g,j,color) for u,j in chosen];g['basis'][i]='ACTUAL_COLD_OWN_CHOICE' if s[6]==color and len(ll)>1 else 'SOLE_OWN_ACTION' if s[6]==color else 'ALL_OPPONENT_ACTIONS';progressed=True
   if not progressed:break
   if queries and queries%5000==0:print('REACHABLE',queries,round(time.monotonic()-start,1),flush=True)
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 for e in engines.values():e.close();exits.append(e.p.poll())
def solve(g,bound):
 n=len(g['keys']);v=[None]*n;rank=[None]*n;pred=[[] for i in range(n)];remaining=[len(x or []) for x in g['adj']];q=collections.deque()
 for i,ll in enumerate(g['adj']):
  sid,color=g['keys'][i]
  if ll is None and g['basis'][i]=='UNKNOWN_FRONTIER':v[i]=-1 if bound=='lower' else original[sid]*(1 if states[sid][6]==color else -1);rank[i]=0
  elif g['payoff'][i] is not None:v[i]=g['payoff'][i];rank[i]=0
  else:
   assert ll
   for j in ll:pred[j].append(i)
  if v[i] in [-1,1]:q.append(i)
 while q:
  j=q.popleft()
  for i in pred[j]:
   if v[i] is not None:continue
   sid,color=g['keys'][i];own=states[sid][6]==color
   if (own and v[j]==1) or (not own and v[j]==-1):v[i]=v[j];rank[i]=rank[j]+1;q.append(i)
   else:
    remaining[i]-=1
    if remaining[i]==0:v[i]=v[j];rank[i]=1+max(rank[k] for k in g['adj'][i]);q.append(i)
 for i in range(n):
  if v[i] is None:v[i]=0
 for i,ll in enumerate(g['adj']):
  if not ll:continue
  sid,color=g['keys'][i];own=states[sid][6]==color;child=[v[j] for j in ll];assert v[i]==(max(child) if own else min(child))
  if v[i]:
   exists=(own and v[i]==1) or (not own and v[i]==-1)
   if exists:assert any(v[j]==v[i] and rank[j]<rank[i] for j in ll)
   else:assert all(v[j]==v[i] and rank[j]<rank[i] for j in ll)
  else:assert (all(x!=1 for x in child) if own else all(x!=-1 for x in child)) and 0 in child
 return v,rank
summaries=[];rootvals={}
for price,g in graphs.items():
 lo,lr=solve(g,'lower');hi,hr=solve(g,'upper');assert all(a<=b for a,b in zip(lo,hi));rootvals[price]=[(f,lo[i],hi[i]) for f,i in g['roots']]
 (O/f'graph_R{price}.json').write_text(json.dumps({k:v for k,v in g.items() if k not in ['index','queue']},separators=(',',':')))
 (O/f'bounds_R{price}.json').write_text(json.dumps({'lower':lo,'upper':hi,'lower_rank':lr,'upper_rank':hr},separators=(',',':')))
 summaries.append({'price':price,'reachable_states':len(g['keys']),'basis':dict(collections.Counter(g['basis'])),'roots_exact':sum(a==b for f,a,b in rootvals[price]),'mean_lower':sum(a for f,a,b in rootvals[price])/256,'mean_upper':sum(b for f,a,b in rootvals[price])/256})
base=rootvals[720];learn=rootvals[1728];assert [f for f,a,b in base]==[f for f,a,b in learn];family={}
for (f,a,b),(ff,c,d) in zip(base,learn):family.setdefault(f,[]).append((c-b,d-a))
lower=[sum(z[0] for z in family[f])/2 for f in range(128)];upper=[sum(z[1] for z in family[f])/2 for f in range(128)];rng=random.Random(2026674500);bl=[];bu=[]
for _ in range(10000):
 ss=[rng.randrange(128) for j in range(128)];bl.append(sum(lower[i] for i in ss)/128);bu.append(sum(upper[i] for i in ss)/128)
bl.sort();bu.sort();out={'status':'REACHABLE_POLICY_CERTIFIED_BOUNDS_PARTIAL' if any(g['basis'].count('UNKNOWN_FRONTIER') for g in graphs.values()) else 'REACHABLE_POLICY_CLOSED','actual_saved_go':queries,'possible_issued_go_range':[queries,queries+int(error is not None)],'error':error,'exit_codes':exits,'all_owned_engines_closed':all(x==0 for x in exits),'query_seconds':time.monotonic()-start,'total_seconds':time.monotonic()-_job_start,'profiles':summaries,'gain_interval':[sum(lower)/128,sum(upper)/128],'family95_conservative_gain_interval':[bl[249],bu[9749]],'family_gain_bounds':{f:[lower[f],upper[f]] for f in range(128)},'scope':'Fixed4096-five/64-four stagedcoldpolicy onexposed5actor jointrequiredmu; <=4 exactactualpolicy continuation, opponentALLlegal. Unknownfrontiers boundnotWDL labels. Artificialrank distance toknown/unknownboundary, not physicalmate. Neither entire694kcache nor newfit.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='family_gain_bounds'})
assert time.monotonic()-_job_start<plan['max_total_seconds']
