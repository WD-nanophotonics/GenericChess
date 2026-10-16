from pathlib import Path
from copy import copy
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_rnb_bridge import uci
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2048.portable_certificate import encode
from results.dev_aux.task2131.stop_reader import ParsedStopReader
OUT=Path('results/dev_aux/task2133')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('one180cap neverrestart')
 start=time.perf_counter();deadline=start+180;p=json.loads((OUT/'plan.json').read_text());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');legacy=_load_transport().stop_check;root=Path.cwd();load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-load;rank=RankCertificateProvider(teacher);inputs=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];lookup={r['family']:r for r in(json.loads(x)for x in Path('results/dev_aux/task2126/queries-corrected.jsonl').read_text().splitlines())if r['kind']=='INITIAL'and r['depth']==2};normal=[];rows=[];certs=[]
 def callback(arm):
  reader=ParsedStopReader(root)if arm=='PARSED_BYTES_CACHE'else lambda:legacy(root)
  def cancelled():reader();return time.perf_counter()>=deadline
  return cancelled
 for family in p['roots']:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[family]['rules']).read_text(encoding='utf-8')));s=GameSession(c);q=lookup[family]['child_values']
  for arm in p['arms']:
   r=ProofMaterialPlayer(c,evaluate(1.),proof_enabled=False,max_depth=3).choose(s.state,max_nodes=4096,seconds=.1,cancel=callback(arm));normal.append(dict(family=family,arm=arm,choice=None if r.action is None else uci(r.action),depth=r.completed_depth,nodes=r.nodes,seconds=r.seconds,child_position_WDL=None if r.action is None else q[uci(r.action)]))
  if family==11:cases=[('ROOT_OWN_WIN',s,0)]
  else:
   rr=lookup[family]['regions'];names=rr[0]['top_actions'];assert all(x['top_actions']==names for x in rr);legal={uci(a):a for a in s.legal_actions()};cases=[]
   for name in names:child=copy(s);child.submit(legal[name]);cases.append((name,child,1))
  for index,(name,child,target)in enumerate(cases):
   for prover,fn in [('PN',prove_session_win_batch_pn),('RANK',rank)]:
    for arm in(p['arms']if index%2==0 else list(reversed(p['arms']))):
     cancel=callback(arm);r=fn(child,target=target,max_nodes=1024,seconds=1.5,max_depth=64,cancel=cancel);row=dict(family=family,action=name,target=target,provider=prover,arm=arm,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,verified=None,actual_terminal=None)
     if r.status=='PROVEN_WIN':
      vr=verify_session_certificate(child,r.certificate,max_nodes=65536,seconds=2.,cancel=cancel);assert vr['verified'];cursor=SessionStrategyCursor(child,r.certificate,max_nodes=65536,seconds=2.,cancel=cancel);current=copy(child);moves=0
      while current.result.status is SessionStatus.ONGOING:
       if cancel():raise TimeoutError('original180cap')
       choice=cursor.choose(current)if current.state.position.side_to_move==target else max(cursor.node.edges,key=lambda e:e[1].rank)[0];cursor.commit(current,choice);moves+=1
      assert current.result.winner==target;row.update(verified=vr,cursor_verification=cursor.receipt,actual_terminal=dict(status=current.result.status.value,winner=current.result.winner,moves=moves));certs.append(dict(family=family,action=name,provider=prover,arm=arm,target=target,rules=inputs[family]['rules'],root_record=json.loads(serialize_game_record(child.to_record())),tree=encode(r.certificate.tree),actual_record=json.loads(serialize_game_record(current.to_record()))))
     rows.append(row)
     if time.perf_counter()>=deadline:raise TimeoutError('original180cap')
 # Fixedfirstnonrejectedtie simulation uses ONLY independentlyverifiedwins.
 selectors=[]
 for family in(12,30):
  ties=lookup[family]['regions'][0]['top_actions']
  for prover in p['provers']:
   for arm in p['arms']:
    rr=[r for r in rows if r['family']==family and r['provider']==prover and r['arm']==arm];rejected={r['action']for r in rr if r['verified']and r['verified']['verified']};remaining=[a for a in ties if a not in rejected];selected=remaining[0]if remaining else ties[0];selectors.append(dict(family=family,provider=prover,arm=arm,original=ties[0],rejected=[a for a in ties if a in rejected],selected=selected,all_rejected_normal_fallback=not remaining,posthoc_child_positional_WDL=lookup[family]['child_values'][selected],UNKNOWN_not_safe=True))
 result=dict(status='COMPLETE_DIAGNOSED_ROOT_CONTROLLER_QUALIFICATION',normal_queries=len(normal),proof_queries=len(rows),proof_counts={a+'_'+n:sum(r['arm']==a and r['provider']==n and r['status']=='PROVEN_WIN'for r in rows)for a in p['arms']for n in p['provers']},verified_actual_mates=len(certs),teacher_load_seconds=load,seconds=time.perf_counter()-start,normal=normal,tie_selectors=selectors,scope=p['scope'])
 (OUT/'queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'certificates.json').write_text(json.dumps(certs,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
