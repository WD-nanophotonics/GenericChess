"""All55 nonpositive entries: classify, verify actual opponentWIN, no draw fill."""
from pathlib import Path
from copy import copy
from collections import Counter
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2220.study import Guide,key
from results.dev_aux.task2246.entry_proofs import build
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2264')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(plan=p)));guide=Guide();rows=[json.loads(x)for x in Path('results/dev_aux/task2246/queries.jsonl').read_text().splitlines()if json.loads(x)['status']=='NO_POSITIVE_CANDIDATE_FOR_ACTOR'];assert len(rows)==55;roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2228/inputs.json').read_text())['roots']};queries=[];conversions=[]
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 with(OUT/'queries.jsonl').open('x')as qf,(OUT/'certificates.jsonl').open('x')as cf:
  for r in rows:
   if cancel():raise TimeoutError('original_all55_cap')
   root=roots[r['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==r['root_state_sha'];l=guide.rows[key(actor_state(s.state))];winner=s.state.position.side_to_move if l['label']=='WIN'else 1-s.state.position.side_to_move if l['label']=='LOSS'else None;assert winner==r['canonical_candidate_winner'];q=dict(slot=r['slot'],family=r['family'],ratio=r['ratio'],candidate_color=r['candidate_color'],actual_saved_outcome=r['actual_outcome'],canonical_candidate_winner=winner,status='CANONICAL_DRAW_ACTUAL_UNPROVEN',actual_opponent_WIN=False)
   if winner is not None:
    assert winner==1-r['candidate_color'];cert,work=build(s,guide,winner,p,cancel);v=verify_graph(s,cert,max_nodes=p['verify_nodes'],seconds=p['verify_seconds'],cancel=cancel);q.update(builder=work,verification=v,status='UNKNOWN_ACTUAL_HISTORY'if not v['verified']else'VERIFIED_ACTUAL_OPPONENT_WIN',actual_opponent_WIN=v['verified'])
    cf.write(json.dumps(dict(slot=r['slot'],certificate=encode(cert)))+'\n');cf.flush()
    if v['verified']:
     cursor=GraphStrategyCursor(s,cert,max_nodes=p['verify_nodes'],seconds=p['cursor_seconds'],cancel=cancel);moves=0
     while s.result.status is SessionStatus.ONGOING:
      if cancel():raise TimeoutError('original_all55_cap')
      before=copy(s)
      if s.state.position.side_to_move==winner:choice=cursor.choose(s)
      else:choice=SessionChoice('ACTION',action=sorted(s.legal_actions(),key=uci)[0])
      execute(s,choice);cursor.observe(before,choice,s);moves+=1
     assert s.result.winner==winner;conversions.append(dict(slot=r['slot'],winner=winner,moves=moves,record=json.loads(serialize_game_record(s.to_record()))));q['actual_cursor_converted']=True
   queries.append(q);qf.write(json.dumps(q)+'\n');qf.flush()
 (OUT/'conversions.json').write_text(json.dumps(conversions,separators=(',',':')));result=dict(status='COMPLETE_ALL55_NONPOSITIVE_ENTRY_AUDIT',rows=len(queries),statuses=dict(Counter(q['status']for q in queries)),conversions=len(conversions),conversion_moves=sum(q['moves']for q in conversions),profiles={str(r):dict(statuses=dict(Counter(q['status']for q in queries if q['ratio']==r)),saved_outcomes=dict(Counter(q['actual_saved_outcome']for q in queries if q['ratio']==r)),verified_opponent_entry_saved_outcomes=dict(Counter(q['actual_saved_outcome']for q in queries if q['ratio']==r and q['actual_opponent_WIN'])))for r in(1.,2.)},seconds=time.perf_counter()-start,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
