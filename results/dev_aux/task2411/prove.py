from pathlib import Path
from copy import copy
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import verify_session_certificate,execute
from results.dev_aux.task2384.incremental import prove_incremental_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2200.controls import unroll
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2411')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());cases=json.loads((OUT/'inputs.json').read_text());t=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd())
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_cap=p['cap_seconds'])));rows=[];certs=[]
 def cancel():stop();return time.perf_counter()-t>=p['cap_seconds']
 for case in cases:
  assert not cancel();c=compile_ruleset_for_execution(deserialize_ruleset(Path(case['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));result=prove_incremental_graph(s,max_nodes=p['query_nodes'],seconds=p['query_seconds'],max_depth=p['max_depth'],cancel=cancel);row=dict(case,proof_reason=result.reason,verified=False,work={name:getattr(result,name,None)for name in('positions','expanded','transitions','seconds')})
  if result.certificate is not None:
   cert=result.certificate;v=verify_graph(s,cert,max_nodes=4096,seconds=p['verification_seconds'],cancel=cancel);tree=verify_session_certificate(s,unroll(s,cert),max_nodes=4096,seconds=p['verification_seconds'],cancel=cancel);assert v['verified']and tree['verified'];cur=GraphStrategyCursor(s,cert,max_nodes=4096,seconds=3.,cancel=cancel);moves=0
   while s.result.status is SessionStatus.ONGOING:
    assert not cancel();node=cert.nodes[cur.index];ch=cur.choose(s)if s.state.position.side_to_move==cert.target else max(node.edges,key=lambda e:cert.nodes[e[1]].rank)[0];before=copy(s);execute(s,ch);cur.observe(before,ch,s);moves+=1
   assert s.result.winner==cert.target;row.update(verified=True,verification=v,fullhistory_tree=tree,actual_record=json.loads(serialize_game_record(s.to_record())),winner=s.result.winner,actual_mate_moves=moves);certs.append(dict(extra=case['extra'],certificate=encode(cert)))
  rows.append(row)
 (OUT/'certificates.json').write_text(json.dumps(certs,indent=2));(OUT/'result.json').write_text(json.dumps(dict(status='CLOSED_HAND_MULTIPLICITY_GATE_CONTROL',rows=rows,seconds=time.perf_counter()-t,scope=p['scope']),indent=2));print(json.dumps([dict(extra=r['extra'],total=r['total'],gate=r['gate_current'],verified=r['verified'],proof_reason=r['proof_reason'])for r in rows]))
if __name__=='__main__':run()
