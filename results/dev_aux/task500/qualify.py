import sys,json,time,hashlib,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task500';assert not (O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
D=R/'results/dev_aux/task495/declaration.json';d=json.loads(D.read_text(encoding='utf-8'));exes={'handSEE':R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe','fullCapture':R/'.local_agent/yaneura30/yaneura-material1-full-capture-futility.exe'};assert {k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in exes.items()}==d['executable_hashes'];groups={};sources=[]
for task,arm in [(496,'handSEE'),(497,'fullCapture')]:
 file=R/f'results/dev_aux/task{task}/queries.jsonl';assert json.loads((file.parent/'result.json').read_text(encoding='utf-8'))['status']=='fit_completed';sources.append(dict(path=file.relative_to(R).as_posix(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 for line,text in enumerate(file.open(encoding='utf-8'),1):
  q=json.loads(text);assert q['nodes_limit']==1024;k=(arm,tuple(q['weights']));item=dict(file=file.relative_to(R).as_posix(),line=line,query=q)
  if k not in groups:groups[k]=[item,item]
  else:groups[k][1]=item
(O/'declaration.json').write_text(json.dumps(dict(question='ALLactuallyusedprice vectors first/last cold input reproduced underfresh engine process',study_declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),sources=sources,executable_hashes=d['executable_hashes'],groups=[dict(arm=k[0],weights=list(k[1]),sources=[dict(file=x['file'],line=x['line']) for x in v]) for k,v in groups.items()],estimated_cost='under1min/300sfuse,2go perpricegroup no games/training',scope='freshprocess vs actualsamebinary fit coldreuse responses, fullinfoexcepttime/NPS; not old-vs-hand equality or arbitraryoptions/globaldepthproof'),indent=2),encoding='utf-8');t0=time.perf_counter();go=0;pv=0;acks=[];mismatch=[]
sem=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k not in ['seconds','player','ply']}
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj:
 for (arm,w),pair in groups.items():
  G.stop();assert time.perf_counter()-t0<300;A.EXE=exes[arm];e=A.Engine(w,qj);acks.append(dict(arm=arm,weights=list(w),prices=e.prices))
  try:
   for item in pair:
    q=item['query'];new=e.search(q['initial_sfen'],q['history'],1024);go+=1;pv+=V.query(new)
    if sem(new)!=sem(q):mismatch.append(dict(arm=arm,source=dict(file=item['file'],line=item['line']),actual=q,fresh=new))
  finally:e.close()
out=dict(status='PASS' if not mismatch else 'FAIL_SAVED',groups=len(groups),actual_go=go,PV_move_checks=pv,price_acks=acks,mismatches=mismatch,seconds=time.perf_counter()-t0,scope='ALLactualfitprices first/last coldreuse response vsfresh engine. DifferentSEEarms intentionallynotrequiredtomatch; no newgame/fitting.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['price_acks','mismatches']});assert not mismatch,'finite reproducibility failure saved, diagnose nothide'
