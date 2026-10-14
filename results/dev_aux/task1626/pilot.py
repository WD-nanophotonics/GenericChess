import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,datetime,collections,importlib.util,hashlib,random
R=Path.cwd();O=R/'results/dev_aux/task1631';O.mkdir(exist_ok=False);jobstart=time.monotonic();plan=json.loads((R/'results/dev_aux/task1630/plan.json').read_bytes());jobdeadline=jobstart+plan['single_total_seconds']
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
G=R/'results/dev_aux/task1627';teacherstates=list(map(tuple,json.loads((G/'states.json').read_bytes())));teacherix={s:i for i,s in enumerate(teacherstates)};teacher=json.loads((G/'values.json').read_bytes())['value'];assert json.loads((R/'results/dev_aux/task1628/result.json').read_bytes())['status'].startswith('PASS');assert json.loads((R/'results/dev_aux/task1629/result.json').read_bytes())['error'] is None
(O/'start.json').write_text(json.dumps({'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':json.loads((R/'.local_agent/session.json').read_bytes())['id'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'total_seconds_cap':600,'no_restart':True},indent=2));queries=0;profile_summaries=[];graphs={};exits=[];error=None

def solve(g,bound):
 n=len(g['keys']);v=list(g['payoff']);rank=[0 if x is not None else None for x in v];pred=[[] for _ in v];remaining=[len(x or []) for x in g['adj']];q=collections.deque()
 for i,ll in enumerate(g['adj']):
  if g['basis'][i]=='UNKNOWN_FRONTIER':v[i]=-1 if bound=='lower' else 1;rank[i]=0
  if ll:
   for j in ll:pred[j].append(i)
  if v[i] in (-1,1):q.append(i)
 while q:
  j=q.popleft()
  for i in pred[j]:
   if v[i] is not None:continue
   s,c=g['keys'][i];own=s[8]==c
   if (own and v[j]==1) or (not own and v[j]==-1):v[i]=v[j];rank[i]=rank[j]+1;q.append(i)
   else:
    remaining[i]-=1
    if remaining[i]==0:v[i]=v[j];rank[i]=1+max(rank[k] for k in g['adj'][i]);q.append(i)
 for i in range(n):
  if v[i] is None:v[i]=0
 for i,ll in enumerate(g['adj']):
  if ll:
   s,c=g['keys'][i];own=s[8]==c;ch=[v[j] for j in ll];assert v[i]==(max(ch) if own else min(ch))
   if v[i]:
    exists=(own and v[i]==1) or (not own and v[i]==-1);assert any(v[j]==v[i] and rank[j]<rank[i] for j in ll) if exists else all(v[j]==v[i] and rank[j]<rank[i] for j in ll)
   else:assert 0 in ch and (all(x<=0 for x in ch) if own else all(x>=0 for x in ch))
 return v,rank

for price in map(tuple,plan['profiles']):
 prefix=f'R{price[0]}_N{price[1]}_B{price[2]}';profile_start=time.monotonic();deadline=min(profile_start+300,jobdeadline);g={'keys':[],'adj':[],'payoff':[],'basis':[],'roots':[]};index={};queue=collections.deque();e=None;physical=0;profile_error=None;cap_reason=None
 def add(s,c):
  key=(s,c)
  if key in index:return index[key]
  i=len(g['keys']);index[key]=i;g['keys'].append(key);g['adj'].append(None)
  if sum(x!=16 for x in s[:8])<=4:g['payoff'].append(teacher[teacherix[s]]*(1 if s[8]==c else -1));g['basis'].append('COMMON_PERFECT_4_ORACLE')
  else:g['payoff'].append(None);g['basis'].append('UNKNOWN_FRONTIER');queue.append(i)
  return i
 for f in plan['families']:
  for s in f['roots']:s=tuple(s);g['roots'].append((f['family'],add(s,s[8])))
 try:
  P.stop();e=P.M.start(R/plan['binary'],3,deadline,P.stop);assert hashlib.sha256((R/plan['binary']).read_bytes()).hexdigest()==plan['binary_sha256']
  for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/plan['variant_ini'])),('UCI_Variant','aux_tiny')]:
   e.send(f'setoption name {name} value {val}');ack=e.ready()
   if name=='UCI_Variant':assert any(z.startswith('info string variant aux_tiny files 4 ranks 4 ') for z in ack)
  e.send(f'devauxleafrnbp {price[0]} {price[1]} {price[2]} 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {price[0]} {price[1]} {price[2]} 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack;(O/(prefix+'_ack.json')).write_text(json.dumps(ack))
  with (O/(prefix+'_choices.jsonl')).open('w') as f:
   while queue:
    P.stop()
    if time.monotonic()>=deadline or physical>=30000:cap_reason='ORIGINAL_TIME_OR_QUERY_CAP';break
    i=queue.popleft();s,c=g['keys'][i];ll=T.moves(s)
    if not ll:g['adj'][i]=[];g['basis'][i]='TERMINAL';g['payoff'][i]=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;continue
    if s[8]==c and len(ll)>1:
     e.send('ucinewgame');e.ready();e.send('position fen '+T.fen(s))
     with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'price':price,'state':s,'color':c,'event':'SEND_INTENT','elapsed':time.monotonic()-jobstart})+'\n')
     e.send('go nodes 64');queries+=1;physical+=1
     with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'price':price,'state':s,'color':c,'event':'SENT','elapsed':time.monotonic()-jobstart})+'\n')
     raw=e.until(lambda x:x.startswith('bestmove '));move=raw[-1].split()[1];e.ready();t=dict(ll)[move]
     for line in raw[:-1]:
      ss=line.split()
      if 'pv' in ss:
       q=s
       for u in ss[ss.index('pv')+1:]:q=dict(T.moves(q))[u]
     f.write(json.dumps({'price':price,'state':s,'color':c,'move':move,'child':t,'position':T.fen(s),'command':'go nodes 64','uci_info':raw[:-1]})+'\n');f.flush();chosen=[(move,t)];basis='ACTUAL_OWN'
    else:chosen=ll;basis='SOLE_OWN' if s[8]==c else 'ALL_OPPONENT'
    prospective={(t,c) for u,t in chosen if (t,c) not in index}
    if len(g['keys'])+len(prospective)>80000:cap_reason='ORIGINAL80000STATE_CAP';queue.appendleft(i);break
    g['adj'][i]=[add(t,c) for u,t in chosen];g['basis'][i]=basis
 except BaseException as ex:profile_error=type(ex).__name__+':'+str(ex)
 finally:
  if e is not None:e.close();exits.append(e.p.poll())
 lo,lr=solve(g,'lower');hi,hr=solve(g,'upper');assert all(a<=b for a,b in zip(lo,hi));root=[(f,lo[i],hi[i]) for f,i in g['roots']];summary={'price':price,'states':len(g['keys']),'basis':dict(collections.Counter(g['basis'])),'actual_go':physical,'seconds':time.monotonic()-profile_start,'roots_exact':sum(a==b for f,a,b in root),'mean_lower':sum(a for f,a,b in root)/32,'mean_upper':sum(b for f,a,b in root)/32,'root_bounds':root,'cap_reason':cap_reason,'error':profile_error}
 (O/(prefix+'_graph.json')).write_text(json.dumps(g,separators=(',',':')));(O/(prefix+'_bounds.json')).write_text(json.dumps({'lower':lo,'upper':hi,'lower_rank':lr,'upper_rank':hr},separators=(',',':')));(O/(prefix+'_result.json')).write_text(json.dumps(summary,indent=2));profile_summaries.append(summary);graphs[price]=root;print({k:v for k,v in summary.items() if k!='root_bounds'},flush=True)
 if profile_error is not None:error=profile_error;break
out={'status':'ALL_ROOT_BOUNDS_EXACT' if len(graphs)==2 and all(a==b for x in graphs.values() for f,a,b in x) else 'PARTIAL_CERTIFIED_BOUNDS_OR_FAILURE','actual_go':queries,'seconds':time.monotonic()-jobstart,'profiles':profile_summaries,'exit_codes':exits,'all_owned_engines_closed':len(exits)==len(profile_summaries) and all(x==0 for x in exits),'error':error,'scope':'4x4actualfixedcold64five policy vsALLopponent, commonperfect4oracle; nofull5oracle, UNKNOWNboundsnotdraw. Fixed3x4priorC50transfer, NOT4x4pricelearning. Frozen16rootfamilies pressurelaw, colorsnotindependent; baseline/C50 each300s, total600s.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='profiles'})
