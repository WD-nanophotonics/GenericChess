import sys,json,time,hashlib,re,collections
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task478';assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));sys.path.insert(0,str(R/'results/dev_aux/task390'));import adapter as A;import run as G;import audit as V;from analyze import features
D=O/'declaration.json';d=json.loads(D.read_text(encoding='utf-8'));exes={'base':R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe','trace':R/'.local_agent/yaneura29/yaneura-material1-futility-trace.exe'};assert hashlib.sha256(exes['base'].read_bytes()).hexdigest()==d['base_executable_sha256'] and hashlib.sha256(exes['trace'].read_bytes()).hexdigest()==d['trace_executable_sha256'];t0=time.perf_counter();qs={};acks=[];pv=0;events=[]
pattern=re.compile(r'^info string auxfutility (main|q) alpha (-?\d+) base (-?\d+) value (-?\d+) board (-?\d+) full (-?\d+) pruned ([01]) ply (\d+) depth (-?\d+) move (\S+) sfen (.+)$')
for arm,exe in exes.items():
 A.EXE=exe;out=[]
 with (O/(arm+'_queries.jsonl')).open('w',encoding='utf-8') as journal:
  for budget in d['node_budgets']:
   for profile in d['initial_profiles']:
    for root in d['roots']:
     G.stop();assert time.perf_counter()-t0<180;e=A.Engine(profile['weights'],journal);acks.append(dict(arm=arm,weights=e.w,prices=e.prices,nodes=budget,root_seed=root['seed']))
     try:q=e.search(root['initial_sfen'],root['history'],budget);pv+=V.query(q);out.append(q)
     finally:e.close()
     for li,line in enumerate(q['lines']):
      if not line.startswith('info string auxfutility '):continue
      m=pattern.fullmatch(line);assert m,line;kind,*parts=m.groups();alpha,base,value,board,full,pruned,ply,depth=map(int,parts[:8]);u,sfen=parts[8:];assert value==base+board and bool(pruned)==(value<=alpha);b=C.Board(sfen);mv=b.move_from_usi(u);legal=b.is_legal(mv);v0,_=features(sfen);actual=None
      if legal:
       sign=1 if b.turn==0 else -1;b.push(mv);v1,_=features(b.sfen());actual=sign*sum(q['weights'][i]*(v1[i]-v0[i]) for i in range(16));assert actual==full,(u,sfen,actual,full)
      events.append(dict(kind=kind,query_index=len(out)-1,info_index=li,root_seed=root['seed'],phase=root['phase'],family=profile['name'],nodes=budget,weights=q['weights'],alpha=alpha,base=base,value=value,captured_board_price=board,full_increment=full,pruned=bool(pruned),native_legal=bool(legal),native_immediate_increment=actual,full_proxy=base+full,threshold_crossing=bool(legal and pruned and base+full>alpha),ply=ply,depth=depth,move=u,sfen=sfen,source=dict(file=f'results/dev_aux/task478/{arm}_queries.jsonl',line=len(out))))
 qs[arm]=out
sem=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v if not l.startswith('info string auxfutility ')] if k=='lines' else v) for k,v in q.items() if k!='seconds'}
mismatches=[dict(index=i,base=a,trace=b) for i,(a,b) in enumerate(zip(qs['base'],qs['trace'])) if sem(a)!=sem(b)];summary={kind:dict(events=len(es),native_legal=sum(e['native_legal'] for e in es),pruned_legal=sum(e['native_legal'] and e['pruned'] for e in es),threshold_crossings=sum(e['threshold_crossing'] for e in es)) for kind in ['main','q'] for es in [[e for e in events if e['kind']==kind]]};out=dict(status='PASS_RESPONSE_MATCH' if not mismatches else 'FAIL_RESPONSE_MATCH_SAVED',actual_go=sum(len(x) for x in qs.values()),new_games=0,PV_move_checks=pv,price_acks=acks,mismatches=mismatches,events=events,summary=summary,seconds=time.perf_counter()-t0,scope='Actualloggedfutility branches +independentnativelegality/literalmaterial. Thresholdcrossing changes the arithmetic pruningproxy if fullincrement replacesboard term, not proof continuationvalue>alpha, harmfulpruning, mate/WDL orlearninggain. Trace cappedfirst64/template/process, not allfrontier. ALL64base/trace inputs preserve originalnon-time/non-trace search responses ifPASS.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['price_acks','mismatches','events']});assert not mismatches,'logging altered finite responses; diagnose before branch interpretation'
