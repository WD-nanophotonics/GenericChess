"""Actual saved-history qualification of opt-in positive DFS; no new game reward."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import execute
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2267.positive_dfs import prove_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2269')
def run():
 assert not(OUT/'result.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2258/inputs.json').read_text())['roots']};conversions=json.loads(Path('results/dev_aux/task2260/actual_conversions.json').read_text());results=[];certs=[]
 def cancel():stop();return time.perf_counter()-start>=120
 for r in conversions[:4]:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[r['family']]['rules']).read_text(encoding='utf-8')));s=GameSession(c);record=deserialize_game_record(json.dumps(r['record']));assert len(record.actions)>=2
  for a in record.actions[:-1]:s.submit(a)
  original=s.to_record();state=s.state;outcome=s.result;assert s.result.status is SessionStatus.ONGOING and s.state.position.side_to_move==r['winner']
  proof=prove_graph(s,max_nodes=2048,max_edges=16384,seconds=1.,max_depth=3,cancel=cancel);assert proof.status=='CANDIDATE_WIN_GRAPH'and proof.certificate is not None;cert=proof.certificate;v=verify_graph(s,cert,max_nodes=8192,seconds=2.,cancel=cancel);assert v['verified']and cert.nodes[0].rank==1;cursor=GraphStrategyCursor(s,cert,max_nodes=8192,seconds=2.,cancel=cancel);played=copy(s);execute(played,cursor.choose(played));assert played.result.winner==r['winner']and played.result.status is not SessionStatus.ONGOING
  wrong=replace(cert,root_record=GameSession(c).to_record());rejected=verify_graph(s,wrong,max_nodes=8192,seconds=2.,cancel=cancel);assert not rejected['verified']and rejected['reason']=='root_binding_mismatch'
  zero=prove_graph(s,max_nodes=2048,seconds=1.,max_depth=0,cancel=cancel);assert zero.status=='UNKNOWN'and zero.certificate is None
  empty=prove_graph(s,max_nodes=0,seconds=1.,max_depth=3,cancel=cancel);assert empty.status=='UNKNOWN'and empty.certificate is None and empty.positions==0
  pulse=prove_graph(s,max_nodes=2048,seconds=1.,max_depth=3,cancel=lambda:True);assert pulse.status=='UNKNOWN'and pulse.certificate is None and pulse.reason=='cancelled'
  assert _same_state(s.to_record(),original)and _same_state(s.state,state)and s.result==outcome
  results.append(dict(family=r['family'],root_plies=len(original.actions),verified=v,actual_oneply_mate=True,wrongroot_rejected=rejected['reason'],zero_depth=zero.reason,zero_nodes=empty.reason,cancelled=pulse.reason,producer_visits=proof.expanded,producer_positions=proof.positions));certs.append(dict(family=r['family'],root_record=json.loads(serialize_game_record(original)),certificate=encode(cert)))
 (OUT/'certificates.json').write_text(json.dumps(certs,separators=(',',':')));result=dict(status='PASS_4_ACTUAL_HISTORY_MATES_AND_16_BOUNDARY_CONTROLS',cases=results,seconds=time.perf_counter()-start,scope='FOURfirstsavedconversionpreterminalcontexts, actualfullrecords independentverification/execution, wrongroot/depth0/node0/cancel controls. Exposedsmallqualification, notall-domain/equivalence/completeness orspeedup proof. No tableinDFS, no default/learning/adoption. Existingfullsemanticguard/verifier retained.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
