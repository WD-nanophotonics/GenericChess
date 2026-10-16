"""Bounded actual certificate probes on diagnosed all-positive-price tie errors."""
from pathlib import Path
from copy import copy
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor,execute
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_session_native_material import _load_transport
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
from results.dev_aux.task2072.no_win_filter import CompleteGraphNoWinFilter
from results.dev_aux.task2048.portable_certificate import encode
OUT=Path('results/dev_aux/task2121')
def run(teacher=None):
 if (OUT/'started.json').exists():raise RuntimeError('one frozen probe only')
 start=time.perf_counter();deadline=start+180;plan=json.loads((OUT/'plan.json').read_text());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');load=time.perf_counter();teacher=teacher or CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-load;rank=RankCertificateProvider(teacher);stop=_load_transport().stop_check
 def cancelled():stop(Path.cwd());return time.perf_counter()>=deadline
 roots=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];cases=[]
 for family in(12,30,11):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[family]['rules']).read_text(encoding='utf-8')));s=GameSession(c)
  if family==11:cases.append((family,'ROOT_OWN_POSITIVE_CONTROL',s,0))
  else:
   for a in sorted(s.legal_actions(),key=uci):child=copy(s);child.submit(a);cases.append((family,uci(a),child,1))
 (OUT/'cases-before-proofs.json').write_text(json.dumps([dict(family=f,action=a,target=t,full_record=json.loads(serialize_game_record(s.to_record())))for f,a,s,t in cases],indent=2),encoding='utf-8');rows=[];paths=[];certificates=[]
 for i,(family,action,s,target)in enumerate(cases):
  label=teacher.rows[teacher.key(actor_state(s.state))];v={'WIN':1,'DRAW':0,'LOSS':-1}[label['label']];v=v if s.state.position.side_to_move==target else-v
  for name,provider in([('PN',prove_session_win_batch_pn),('RANK',rank)]if i%2==0 else[('RANK',rank),('PN',prove_session_win_batch_pn)]):
   if cancelled():break
   r=provider(s,target=target,max_nodes=1024,seconds=1.5,max_depth=64,cancel=cancelled);row=dict(family=family,action=action,target=target,positional_value_for_target=v,provider=name,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,verified=None,cursor_terminal=None)
   if r.status=='PROVEN_WIN':
    vr=verify_session_certificate(s,r.certificate,max_nodes=65536,seconds=2.,cancel=cancelled);assert vr['verified'];cursor=SessionStrategyCursor(s,r.certificate,max_nodes=65536,seconds=2.,cancel=cancelled);current=copy(s);steps=[]
    while current.result.status is SessionStatus.ONGOING:
     if cancelled():raise RuntimeError('probe cap during strategy')
     selected=cursor.choose(current)if current.state.position.side_to_move==target else max(cursor.node.edges,key=lambda e:e[1].rank)[0];cursor.commit(current,selected);steps.append(uci(selected.action))
    assert current.result.winner==target;certificates.append(dict(family=family,action=action,provider=name,target=target,rules=roots[family]['rules'],root_record=json.loads(serialize_game_record(s.to_record())),tree=encode(r.certificate.tree)));row.update(verified=vr,cursor_verification=cursor.receipt,cursor_terminal=dict(status=current.result.status.value,winner=current.result.winner,moves=len(steps)));paths.append(dict(family=family,action=action,provider=name,target=target,full_record=json.loads(serialize_game_record(current.to_record())),moves=steps))
   rows.append(row)
 result=dict(status='COMPLETE'if len(rows)==len(cases)*2 else'CAP_PARTIAL',cases=len(cases),queries=len(rows),proofs={n:sum(r['provider']==n and r['status']=='PROVEN_WIN'for r in rows)for n in('PN','RANK')},verified_actual_mates=len(paths),teacher_load_seconds=load,seconds=time.perf_counter()-start,scope=plan['scope'])
 (OUT/'certificates.json').write_text(json.dumps(certificates,indent=2),encoding='utf-8');(OUT/'queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'actual-paths.json').write_text(json.dumps(paths,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
