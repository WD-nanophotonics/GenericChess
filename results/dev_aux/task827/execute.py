import json,time,sys,os,hashlib,cProfile,pstats
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task827';P=R/'results/dev_aux/task828';start=time.monotonic();deadline=start+120
for n in [360,364,381,509,583]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from warm_adapter import ControlledEngine
from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());roots=[f for f in json.loads((R/'results/dev_aux/task784/roots_frozen.json').read_bytes())['roots'] if f['phase']=='development'];assert len(roots)==8
class GameBarrierEngine(ControlledEngine):
 def search(self,initial,history,nodes=1024):
  j=self.journal;self.journal=None
  try:q=super().search(initial,history,nodes)
  finally:self.journal=j
  if j:j.write(json.dumps(q)+'\n');j.flush()
  return q
save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8');d=dict(cap=12,nodes=1024,seed_base=0,fixed_opponent=old['initial_profiles'][0]['weights'],candidate=old['initial_profiles'][1]['weights'],pools=[dict(name='development',roots=roots)],blocks=['A','B','B','A'],executable_sha256=old['executable_sha256'],scope='827ABBA journal durability overhead control only, ALL64physical1024warmH12 fixedcandidate/opponent/devroots, nolearning/newholdoutclaims. A perqueryfsync/B closedgame fsyncbeforeclosedrecord; same semantic/PVchecks. cProfileallblocks equally.');assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];save(O/'execution_inputs.json',d);assert not(P/'games.jsonl').exists();games=go=0;acks=[];blocks=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for bi,policy in enumerate(d['blocks']):
  prof=cProfile.Profile();prof.enable();bt=time.monotonic();cls=ControlledEngine if policy=='A' else GameBarrierEngine;e=cls(d['candidate'],qj,'warm_game');eu=cls(d['fixed_opponent'],qj,'warm_game');acks.extend([dict(role='candidate',weights=e.w,prices=e.prices),dict(role='unit',weights=eu.w,prices=eu.prices)]);save(P/'price_acks.json',acks);bg=bo=0
  try:
   for f in roots:
    for color in [0,1]:
     e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,f,color,None,d,deadline);qj.flush();os.fsync(qj.fileno());g.update(block=bi,journal_policy=policy,pool='development',cap=12,quantity12=g['raw_quantity'],quantity24=None,fitness=g['goal']);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());games+=1;bg+=1;go+=len(g['queries']);bo+=len(g['queries'])
  finally:qj.flush();os.fsync(qj.fileno());e.close();eu.close()
  wall=time.monotonic()-bt;prof.disable();stats=pstats.Stats(prof);top=sorted(stats.stats.items(),key=lambda x:x[1][3],reverse=True)[:20];profile=[dict(file=Path(k[0]).name,line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in top];blocks.append(dict(block=bi,policy=policy,games=bg,go=bo,seconds=wall,profile=profile));print('IO_COST',bi,policy,bg,bo,round(wall,3),flush=True)
save(P/'result.json',dict(status='ALL64_ABBA_QUERY_DURABILITY_CONTROL_COMPLETE',actual_games=games,actual_go=go,blocks=blocks,seconds=time.monotonic()-start,source_scope=d['scope']));assert games==64
