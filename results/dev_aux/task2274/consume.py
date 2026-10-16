"""Closed query/certificate/real-cursor consumer; no proof producer rerun."""
from pathlib import Path
from collections import defaultdict
from copy import copy
import json,time,hashlib,sys
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,SessionWinCertificate,SessionStrategyCursor,verify_session_certificate,execute
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2048.portable_certificate import decode as decode_tree
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2274')
def run(task):
 start=time.perf_counter(); stop=EvidenceStopReader(Path.cwd()); folder=Path(f'results/dev_aux/task{task}')
 read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
 plan=read(folder/'plan.json'); done=read(folder/'result.json'); inputs=read(folder/'inputs.json')
 queries=[json.loads(x) for x in (folder/'queries.jsonl').read_text().splitlines()]
 certs={r['query']:r for r in map(json.loads,(folder/'certificates.jsonl').read_text().splitlines())}
 conversions={r['query']:r for r in read(folder/'conversions.json')}
 assert hashlib.sha256((folder/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha']
 assert len(queries)==done['queries']; expected=[]
 for ri,r in enumerate(inputs):
  caps=plan['caller_seconds']; caps=caps[ri%3:]+caps[:ri%3]
  expected.extend((ri,cap) for cap in caps)
 assert len(expected)==plan['expected_queries'] and len(queries)<=len(expected)
 rollup=defaultdict(list); steps=0; overshoot=[]
 def cancel():
  stop(); return time.perf_counter()-start>=180
 for qi,(q,(ri,cap)) in enumerate(zip(queries,expected)):
  if cancel():raise TimeoutError('consumer_cap')
  assert q['index']==qi and q['entry']==ri and q['caller_seconds']==cap
  r=inputs[ri]; c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')))
  s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])))
  assert hashlib.sha256(repr(s.state).encode()).hexdigest()==r['root_state_sha'] and q['side_to_move']==s.state.position.side_to_move
  legal={json.dumps(choice_value(SessionChoice('ACTION',action=a)),sort_keys=True) for a in s.legal_actions()}
  assert q['choice'] is None or json.dumps(q['choice'],sort_keys=True) in legal
  assert q['normal_visits']<=512 and q['graph_positions']<=(65536 if task==2273 else 8192)
  assert q['graph_transitions']<=(524288 if task==2273 else 65536)
  cost=['admission_seconds','fallback_admission_seconds','proof_seconds','verification_seconds','normal_seconds']
  assert all(q[k]>=0 for k in cost+['measured_seconds','reported_seconds'])
  assert sum(q[k] for k in cost)<=q['reported_seconds']+.001
  method=q.get('method','BFS'); assert method==r.get('method','BFS'); rollup[(method,cap)].append(q)
  overshoot.append(max(0.,q['measured_seconds']-cap))
  if q['verified']:
   assert q['source'] in ('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY') and qi in certs and qi in conversions
   assert q['side_to_move']==q['known_WIN_for']
   receipts=q['verification_receipts']
   assert any(v[1]=='INDEPENDENT' and v[2]['verified'] for v in receipts)
   assert any(v[1]=='CURRENT_CURSOR' and v[2]['verified'] for v in receipts)
   saved=certs[qi]; kind=saved['kind']
   if kind=='GRAPH':
    cert=decode_graph(s,saved['certificate']); v=verify_graph(s,cert,max_nodes=131072,seconds=5.,cancel=cancel)
    assert v['verified']; cursor=GraphStrategyCursor(s,cert,max_nodes=131072,seconds=5.,cancel=cancel)
   else:
    cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,q['side_to_move'],decode_tree(saved['certificate'],c.ruleset_fingerprint))
    v=verify_session_certificate(s,cert,max_nodes=131072,seconds=5.,cancel=cancel); assert v['verified']
    cursor=SessionStrategyCursor(s,cert,max_nodes=131072,seconds=5.,cancel=cancel)
   final=deserialize_game_record(json.dumps(conversions[qi]['record'])); prefix=s.to_record().actions
   assert final.actions[:len(prefix)]==prefix
   for a in final.actions[len(prefix):]:
    before=copy(s); choice=SessionChoice('ACTION',action=a)
    if s.state.position.side_to_move==q['side_to_move']:assert cursor.choose(s)==choice
    execute(s,choice); cursor.observe(before,choice,s); steps+=1
   assert s.result.status is not SessionStatus.ONGOING and s.result.winner==q['side_to_move']
   assert json.loads(serialize_game_record(s.to_record()))==conversions[qi]['record']
  else:assert qi not in certs and qi not in conversions
 assert len(certs)==len(conversions)==sum(q['verified'] for q in queries)
 result=dict(status='PASS_CLOSED_PAID_QUERY_CERTIFICATE_CURSOR',task=task,queries=len(queries),planned=len(expected),missing=len(expected)-len(queries),verified_instances=len(certs),actual_conversion_moves=steps,maximum_measured_atomic_overrun=max(overshoot,default=0),by_method_cap=[dict(method=m,caller_seconds=cap,queries=len(rr),mover_knownWIN=sum(q['side_to_move']==q['known_WIN_for'] for q in rr),verified=sum(q['verified'] for q in rr),measured_seconds=sum(q['measured_seconds'] for q in rr)) for (m,cap),rr in sorted(rollup.items())],seconds=time.perf_counter()-start,scope='Closed actualroot/returnedlegality/separateunits/phasecost/paidindependent+currentcursor receipts andsavedactualconversion replay. No proofproducer/fit/newrewardgames. UNKNOWNnotDRAW; moverstrata andactualatomicovershoot explicit; no exactlatency/nodeequivalenceclaim.')
 with (OUT/f'task{task}-audit.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='by_method_cap'}))
if __name__=='__main__':run(int(sys.argv[1]))
