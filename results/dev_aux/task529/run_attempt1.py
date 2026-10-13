import sys,json,time,hashlib,re,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task529';D=O/'declaration.json';d=json.loads(D.read_bytes());assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));sys.path.insert(0,str(R/'results/dev_aux/task509'));sys.path.insert(0,str(R/'results/dev_aux/task528'));import adapter as A;import run as G;import audit as V;from transport import TransportEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';A.validate_search=V.query;assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];d['seed_base']=d['random_seed_base'];current_policy='warm_game';current_transport='separate'
src=(R/'results/dev_aux/task410/run_random.py').read_text(encoding='utf-8');src=src[src.index('def random_game('):src.index('arm=sys.argv[1]')].replace('out=dict(weights=w','out=dict(reset_policy=current_policy,transport=current_transport,weights=w');exec(compile(src,'frozen_random_transport_game','exec'))
t0=time.perf_counter();rows=[];acks=[];paired=[];case=0;mismatch=[]
semq=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','transport','transport_costs']}
semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k not in ['seconds','transport']}
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for policy in d['resource_policies']:
  for profile in d['initial_profiles']:
   for opponent in d['opponents']:
    for f in d['roots']:
     for color in d['colors']:
      case_rows=[]
      for transport in (['separate','batched'] if case%2==0 else ['batched','separate']):
       G.stop();assert time.perf_counter()-t0<600;current_policy=policy;current_transport=transport;start=time.perf_counter();ec=TransportEngine(profile['weights'],qj,policy,transport);eu=TransportEngine([0]+[90]*7+[0]+[90]*6+[0],qj,policy,transport) if opponent=='unit' else None;startup=time.perf_counter()-start;acks.append(dict(case=case,transport=transport,weights=ec.w,prices=ec.prices));start=time.perf_counter();ec.begin_game();eu.begin_game() if eu else None
       try:
        g=G.game(ec,eu,profile['weights'],f,color,None,cap=d['cap'],nodes=d['nodes'],deadline=t0+600) if eu else random_game(ec,profile['weights'],f,color,gj,t0+600)
        if eu:g.update(reset_policy=policy,transport=transport);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno())
        wall=time.perf_counter()-start
       finally:ec.close();eu.close() if eu else None
       row=dict(case=case,policy=policy,profile=profile['name'],opponent=opponent,root_seed=f['seed'],color=color,transport=transport,order_index=len(case_rows),startup_wall=startup,game_wall=wall,game=g,source=dict(file='results/dev_aux/task529/games.jsonl',line=len(rows)+1));rows.append(row);case_rows.append(row)
      equal=semg(case_rows[0]['game'])==semg(case_rows[1]['game']);paired.append(dict(case=case,policy=policy,profile=profile['name'],opponent=opponent,root_seed=f['seed'],color=color,order=[r['transport'] for r in case_rows],non_time_equal=equal,game_wall={r['transport']:r['game_wall'] for r in case_rows},startup_wall={r['transport']:r['startup_wall'] for r in case_rows}));
      if not equal:mismatch.append(case)
      case+=1;print(policy,profile['name'],opponent,case,round(time.perf_counter()-t0,2),flush=True)
out=dict(status='PASS' if not mismatch else 'FAIL_SAVED',actual_games=len(rows),actual_go=sum(len(r['game']['queries']) for r in rows),rows=rows,paired=paired,price_acks=acks,mismatches=mismatch,seconds=time.perf_counter()-t0,scope=d['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['rows','paired','price_acks']}));assert not mismatch
