"""Instrument real stable solved PN nodes; no mocked proof or game."""
from pathlib import Path
import hashlib,json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionWinCertificate,SessionProofNode,verify_session_certificate
from scripts.generic_session_native_material import _load_transport
import scripts.generic_session_win_proof_batch_pn as pn
OUT=Path('results/dev_aux/task1886')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert hashlib.sha256(Path(p['source']).read_bytes()).hexdigest()==p['source_sha'];source=json.loads(Path(p['source']).read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()));t=_load_transport();start=time.perf_counter();rows=[]
 base=pn._Node
 for ply in p['plies']:
  t.stop_check(Path.cwd());assert time.perf_counter()-start<p['seconds_cap'];record=next(r['root_record'] for r in source['rows'] if r['ply']==ply);s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));captured=[];seen=set();all_count=0
  class ObservedNode(base):
   def __setattr__(self,name,value):
    nonlocal all_count
    super().__setattr__(name,value)
    if name=='pn' and value==0 and getattr(self,'edges',None) and self.depth in p['retention_depths'] and self.session.state.position.side_to_move==p['target'] and id(self) not in seen:
     seen.add(id(self));all_count+=1
     if len(captured)<p['max_retained']:captured.append(self)
  pn._Node=ObservedNode
  try:r=pn.prove_session_win_batch_pn(s,target=p['target'],max_nodes=p['proof_nodes'],seconds=p['proof_seconds'],max_depth=p['max_depth'],cancel=lambda:time.perf_counter()-start>=p['seconds_cap'])
  finally:pn._Node=base
  export_start=time.perf_counter();exports=[]
  def tree(node):
   assert time.perf_counter()-start<p['seconds_cap'] and node.pn==0
   if node.terminal is not None:return SessionProofNode(0,terminal=node.terminal)
   edges=node.edges if node.session.state.position.side_to_move!=p['target'] else [next((choice,child) for choice,child in node.edges if child.pn==0)]
   branches=tuple((choice,tree(child)) for choice,child in edges)
   return SessionProofNode(1+max(child.rank for _,child in branches),branches)
  for node in captured:
   t.stop_check(Path.cwd());current=GameSession.replay(c,node.session.to_record());assert repr(current.state)==repr(node.session.state) and current.result==node.session.result
   cert=SessionWinCertificate(c.ruleset_fingerprint,node.session.to_record(),node.session.state,p['target'],tree(node))
   v=verify_session_certificate(current,cert,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'],cancel=lambda:time.perf_counter()-start>=p['seconds_cap'])
   exports.append(dict(relative_ply=node.depth,root_record=json.loads(serialize_game_record(current.to_record())),state_sha=hashlib.sha256(repr(current.state).encode()).hexdigest(),rank=cert.tree.rank,verification=v))
  rows.append(dict(ply=ply,root_status=r.status,root_reason=r.reason,nodes=r.nodes,proof_seconds=r.seconds,solved_qualifying_nodes=all_count,captured=len(captured),exports=exports,export_and_verification_seconds=time.perf_counter()-export_start))
 out=dict(status='COMPLETE_REAL_PROOF_NODE_OBSERVATION',rows=rows,seconds=time.perf_counter()-start,scope=p['scope'],new_native_go=0,new_learning_games=0)
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({**out,'rows':[{k:v for k,v in row.items() if k!='exports'} for row in rows]}))
if __name__=='__main__':run()
