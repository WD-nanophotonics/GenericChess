import sys,json,time,random,os,hashlib,cProfile,pstats
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task504';assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
D=O/'declaration.json';d=json.loads(D.read_text(encoding='utf-8'));d['seed_base']=d['random_seed_base'];A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];A.validate_search=V.query;PHASES=[];current_case={}
class PhaseEngine(A.Engine):
 def search(self,initial,history,nodes=1024):
  t0=time.perf_counter();self.send('isready');ready=self.until(lambda x:x=='readyok');t1=time.perf_counter();self.position(initial,history);t2=time.perf_counter();self.send('auxstate');state=self.until(lambda x:x.startswith('info string auxstate '))[-1];t3=time.perf_counter();t=time.monotonic();cmd=f'go nodes {nodes}';self.send(cmd);lines=self.until(lambda x:x.startswith('bestmove '));t4=time.perf_counter();phase=dict(cold_ready=t1-t0,position_send=t2-t1,state_roundtrip=t3-t2,go_roundtrip=t4-t3);q=dict(initial_sfen=initial,history=list(history),weights=self.w,nodes_limit=nodes,cold_isready=ready,state=state,command=cmd,lines=lines,bestmove=lines[-1].split()[1],seconds=time.monotonic()-t,phase_costs=phase)
  j0=time.perf_counter()
  if self.journal:self.journal.write(json.dumps(q,ensure_ascii=False)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
  j1=time.perf_counter();PHASES.append(dict(**current_case,phases=phase,journal_wall=j1-j0,total_search_call_wall=j1-t0));return q
src=(R/'results/dev_aux/task410/run_random.py').read_text(encoding='utf-8');src=src[src.index('def random_game('):src.index('arm=sys.argv[1]')];exec(compile(src,'actual_cost_random_controller','exec'))
t0=time.perf_counter();rows=[];profiles=[];startup=[];acks=[];private=R/'.local_agent/profiles';private.mkdir(exist_ok=True);unit=[0]+[90]*7+[0]+[90]*6+[0]
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 case=0
 for p in d['initial_profiles']:
  for env in d['opponents']:
   order=[False,True] if case%2==0 else [True,False]
   for profiled in order:
    G.stop();assert time.perf_counter()-t0<180;current_case=dict(case=case,family=p['name'],opponent=env,profiled=profiled);st=time.perf_counter();ec=PhaseEngine(p['weights'],qj);eu=PhaseEngine(unit,qj) if env=='unit' else None;startup.append(dict(**current_case,wall=time.perf_counter()-st));acks.append(dict(**current_case,weights=ec.w,prices=ec.prices));pr=cProfile.Profile();start=time.perf_counter()
    try:
     if profiled:pr.enable()
     g=G.game(ec,eu,p['weights'],d['root'],d['candidate_color'],None,cap=d['cap'],nodes=d['nodes'],deadline=t0+180) if eu else random_game(ec,p['weights'],d['root'],d['candidate_color'],gj,t0+180)
     if profiled:pr.disable()
     wall=time.perf_counter()-start
     if eu:gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno())
    finally:ec.close();eu.close() if eu else None
    rows.append(dict(**current_case,game=g,measured_game_wall=wall,source=dict(file='results/dev_aux/task504/games.jsonl',line=len(rows)+1)))
    if profiled:
     pr.dump_stats(str(private/f'504-case{case}.prof'));ps=pstats.Stats(pr);functions=[]
     for (file,line,fn),(cc,nc,tt,ct,callers) in ps.stats.items():
      path=Path(file);label=path.relative_to(R).as_posix() if path.is_absolute() and path.is_relative_to(R) else ('external/'+path.name if path.is_absolute() else file);functions.append(dict(file=label,line=line,function=fn,primitive_calls=cc,total_calls=nc,self_wall=tt,cumulative_wall=ct))
     profiles.append(dict(**current_case,total_profile_wall=ps.total_tt,functions=sorted(functions,key=lambda x:x['cumulative_wall'],reverse=True)[:40]))
   case+=1
semq=lambda q:{k:([ ' '.join(__import__('re').sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','phase_costs']}
def semg(g):return {k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k!='seconds'}
for c in range(4):
 rs=[x for x in rows if x['case']==c];assert len(rs)==2 and semg(rs[0]['game'])==semg(rs[1]['game']),'profile altered semanticresponse; saved raw beforediagnosis'
out=dict(status='PASS_ACTUAL_COST_PROFILE',actual_games=len(rows),actual_go=len(PHASES),rows=rows,query_phases=PHASES,startup=startup,profile_functions=profiles,price_acks=acks,seconds=time.perf_counter()-t0,scope=d['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],games=len(rows),actual_go=len(PHASES),seconds=out['seconds'],normal_wall=sum(x['measured_game_wall'] for x in rows if not x['profiled']),profiled_wall=sum(x['measured_game_wall'] for x in rows if x['profiled']),phase_sums={k:sum(x['phases'][k] for x in PHASES if not x['profiled']) for k in PHASES[0]['phases']}),ensure_ascii=True))
