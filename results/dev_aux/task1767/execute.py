import json,time,hashlib
from pathlib import Path
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_win_proof import prove_win,verify_certificate,PROVEN_WIN
from scripts.generic_win_proof_pn import prove_win_pn
p=Path('results/dev_aux/task1767');plan=json.loads((p/'plan.json').read_text());start=time.perf_counter();deadline=start+plan['total_seconds'];co=compile_krk();n=0;counts={}
with (p/'calls.jsonl').open('x') as log:
 for index,row in enumerate(plan['rows']):
  i=row['id'];s=krk_state(co,i//512,(i//32)%16,(i//2)%16,i%2)
  for cap in plan['caps']:
   algorithms=[('ANDOR',prove_win),('PN',prove_win_pn)]
   if index%2:algorithms.reverse()
   for name,fn in algorithms:
    if time.perf_counter()>=deadline:break
    r=fn(co,s,target=0,max_nodes=cap,seconds=plan['seconds'],max_depth=plan['max_depth'],cancel=lambda:time.perf_counter()>=deadline)
    v=verify_certificate(co,s,r.certificate,seconds=1.) if r.status==PROVEN_WIN else None
    if r.status==PROVEN_WIN:assert row['wdl']!=0 and v['verified'] and r.certificate.tree.rank>=row['rank']
    z=dict(id=i,library=row,algorithm=name,cap=cap,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,rank=r.certificate.tree.rank if r.certificate else None,verification=v,pushes=r.pushes,pops=r.pops)
    assert r.pushes==r.pops
    log.write(json.dumps(z)+'\n');log.flush();n+=1;key=str((name,cap,r.status));counts[key]=counts.get(key,0)+1
out=dict(status='COMPLETE' if n==len(plan['rows'])*4 else 'PARTIAL',calls=n,seconds=time.perf_counter()-start,counts=counts)
(p/'result.json').write_text(json.dumps(out,indent=2));print(out)
