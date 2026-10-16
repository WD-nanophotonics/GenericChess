"""Bounded complete predeclared root/target/budget proof-coverage diagnostic."""
from pathlib import Path
import json,time,hashlib,datetime
from collections import Counter
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_native_material import _load_transport
from results.dev_aux.task2048.portable_certificate import encode
OUT=Path('results/dev_aux/task2052')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
 p=read(OUT/'plan.json');assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['files'].items());assert Path('results/dev_aux/task2050/campaign-completion.json').exists()
 start=time.perf_counter();rows=[];samples=set();status='COMPLETE';t=_load_transport();c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text(encoding='utf-8')));roots=read(p['roots'])['roots'];planned=[(f,target,n)for f in p['families']for target in p['targets']for n in p['PN_nodes']];assert len(planned)==p['expected_calls']
 (OUT/'start.json').write_text(json.dumps(dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),one_clock=True,cap_seconds=600,restart_forbidden=True)),encoding='utf-8')
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as output:
  for ordinal,(family,target,n)in enumerate(planned):
   if time.perf_counter()-start>=p['seconds_cap']:status='GLOBAL_CAP';break
   t.stop_check(Path.cwd());session=GameSession(c,roots[family]['setup']);before=session.to_record();r=prove_session_win_batch_pn(session,target=target,max_nodes=n,seconds=p['proof_seconds'],max_depth=p['proof_depth'],cancel=lambda:time.perf_counter()-start>=p['seconds_cap']);v=None
   if r.certificate is not None:v=verify_session_certificate(session,r.certificate,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'],cancel=lambda:time.perf_counter()-start>=p['seconds_cap'])
   assert session.to_record()==before
   label='PROVED_WIN'if v is not None and v['verified']else'UNKNOWN';sample=None
   if label=='PROVED_WIN'and n not in samples:
    samples.add(n);sample=f'certificate-{n}.json';(OUT/sample).write_text(json.dumps(dict(family=family,budget=n,target=target,ruleset_fingerprint=c.ruleset_fingerprint,root_record=json.loads(serialize_game_record(before)),tree=encode(r.certificate.tree)),indent=2),encoding='utf-8')
   row=dict(ordinal=ordinal,family=family,phase=roots[family]['phase'],target=target,budget=n,label=label,solver_status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,rank=None if r.certificate is None else r.certificate.tree.rank,verification=v,certificate_sample=sample);rows.append(row);output.write(json.dumps(row)+'\n');output.flush()
   if len(rows)%24==0:print(json.dumps(dict(done=len(rows),seconds=time.perf_counter()-start)),flush=True)
 summary={str(n):dict(calls=sum(r['budget']==n for r in rows),proved=sum(r['budget']==n and r['label']=='PROVED_WIN'for r in rows),nodes=sum(r['nodes']for r in rows if r['budget']==n),seconds=sum(r['seconds']for r in rows if r['budget']==n),reasons=dict(Counter(r['reason']for r in rows if r['budget']==n)))for n in p['PN_nodes']}
 for f in p['families']:assert len({r['target']for r in rows if r['family']==f and r['label']=='PROVED_WIN'})<=1
 result=dict(status=status,queries=len(rows),planned=p['expected_calls'],unrun=[dict(family=f,target=t,budget=n)for f,t,n in planned[len(rows):]],summary=summary,verified_winning_families=sorted({r['family']for r in rows if r['label']=='PROVED_WIN'}),seconds=time.perf_counter()-start,original_cap=600,new_Native_calls=0,new_reward_games=0,scope=p['scope'],inference=p['decision'])
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
