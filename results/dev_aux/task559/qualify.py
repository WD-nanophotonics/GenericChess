import sys,json,time,hashlib,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task559';D=R/'results/dev_aux/task553/declaration.json';d=json.loads(D.read_bytes());assert not (O/'result.json').exists()
for n in [360,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,audit as V
from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];assert (R/'results/dev_aux/task556/result.json').exists();groups={};sources=[]
for task,opp in [(554,'unit'),(555,'random')]:
 file=R/f'results/dev_aux/task{task}/games.jsonl';assert json.loads((file.parent/'result.json').read_bytes())['status']=='FIT_COMPLETE';sources.append(dict(file=file.relative_to(R).as_posix(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 for i,line in enumerate(file.open(),1):
  g=json.loads(line);k=(opp,tuple(g['weights']));item=dict(file=file.relative_to(R).as_posix(),line=i,game=g)
  if k not in groups:groups[k]=[item,item]
  else:groups[k][1]=item
(O/'declaration.json').write_text(json.dumps(dict(question='ALLactualtrainingprices first/last completewarmgame sequences BOTHroles exactlyreplay',study_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),sources=sources,groups=[dict(opponent=k[0],weights=list(k[1]),sources=[{n:x[n] for n in ['file','line']} for x in pair]) for k,pair in groups.items()],fuse=600,estimated='under2minutes max392 sequences/alloriginalgo, no newphysicalgames/learning; singleproducer',scope='Fullactualcandidate+unit queryinterleaving andfullhistory restores eachrole warmcontext. Randomcontroller draws retainedactualpath; replaynotnewgames orallpossiblepriceproof.'),indent=2),encoding='utf-8')
sem=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','player','ply']};start=time.perf_counter();acks=[];mismatch=[];go=0;pv=0
with (O/'queries.jsonl').open('w') as journal:
 for (opp,w),pair in groups.items():
  for item in pair:
   assert time.perf_counter()-start<600;ec=ControlledEngine(w,journal,'warm_game');eu=ControlledEngine(d['fixed_opponent'],journal,'warm_game') if opp=='unit' else None;ec.begin_game();eu.begin_game() if eu else None;acks.append(dict(role='candidate',weights=list(w),prices=ec.prices))
   if eu:acks.append(dict(role='unit',weights=eu.w,prices=eu.prices))
   try:
    for i,q in enumerate(item['game']['queries']):
     e=ec if q['player']=='candidate' else eu;new=e.search(q['initial_sfen'],q['history'],1024);pv+=V.query(new);go+=1
     if sem(new)!=sem(q):mismatch.append(dict(opponent=opp,weights=w,source={k:item[k] for k in ['file','line']},query_index=i,old=q,new=new))
   finally:ec.close();eu.close() if eu else None
out=dict(status='PASS' if not mismatch else 'FAIL_SAVED',groups=len(groups),whole_game_query_replays=2*len(groups),actual_go=go,PV_moves=pv,price_acks=acks,mismatches=mismatch,seconds=time.perf_counter()-start,scope='ALLactualprice firstlast wholewarmgame querysequences BOTHcandidate/unit roles, noisolatedgo equivalence/no physicalgame/refit/searchdefaultchange. Originalrandomdraws do not requireRNGre-execution for fixedqueryhistory replay; newnativepaths independentlyPythonchecked557.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['price_acks','mismatches']});assert not mismatch
