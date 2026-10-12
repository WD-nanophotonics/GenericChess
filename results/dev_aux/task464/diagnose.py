import json,sys,time,hashlib
from pathlib import Path
import numpy as np
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task390'));from analyze import features
O=R/'results/dev_aux/task464';tasks=[int(x) for x in sys.argv[1:]] or [432,433,439,440,449,450];axes=[2,3,4,5,6,7,9,10,11,12,13,14];unit=[0]+[90]*7+[0]+[90]*6+[0];rows=[];t0=time.perf_counter()
for task in tasks:
 folder=R/f'results/dev_aux/task{task}';E=json.loads((folder/'endpoints.json').read_text(encoding='utf-8'));initial=[u for u in E['updates'] if u['family']=='unit'][0]['candidates'][0];refs={x['line'] for x in initial['sources']};games=[]
 for line,text in enumerate((folder/'games.jsonl').open(encoding='utf-8'),1):
  if line in refs:games.append(json.loads(text))
 assert len(games)==len(refs) and all(g['weights']==unit for g in games)
 played=[];pv=[];presence=[0]*16;pp=[0]*16;cells=[];queries=0
 for g in games:
  cp=[];cv=[]
  for s in [g['root']['expected_sfen']]+[a['after_sfen'] for a in g['actions']]:
   v,types=features(s);played.append([v[a] for a in axes]);cp.append([v[a] for a in axes]);presence=[x+int(y>0) for x,y in zip(presence,types)]
  for q in g['queries']:
   queries+=1;b=C.Board(q['initial_sfen'])
   for u in q['history']:b.push_usi(u)
   for text in q['lines']:
    if ' pv ' not in text:continue
    p=b.copy()
    for u in text.split(' pv ',1)[1].split():
     m=p.move_from_usi(u);assert p.is_legal(m);p.push(m);v,types=features(p.sfen());pv.append([v[a] for a in axes]);cv.append([v[a] for a in axes]);pp=[x+int(y>0) for x,y in zip(pp,types)]
  rank=lambda x:int(np.linalg.matrix_rank(np.asarray(x,dtype=float))) if x else 0
  cells.append(dict(root_seed=g['root']['seed'],color=g['color'],played_states=len(cp),PV_states=len(cv),played_rank=rank(cp),PV_rank=rank(cv),terminal=g['termination']['kind']))
 sv=np.linalg.svd(np.asarray(played+pv,dtype=float),compute_uv=False)
 rows.append(dict(task=task,arm=E['arm'],baseline_games=len(games),source_file=(folder/'games.jsonl').relative_to(R).as_posix(),source_sha256=hashlib.sha256((folder/'games.jsonl').read_bytes()).hexdigest(),source_lines=sorted(refs),query_calls=queries,played_states=len(played),PV_states=len(pv),played_rank=rank(played),PV_rank=rank(pv),combined_rank=rank(played+pv),combined_singular_values=sv.tolist(),played_presence={str(a):presence[a] for a in axes},PV_presence={str(a):pp[a] for a in axes},cells=cells))
out=dict(status='PASS_DERIVATION',rows=rows,axes=axes,new_go=0,seconds=time.perf_counter()-t0,scope='ALL declared unit-initial baseline cells selected by exact immutable update source references; signed board+hand linear feature rank of played and actually returned PV states ONLY, no full searched-frontier/parameter identifiability or human-price proof. Shared baseline records may occur across same-root objective arms; no independent replications claim.');dest=O/('result_'+('_'.join(map(str,tasks)))+'.json');assert not dest.exists();dest.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([{k:x[k] for k in ['task','baseline_games','query_calls','played_rank','PV_rank','combined_rank','PV_presence']} for x in rows]))
