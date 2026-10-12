import sys,json,time,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import audit as V
O=R/'results/dev_aux/task395';O.mkdir(exist_ok=True);file=R/'results/dev_aux/task369/games.jsonl';games=[json.loads(x) for x in file.read_text(encoding='utf-8').splitlines()];qs=[q for g in games for q in g['queries']];assert len(games)==16 and len(qs)==384;d=dict(frozen_game_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),games=16,go_records=384,order=['python','cshogi','cshogi','python'],methods='originaladapterA.validate_search vs independentliteralSFEN+cshogi V.query on SAMErecordedqueries, state/fullprices/chosenmove/PVs',new_go=0,goal='attribute existing researchwrapper overhead, not speedup ofengine/backend ornoisefreecomputer',parent_reference='task369actualsamebehaviour16games384go20.375s');(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');rows=[]
for index,method in enumerate(d['order']):
 t0=time.perf_counter();checks=0
 for q in qs:
  if method=='python':A.validate_search(q)
  else:checks+=V.query(q)
 rows.append(dict(index=index,method=method,seconds=time.perf_counter()-t0,queries=len(qs),PV_checks=checks if method=='cshogi' else 'originalreturnsBoolean'));print(rows[-1],flush=True)
result=dict(status='PASS',rows=rows,recorded_gamewall=sum(g['seconds'] for g in games),recorded_go_transport_seconds=sum(q['seconds'] for q in qs),new_go=0,scope='paired/counterbalancedtwo-validationimplementations on frozenoutputs, ordinaryconcurrency; scope legality/fullhistory/literalprices/PVs, not ruleout allsemanticdefects or productionacceptance');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('DONE',flush=True)