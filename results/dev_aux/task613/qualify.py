import json,hashlib,time,sys,os,re,itertools
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task613';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());oldsha='c69d96c10244b65da124d66c653449bc701680f4e3da05ec48b3979ef950d2e2';b=json.loads((R/'results/dev_aux/task612/result.json').read_bytes());assert b['status']=='PRIVATE_INCREMENTAL_BUILD_PASS';newsha=b['executable_sha256'];profiles=json.loads((R/'results/dev_aux/task599/result.json').read_bytes())['profiles'];families=sorted({f['source_family'] for f in d['roots']});roots=[next(f for f in d['roots'] if f['source_family']==seed) for seed in families];plan=dict(question='Freshcountermode0 reproducespinnedoriginal non-timeFULLwarmqueries/paths beforeactualintervention?',profiles=profiles,roots=roots,colors=[0,1],old_executable_sha256=oldsha,new_executable_sha256=newsha,cap=12,nodes=1024,seed_base=d['seed_base'],fuse_seconds=180,planned_physical_games=4*11*2*2,comparison='Everyactualquery/action/material/fullhistory/goal/node/PV exactlyequals excludingonlyseconds/time/nps andnewdiagnosticcarrier; no isolated-go replay',scope='ALL4actual596prices/onefirstrootperALL11eligiblefamilies BOTHcolors/wholewarm12plygames. Exposedprotocolqualification, notindependentpricevalidation; no sourcefitness/training/newfamilies.');(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
fields=['eligible','old_pruned','new_pruned','rescued_by_new','newly_pruned_by_new','new_gain_larger','new_gain_smaller']
class CounterEngine(ControlledEngine):
 def __init__(self,w,journal=None,policy='warm_game'):self.diagjournal=journal;super().__init__(w,None,policy)
 def search(self,initial,history,nodes=1024):
  q=super().search(initial,history,nodes);self.send('auxcapture');line=self.until(lambda x:x.startswith('info string auxcapture '))[-1];a=list(map(int,line.split()[3:]));assert len(a)==8 and a[0] in [0,1];s=dict(zip(fields,a[1:]));assert s['old_pruned']-s['new_pruned']==s['rescued_by_new']-s['newly_pruned_by_new'];assert all(x<=s['eligible'] for x in s.values());q['capture_diag']=dict(mode=a[0],**s)
  if self.diagjournal:self.diagjournal.write(json.dumps(q)+'\n');self.diagjournal.flush();os.fsync(self.diagjournal.fileno())
  return q
semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','capture_diag']}
semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k not in ['seconds','implementation','profile']}
start=time.monotonic();deadline=start+180;rows=[];acks=[];go=0
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for pi,p in enumerate(profiles):
  ee=[]
  for label,exe,cls in [('original',R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe',ControlledEngine),('prototype_mode0',R/'.local_agent/yaneura33_capture/yaneura-capture-diag.exe',CounterEngine)]:
   A.EXE=exe;assert hashlib.sha256(exe.read_bytes()).hexdigest()==(oldsha if label=='original' else newsha);os.environ['DEV_AUX_CAPTURE_GAIN_MODE']='0';e=cls(p['weights'],qj,'warm_game');ee.append(e);acks.append(dict(implementation=label,profile=pi,weights=e.w,prices=e.prices));(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
  try:
   for f in roots:
    for c in [0,1]:
     pair=[]
     for label,e in zip(['original','prototype_mode0'],ee):
      G.stop();assert time.monotonic()<deadline;e.begin_game();g=native_game(e,None,e.w,f,c,None,d,deadline);g.update(implementation=label,profile=pi);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());go+=len(g['queries']);pair.append(g)
     assert semg(pair[0])==semg(pair[1]),(pi,f['index'],c);rows.append(dict(profile=pi,family=f['source_family'],root=f['index'],color=c,all_non_time_equal=True,go=sum(len(g['queries']) for g in pair),source_lines=[len(rows)*2+1,len(rows)*2+2]))
  finally:
   for e in ee:e.close()
  print('mode0qualified',pi,len(rows),round(time.monotonic()-start,2),flush=True)
out=dict(status='PASS_ALL_MODE0_QUALIFICATION',actual_games=2*len(rows),actual_go=go,fullwarm_game_pairs=len(rows),all_non_time_equal=True,rows=rows,price_acks=acks,seconds=time.monotonic()-start,scope=plan['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['rows','price_acks']}))