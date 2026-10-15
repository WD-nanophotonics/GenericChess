"""All defender children of one exposed late-win prefix, separate fixed budgets."""
from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import SessionStrategyCursor,replay_bound
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_rnb_bridge import uci
from scripts.generic_win_proof import CertificateVerificationError
OUT=Path('results/dev_aux/task1888')
def run():
 p=json.loads((OUT/'plan.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(p['root_record'])))
 actions={uci(a):a for a in s.legal_actions()};assert list(actions)==p['actions'];t=_load_transport();start=time.perf_counter();rows=[]
 def cancel():
  return time.perf_counter()-start>=p['seconds_cap']
 for name in p['actions']:
  t.stop_check(Path.cwd());assert not cancel();child=replay_bound(s);child.submit(actions[name]);before=child.to_record();root_state=repr(child.state)
  r=prove_session_win_batch_pn(child,target=p['target'],max_nodes=p['proof_nodes'],seconds=p['proof_seconds'],max_depth=p['max_depth'],cancel=cancel)
  row=dict(action=name,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,root_record=json.loads(serialize_game_record(before)),state_sha=hashlib.sha256(root_state.encode()).hexdigest())
  assert child.to_record()==before and repr(child.state)==root_state
  if r.certificate:
   try:
    cursor=SessionStrategyCursor(child,r.certificate,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'],cancel=cancel);row['verification']=cursor.receipt;row['rank']=cursor.node.rank
    while child.result.status is SessionStatus.ONGOING:
     assert not cancel();choice=cursor.choose(child) if child.state.position.side_to_move==p['target'] else cursor.node.edges[0][0];cursor.commit(child,choice)
    assert child.result.winner==p['target'];row['executed_record']=json.loads(serialize_game_record(child.to_record()));row['winner']=child.result.winner
   except CertificateVerificationError as e:row['verification']=e.receipt
  rows.append(row)
 out=dict(status='COMPLETE_ALL_DEFENDER_CHILDREN',rows=rows,seconds=time.perf_counter()-start,scope=p['scope'],new_native_go=0,new_learning_games=0)
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({**out,'rows':[{k:r[k] for k in ('action','status','reason','nodes','seconds')} for r in rows]}))
if __name__=='__main__':run()
