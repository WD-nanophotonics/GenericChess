import sys,json,time,hashlib,re,os,random
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task551';d=json.loads((O/'declaration.json').read_bytes());assert not (O/'games.jsonl').exists()
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V,controller as N
from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';A.validate_search=V.query;assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256']
src=(R/'results/dev_aux/task410/run_random.py').read_text(encoding='utf-8');src=src[src.index('def random_game('):src.index('arm=sys.argv[1]')];src=src.replace("d['seed_base']+2*f['index']+c","d['seed_base']+2*f['index']+c+(100 if f['phase']=='development' else 0)");exec(compile(src,'oldactualPythonrandomcontroller','exec'))
semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k!='seconds'}
semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k not in ['seconds','controller','reset_policy']}
t0=time.monotonic();rows=[];pairs=[];acks=[];case=0
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for nodes in d['budgets']:
  d['nodes']=nodes
  for p in d['profiles']:
   for opp in d['opponents']:
    for f in d['roots']:
     for color in d['colors']:
      rs=[]
      for ctrl in (d['controllers'] if case%2==0 else list(reversed(d['controllers']))):
       G.stop();assert time.monotonic()-t0<d['fuse'];ts=time.monotonic();ec=ControlledEngine(p['weights'],qj,'warm_game');eu=ControlledEngine([0]+[90]*7+[0]+[90]*6+[0],qj,'warm_game') if opp=='unit' else None;startup=time.monotonic()-ts;acks.append(dict(case=case,controller=ctrl,role='candidate',weights=ec.w,prices=ec.prices))
       if eu:acks.append(dict(case=case,controller=ctrl,role='unit',weights=eu.w,prices=eu.prices))
       ts=time.monotonic();ec.begin_game();eu.begin_game() if eu else None
       try:
        if ctrl=='native_rules':g=N.native_game(ec,eu,p['weights'],f,color,None,d,t0+d['fuse'])
        elif eu:g=G.game(ec,eu,p['weights'],f,color,None,cap=d['cap'],nodes=nodes,deadline=t0+d['fuse'])
        else:
         # Old randomcontroller requiresjournal; temporary sink also preserved to distinguishphysicalcalls.
         with (O/'python_random_journal.jsonl').open('a') as sink:g=random_game(ec,p['weights'],f,color,sink,t0+d['fuse'])
        g.update(controller=ctrl,reset_policy='warm_game');gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());wall=time.monotonic()-ts
       finally:ec.close();eu.close() if eu else None
       row=dict(case=case,controller=ctrl,nodes=nodes,profile=p['name'],opponent=opp,seed=f['seed'],color=color,order_index=len(rs),startup_seconds=startup,game_wall_seconds=wall,game=g);rows.append(row);rs.append(row)
      equal=semg(rs[0]['game'])==semg(rs[1]['game']);pairs.append(dict(case=case,nodes=nodes,profile=p['name'],opponent=opp,seed=f['seed'],color=color,order=[x['controller'] for x in rs],non_time_equal=equal,game_seconds={x['controller']:x['game']['seconds'] for x in rs},game_wall_seconds={x['controller']:x['game_wall_seconds'] for x in rs},go=len(rs[0]['game']['queries'])));case+=1;print(case,equal,round(time.monotonic()-t0,2),flush=True)
      (O/'progress.json').write_text(json.dumps(dict(pairs=pairs,seconds=time.monotonic()-t0)),encoding='utf-8')
out=dict(status='PASS' if all(p['non_time_equal'] for p in pairs) else 'FAIL_SAVED',actual_games=len(rows),actual_go=sum(len(x['game']['queries']) for x in rows),rows=rows,pairs=pairs,price_acks=acks,seconds=time.monotonic()-t0,scope=d['known_scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['rows','pairs','price_acks']})
