import sys,json,time,random,hashlib,cProfile,pstats,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task562'
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V,controller as N
from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';decl=json.loads((O/'declaration.json').read_bytes());policy=decl['policy'];f=decl['root'];w=decl['weights'];d=dict(cap=24,nodes=1024,seed_base=2026104492);remaining=120-(time.time()-policy['frozen_at']);assert remaining>0, 'originalprofilefuseexpired';start=time.monotonic();rows=[];gs=[];acks=[]
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for ctrl in decl['order']:
  G.stop();assert time.monotonic()-start<remaining;ec=ControlledEngine(w,qj,'warm_game');eu=ControlledEngine(w,qj,'warm_game');ec.begin_game();eu.begin_game();acks.extend([dict(role=role,weights=w,prices=e.prices) for role,e in [('candidate',ec),('unit',eu)]]);p=cProfile.Profile()
  try:
   p.enable();g=N.native_game(ec,eu,w,f,0,None,d,start+remaining) if ctrl=='native_rules' else G.game(ec,eu,w,f,0,None,cap=24,nodes=1024,deadline=start+remaining);p.disable()
  finally:ec.close();eu.close()
  g.update(controller=ctrl,reset_policy='warm_game');gj.write(json.dumps(g)+'\n');gj.flush();stats=pstats.Stats(p);rs=[]
  for (file,line,name),(cc,nc,tt,ct,callers) in stats.stats.items():rs.append(dict(file=Path(file).name,line=line,function=name,primitive_calls=cc,total_calls=nc,self_seconds=tt,cumulative_seconds=ct))
  rows.append(dict(controller=ctrl,profiled_game_seconds=g['seconds'],total_profile_self_seconds=sum(x['self_seconds'] for x in rs),function_stats=sorted(rs,key=lambda x:x['self_seconds'],reverse=True)));gs.append(g)
semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k!='seconds'};semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k not in ['seconds','controller']};equal=semg(gs[0])==semg(gs[1]);out=dict(status='PASS' if equal else 'FAIL_SAVED',actual_games=2,actual_go=sum(len(g['queries']) for g in gs),non_time_equal=equal,rows=rows,price_acks=acks,seconds=time.monotonic()-start,scope=decl['scope']+' Instrumentationchangeswall; exclusive/self times avoidaddingoverlapping cumulativecosts. Exactnon-time outputs requiredbeforeattribution.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],actual_go=out['actual_go'],rows=[dict(controller=x['controller'],profiled_game_seconds=x['profiled_game_seconds'],top_self=x['function_stats'][:12]) for x in rows])));assert equal
