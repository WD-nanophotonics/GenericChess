import sys,json,time,hashlib,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task539';O.mkdir(exist_ok=True);assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));sys.path.insert(0,str(R/'results/dev_aux/task509'));import adapter as A;import run as G;import audit as V;from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';D=R/'results/dev_aux/task532/declaration.json';d=json.loads(D.read_bytes());assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];groups={};sources=[]
for condition in d['fit_conditions']:
 task=condition['task'];arm=condition['name'];file=R/f'results/dev_aux/task{task}/games.jsonl';assert json.loads((file.parent/'result.json').read_bytes())['status']=='fit_completed';sources.append(dict(path=file.relative_to(R).as_posix(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 for i,line in enumerate(file.open(encoding='utf-8'),1):
  g=json.loads(line);assert g['reset_policy']=='warm_game';k=(arm,tuple(g['weights']));item=dict(file=file.relative_to(R).as_posix(),line=i,game=g,condition=condition)
  if k not in groups:groups[k]=[item,item]
  else:groups[k][1]=item
(O/'declaration.json').write_text(json.dumps(dict(question='ALLactualprice/condition firstlast WHOLEGAME candidate+unit role sequences replayedfromfreshgamestart',study_declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),sources=sources,groups=[dict(arm=k[0],weights=list(k[1]),game_sources=[dict(file=x['file'],line=x['line']) for x in v]) for k,v in groups.items()],scope='Freshcandidate andunitifneeded processes, resetbothATGAMESTART; thenreplay EVERYactualrole query inoriginalorder/fullhistory/nodelimit torestore eachrolewarmTT/history. No isolated-go oronepriceprocess forunitmoves. Allnon-timeoutputs/resetmetadata verified. No newphysicalgames/refit/endpointchoice.',cost='Max784wholegame rolequerysequences/<=18816go, actualcountseparate. Basedoriginalbudgets1k/8k expected2-6minutes/900sfuse, no workers/fees/artificialsplit >1h.'),indent=2),encoding='utf-8');t0=time.perf_counter();acks=[];mismatches=[];go=0;pv=0;rolecounts={'candidate':0,'unit':0}
sem=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','player','ply']}
with (O/'queries.jsonl').open('w',encoding='utf-8') as journal:
 for (arm,w),pair in groups.items():
  for item in pair:
   G.stop();assert time.perf_counter()-t0<900;ec=ControlledEngine(w,journal,'warm_game');eu=ControlledEngine(d['fixed_opponent'],journal,'warm_game') if item['condition']['opponent']=='unit' else None;ec.begin_game();eu.begin_game() if eu else None;acks.append(dict(arm=arm,role='candidate',weights=list(w),prices=ec.prices))
   if eu:acks.append(dict(arm=arm,role='unit',weights=eu.w,prices=eu.prices))
   try:
    for qi,q in enumerate(item['game']['queries']):
     G.stop();e=ec if q['player']=='candidate' else eu;assert e is not None and e.w==q['weights'];new=e.search(q['initial_sfen'],q['history'],q['nodes_limit']);go+=1;rolecounts[q['player']]+=1;pv+=V.query(new)
     if sem(new)!=sem(q):mismatches.append(dict(arm=arm,source=dict(file=item['file'],line=item['line']),role=q['player'],query_index=qi,actual=q,fresh_replayed=new))
   finally:ec.close();eu.close() if eu else None
out=dict(status='PASS' if not mismatches else 'FAIL_REPLAY_SAVED',groups=len(groups),whole_game_replays=2*len(groups),actual_go=go,role_queries=rolecounts,PV_move_checks=pv,price_acks=acks,mismatches=mismatches,seconds=time.perf_counter()-t0,scope='ALLactualprice/condition firstlast wholegame sequences BOTHroles actualqueryhistory. No newphysicalgames/refit, no isolatedquerycounterfactual/warmgenericcorrectness proof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['price_acks','mismatches']}));assert not mismatches,'actualstate replay mismatch saved; diagnose'
