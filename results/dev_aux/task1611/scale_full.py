from pathlib import Path
import json,collections,importlib.util,time,datetime,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1620';O.mkdir(exist_ok=False);start=time.monotonic();deadline=start+3300
plan=json.loads((R/'results/dev_aux/task1618/plan.json').read_bytes());base=json.loads((R/'results/dev_aux/task1586/study.json').read_bytes());plan.update({k:base[k] for k in ['binary','binary_sha256','variant_ini']});assert json.loads((R/'results/dev_aux/task1585/result.json').read_bytes())['error'] is None
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
G=R/'results/dev_aux/task1583';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};oracle=json.loads((G/'values.json').read_bytes())['value'];edges=[json.loads(x) for x in (G/'edges.jsonl').open()]
(O/'start.json').write_text(json.dumps({'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':json.loads((R/'.local_agent/session.json').read_bytes())['id'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'single_seconds_cap':3300,'no_restart':True},indent=2))
queries=0;profiles={};e=None;error=None;exits=[]
assert json.loads((R/'results/dev_aux/task1602/result.json').read_bytes())['status'].startswith('PASS')
selected=plan['primary_full_cases'];prices=sorted((x['R'],x['N'],x['B']) for x in selected)
provenance=[]
for path in sorted((R/'results/dev_aux/task1587').glob('*_choices.jsonl'))+sorted((R/'results/dev_aux/task1606').glob('*_choices.jsonl'))+sorted((R/'results/dev_aux/task1615').glob('*_choices.jsonl')):
 for line in path.open():
  x=json.loads(line);key=(x['R'],x['N'],x['B'])
  if key in prices:profiles.setdefault(key,{})[x['sid']]=x
 provenance.append({'path':path.as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(O/'cache_provenance.json').write_text(json.dumps({'source_audit':'task1602','sources':provenance,'cold64_reused':{str(k):len(v) for k,v in profiles.items()},'selected_from':'task1613fixedTRAINcohorts/POOLED','root_study':'task1612'},indent=2))
def check():
 if P.stop():raise InterruptedError('userstop')
 if time.monotonic()>deadline:raise TimeoutError('original3300seconds')
def solve(g):
 n=len(g['keys']);v=list(g['payoff']);rank=[0 if x is not None else None for x in v];pred=[[] for _ in v];remaining=[len(x or []) for x in g['adj']];q=collections.deque()
 for i,ll in enumerate(g['adj']):
  if ll:
   for j in ll:pred[j].append(i)
  if v[i] in (-1,1):q.append(i)
 while q:
  j=q.popleft()
  for i in pred[j]:
   if v[i] is not None:continue
   sid,c=g['keys'][i];own=states[sid][8]==c
   if (own and v[j]==1) or (not own and v[j]==-1):v[i]=v[j];rank[i]=rank[j]+1;q.append(i)
   else:
    remaining[i]-=1
    if remaining[i]==0:v[i]=v[j];rank[i]=1+max(rank[k] for k in g['adj'][i]);q.append(i)
 for i in range(n):
  if v[i] is None:v[i]=0
 for i,ll in enumerate(g['adj']):
  if ll:
   own=states[g['keys'][i][0]][8]==g['keys'][i][1];cv=[v[j] for j in ll];assert v[i]==(max(cv) if own else min(cv))
   if v[i]:
    exists=(own and v[i]==1) or (not own and v[i]==-1)
    assert any(v[j]==v[i] and rank[j]<rank[i] for j in ll) if exists else all(v[j]==v[i] and rank[j]<rank[i] for j in ll)
 return v,rank

def evaluate(price,phase):
 global queries
 g={'keys':[],'adj':[],'payoff':[],'basis':[],'roots':[]};index={};queue=collections.deque();cache=profiles.setdefault(price,{});pf=f'R{price[0]}_N{price[1]}_B{price[2]}_{phase}'
 def add(sid,c):
  key=(sid,c)
  if key in index:return index[key]
  i=len(g['keys']);index[key]=i;g['keys'].append(key);g['adj'].append(None)
  if sum(x!=12 for x in states[sid][:8])<=4:g['payoff'].append(oracle[sid]*(1 if states[sid][8]==c else -1));g['basis'].append('COMMON_RULE_ORACLE')
  else:g['payoff'].append(None);g['basis'].append('PENDING');queue.append(i)
  return i
 for fam in plan['families']:
  if fam['phase']==phase:
   for sid in fam['state_ids']:g['roots'].append((fam['family'],add(sid,states[sid][8])))
 with (O/(pf+'_choices.jsonl')).open('w') as f:
  try:
   while queue:
    check();i=queue.popleft();sid,c=g['keys'][i];s=states[sid];ll=edges[sid]['moves']
    if not ll:g['adj'][i]=[];g['basis'][i]='TERMINAL';g['payoff'][i]=(-1 if s[8]==c else 1) if edges[sid]['checked'] else 0;continue
    if s[8]==c and len(ll)>1:
     if sid not in cache:
      e.send('ucinewgame');e.ready();e.send('position fen '+T.fen(s))
      with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'price':price,'sid':sid,'phase':phase,'event':'SEND_INTENT','elapsed':time.monotonic()-start})+'\n')
      e.send('go nodes 64');queries+=1
      with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'price':price,'sid':sid,'phase':phase,'event':'SENT','elapsed':time.monotonic()-start})+'\n')
      raw=e.until(lambda z:z.startswith('bestmove '));move=raw[-1].split()[1];e.ready();child=dict(ll)[move]
      for line in raw[:-1]:
       ss=line.split()
       if 'pv' in ss:
        q=s
        for u in ss[ss.index('pv')+1:]:q=dict(T.moves(q))[u]
      cache[sid]={'sid':sid,'move':move,'child':child,'uci_info':raw[:-1],'position':T.fen(s),'budget':64,'R':price[0],'N':price[1],'B':price[2]}
      f.write(json.dumps(cache[sid])+'\n');f.flush()
     chosen=[(cache[sid]['move'],cache[sid]['child'])];g['basis'][i]='ACTUAL_OWN'
    else:chosen=ll;g['basis'][i]='SOLE_OWN' if s[8]==c else 'ALL_OPPONENT'
    g['adj'][i]=[add(j,c) for u,j in chosen]
  finally:(O/(pf+'_graph.json')).write_text(json.dumps(g,separators=(',',':')))
 v,r=solve(g);(O/(pf+'_values.json')).write_text(json.dumps({'value':v,'rank':r},separators=(',',':')))
 root=[(fam,v[i]) for fam,i in g['roots']];out={'R':price[0],'N':price[1],'B':price[2],'phase':phase,'mean':sum(x for f,x in root)/len(root),'root_values':root,'WDL':dict(collections.Counter(x for f,x in root)),'states':len(v),'basis':dict(collections.Counter(g['basis'])),'actual_cumulative_go':queries,'elapsed':time.monotonic()-start}
 (O/(pf+'_result.json')).write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='root_values'},flush=True);return out

rows=[]
try:
 e=P.M.start(R/plan['binary'],3,deadline,P.stop)
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/plan['variant_ini'])),('UCI_Variant','aux_tiny')]:
  e.send(f'setoption name {name} value {val}');rr=e.ready()
  if name=='UCI_Variant':assert any(z.startswith('info string variant aux_tiny files 3 ranks 4 ') for z in rr)
 for price in prices:
  e.send(f'devauxleafrnbp {price[0]} {price[1]} {price[2]} 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {price[0]} {price[1]} {price[2]} 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack
  (O/f'R{price[0]}_N{price[1]}_B{price[2]}_ack.json').write_text(json.dumps(ack));rows.append(evaluate(price,'DEV'))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e is not None:e.close();exits.append(e.p.poll())
out={'status':'COMPLETE' if error is None else 'PARTIAL_OR_FAILURE_PRESERVED','error':error,'actual_new_go':queries,'seconds':time.monotonic()-start,'exit_codes':exits,'all_owned_engines_closed':bool(exits) and all(x==0 for x in exits),'profiles':len(rows),'selected':selected,'scope':'Frozen1618commonRNBscale exposedmechanismcontrol C50scales0.5/1/2: actualcold64five policy +commonperfect4 oracle vsALLopponent. Reusedexactcold64 choices qualified1602; extra physicalqueriesunique. No newpricefit/DEVselection. Rootfamiliesdisjoint1586/1601 butcontinuationsoverlap.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
