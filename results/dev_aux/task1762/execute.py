"""Generic proof coverage on the already frozen 8x8 diagnostic roots."""
import json,time,hashlib
from pathlib import Path
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_win_proof import prove_win,verify_certificate,PROVEN_WIN
p=Path('results/dev_aux/task1762');d=json.loads((p/'plan.json').read_text());start=time.perf_counter();deadline=start+d['total_seconds']
assert hashlib.sha256(Path('scripts/generic_win_proof.py').read_bytes()).hexdigest()==d['solver_sha256']
c=compile_krk(8);counts={};rows=[]
for f in d['families']:
 for color,raw in enumerate(f['roots']):
  if time.perf_counter()>=deadline:break
  s=krk_state(c,raw[:-1].index('K' if color==0 else 'k'),raw[:-1].index('k' if color==0 else 'K'),raw[:-1].index('R' if color==0 else 'r'),raw[-1],color)
  for cap in d['nodes']:
   r=prove_win(c,s,target=color,max_nodes=cap,seconds=d['seconds_per_call'],max_depth=d['max_depth'],cancel=lambda:time.perf_counter()>=deadline)
   v=verify_certificate(c,s,r.certificate,seconds=1.) if r.status==PROVEN_WIN else None
   assert v is None or v['verified']
   assert r.status!=PROVEN_WIN or r.certificate.tree.rank==f['DTM']
   row=dict(family_table_id=f['table_id'],DTM=f['DTM'],color=color,cap=cap,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,rank=r.certificate.tree.rank if r.certificate else None,verification=v)
   rows.append(row)
   with (p/'calls.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
   key=str((cap,f['DTM'],r.status));counts[key]=counts.get(key,0)+1
out=dict(status='COMPLETE' if len(rows)==256 else 'PARTIAL',calls=len(rows),seconds=time.perf_counter()-start,counts=counts)
(p/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='counts'})
