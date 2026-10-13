import sys,json,time,hashlib,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task515';assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task381'));sys.path.insert(0,str(R/'results/dev_aux/task509'));import adapter as A;import audit as V;from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';D=R/'results/dev_aux/task510/declaration.json';d=json.loads(D.read_text(encoding='utf-8'));assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];groups={};sources=[]
for task,arm in [(511,'cold_per_query'),(512,'warm_game')]:
 file=R/f'results/dev_aux/task{task}/games.jsonl';assert json.loads((file.parent/'result.json').read_text(encoding='utf-8'))['status']=='fit_completed';sources.append(dict(path=file.relative_to(R).as_posix(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 for i,line in enumerate(file.open(encoding='utf-8'),1):
  g=json.loads(line);assert g['reset_policy']==arm;k=(arm,tuple(g['weights']));item=dict(file=file.relative_to(R).as_posix(),line=i,game=g)
  if k not in groups:groups[k]=[item,item]
  else:groups[k][1]=item
(O/'declaration.json').write_text(json.dumps(dict(question='ALLactualprice vectors first/lastWHOLEGAME candidatequery sequence reproduced withdeclaredwarmstate',study_declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),sources=sources,groups=[dict(arm=k[0],weights=list(k[1]),game_sources=[dict(file=x['file'],line=x['line']) for x in v]) for k,v in groups.items()],scope='Freshprocess +begin_game thenreplay EVERYcandidate search in originalgame order/fullhistory torestore actualwarmTT/history. First/last isolatedgo NOTadequateforwarmcondition. No newgames/refit/trajectorychoice; allnon-time info/modelreset metadata compared.',cost='max392wholegame querysequences/~4000go expected<1min/600sfuse, singleproducer AFTER510ends; countactualgo separate, no fees/workers'),indent=2),encoding='utf-8');t0=time.perf_counter();acks=[];mismatches=[];go=0;pv=0
sem=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','player','ply']}
with (O/'queries.jsonl').open('w',encoding='utf-8') as journal:
 for (arm,w),pair in groups.items():
  for item in pair:
   assert time.perf_counter()-t0<600;e=ControlledEngine(w,journal,arm);e.begin_game();acks.append(dict(arm=arm,weights=list(w),prices=e.prices))
   try:
    for qi,q in enumerate(item['game']['queries']):
     new=e.search(q['initial_sfen'],q['history'],1024);go+=1;pv+=V.query(new)
     if sem(new)!=sem(q):mismatches.append(dict(arm=arm,source=dict(file=item['file'],line=item['line']),query_index=qi,actual=q,fresh_replayed=new))
   finally:e.close()
out=dict(status='PASS' if not mismatches else 'FAIL_REPLAY_SAVED',groups=len(groups),whole_game_replays=2*len(groups),actual_go=go,PV_move_checks=pv,price_acks=acks,mismatches=mismatches,seconds=time.perf_counter()-t0,scope='ALLactualprice first/lastwholegame sequences, fullwarmcontext recreated byactualqueryreplay fromcoldgamestart, no isolatedqueryequivalence claim. Replays no newphysicalgames/refit.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['price_acks','mismatches']});assert not mismatches,'actual warmcontext mismatch saved; diagnose, no unverifiedsuccess'
