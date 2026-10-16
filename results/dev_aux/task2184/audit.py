from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import json,time
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2182.audit import root_session,graph_decode
from results.dev_aux.task2179.graph import verify_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2184')
def audit(cancel=None):
 start=time.perf_counter();deadline=start+180;stop=EvidenceStopReader(Path.cwd())if cancel is None else None
 def check():
  if stop:stop()
  if time.perf_counter()>=deadline or(cancel is not None and cancel()):raise TimeoutError('180savedconsumer')
 roots=json.loads(Path('results/dev_aux/task2177/inputs.json').read_text(encoding='utf-8'))['roots'];folder=Path('results/dev_aux/task2183');rows=list(map(json.loads,(folder/'queries.jsonl').read_text(encoding='utf-8').splitlines()));certs={r['family']:r for r in map(json.loads,(folder/'certificates.jsonl').read_text(encoding='utf-8').splitlines())};actor=RoyalActor(4);verified=mates=moves=forgeries=0
 for i,row in enumerate(rows):
  check();assert row['family']==i;root=roots[i]
  if root['label']=='DRAW':assert row['status']=='TABLE_NONWIN_CONTROL_NO_PROPOSAL'and i not in certs;continue
  raw=certs[i];s=root_session(root);assert _same_state(s.to_record(),deserialize_game_record(json.dumps(raw['root_record'])));cert=graph_decode(raw['certificate'],s);receipt=verify_graph(s,cert,max_nodes=16384,seconds=4.);assert receipt['verified']and receipt['nodes']==len(cert.nodes)==row['positions'];verified+=1
  @lru_cache(None)
  def size(j):return 1+sum(size(k)for _,k in cert.nodes[j].edges)
  assert size(0)==row['unrolled_nodes']==receipt['unrolled_tree_nodes']
  for q in row['queries']:
   if q['receipt']['verified']:assert q['receipt']['nodes']==(len(cert.nodes)if q['arm']=='DAG'else size(0))
  assert not verify_graph(s,replace(cert,target=1-cert.target),max_nodes=16384,seconds=4.)['verified'];forgeries+=1
  actual=row['actual_mate'];assert actual is not None;rec=deserialize_game_record(json.dumps(actual['record']))
  for a in rec.actions:
   legal={uci(x):x for x in s.legal_actions()};literal=dict(actor.moves(actor_state(s.state)));assert set(legal)==set(literal)and uci(a)in legal;s.submit(a);assert actor_state(s.state)==literal[uci(a)];moves+=1
  assert s.result.winner==root['target']==actual['winner']and s.result.status is not SessionStatus.ONGOING and len(rec.actions)==actual['moves'];replay=GameSession.replay(s.compiled,rec);assert _same_state(replay.state,s.state)and replay.result==s.result;mates+=1
 # Compare fixed completed generic panels, with explicit nonnested discovery.
 pn=list(map(json.loads,Path('results/dev_aux/task2177/queries.jsonl').read_text(encoding='utf-8').splitlines()));gr=list(map(json.loads,Path('results/dev_aux/task2181/queries.jsonl').read_text(encoding='utf-8').splitlines()));a={r['family']for r in pn if r['envelope']==dict(nodes=8192,seconds=6.)and r['status']=='PROVEN_WIN'};b={r['family']for r in gr if r['verification']and r['verification']['verified']}
 result=dict(status='PASS_ALL58_STORED_GRAPHS_UNROLLED_COUNTS_TARGET_FORGERIES_AND_ACTUAL_MATES',cases=len(rows),verified_graphs=verified,actual_mates=mates,actual_moves=moves,rejected_target_forgeries=forgeries,PN_6s8192_contexts=sorted(a),graph_6s8192_contexts=sorted(b),both=sorted(a&b),PN_only=sorted(a-b),graph_only=sorted(b-a),seconds=time.perf_counter()-start,new_search_or_fitness_or_teacher_expansion=0,scope='No producer orqueryrerun; oldexecutedsource/currentterminalrootfix separatelypinned. Tableproposal representationcomparison notno-tablealgorithmgain; all62contexts retained with4explicitnonWINcontrols.');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':audit()
