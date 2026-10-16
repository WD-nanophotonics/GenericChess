"""ALL24 already-qualified WIN entries: generic discovery at matched paid caps.
No table construction/import in discovery. Positive-only conditional capability.
"""
from pathlib import Path
from dataclasses import fields
from copy import copy
from collections import Counter
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_win_proof import SessionChoice,choices,execute
from scripts.generic_win_proof import _Budget
from results.dev_aux.task2210.player import PaidGraphPhasePlayer
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2181.run import encode as encode_graph
from results.dev_aux.task2048.portable_certificate import encode as encode_tree
from results.dev_aux.task2175.receipt import choice_value
OUT=Path('results/dev_aux/task2265')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(plan_sha=sha(OUT/'plan.json'))));rows=json.loads((OUT/'inputs.json').read_text());queries=[];conversions=[];status='COMPLETE'
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 with(OUT/'queries.jsonl').open('x')as qf,(OUT/'certificates.jsonl').open('x')as cf:
  for ri,r in enumerate(rows):
   caps=p['caller_seconds'];caps=caps[ri%3:]+caps[:ri%3]
   for cap in caps:
    if cancel():status='PARTIAL_GLOBAL_CAP';break
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==r['root_state_sha'];target=s.state.position.side_to_move
    player=PaidGraphPhasePlayer(c,lambda pos,t:0.,limits=PhaseLimits(proof_nodes=8192,proof_seconds=cap*.70,verification_nodes=32768,verification_seconds=cap*.25,normal_seconds=cap*.05),max_depth=1,proof_depth=96,graph_positions=8192,graph_edges=65536)
    before=time.perf_counter();d=player.choose(s,max_nodes=512,seconds=cap,cancel=cancel);wall=time.perf_counter()-before;query=dict(index=len(queries),entry=ri,slot=r['slot'],family=r['family'],known_WIN_for=r['candidate_color'],side_to_move=target,caller_seconds=cap,source=d.source,exit_cause=d.exit_cause,proof_reason=d.proof_reason,measured_seconds=wall,reported_seconds=d.seconds,admission_seconds=d.admission_seconds,fallback_admission_seconds=d.fallback_admission_seconds,proof_seconds=d.proof_seconds,verification_seconds=d.verification_seconds,normal_seconds=d.normal_seconds,raw_proofs=d.raw_proofs,verification_receipts=d.verification_receipts,phase_limits=d.phase_limits,graph_positions=d.graph_positions,graph_expanded=d.graph_expanded,graph_transitions=d.graph_transitions,graph_verifier_visits=d.graph_verifier_visits,tree_visits=d.proof_nodes,tree_verifier_visits=d.tree_verifier_visits,normal_visits=d.search_nodes,choice=choice_value(d.choice),verified=d.source in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'))
    # Prover targets actual mover. Some saved knownWIN entries are opponent-to-move.
    # Preserve these strata rather than silently flipping/injecting turns.
    if query['verified']:
     assert target==r['candidate_color'];cur=player.cursor;kind=player.cursor_kind;cert=cur.certificate;cf.write(json.dumps(dict(query=query['index'],kind=kind,certificate=encode_graph(cert)if kind=='GRAPH'else encode_tree(cert.tree)))+'\n');cf.flush();move_count=0;conversion_start=time.perf_counter()
     while s.result.status is SessionStatus.ONGOING:
      if cancel()or time.perf_counter()-conversion_start>5:raise TimeoutError('postquery_cursor_conversion_cap')
      before_s=copy(s)
      if s.state.position.side_to_move==target:choice=cur.choose(s)
      else:choice=next(choices(s,_Budget(512,1.,cancel)))
      execute(s,choice);cur.observe(before_s,choice,s);move_count+=1
     assert s.result.winner==target;conversions.append(dict(query=query['index'],moves=move_count,seconds=time.perf_counter()-conversion_start,record=json.loads(serialize_game_record(s.to_record()))))
    queries.append(query);qf.write(json.dumps(query)+'\n');qf.flush()
   if status!='COMPLETE':break
   print(json.dumps(dict(entries=ri+1,queries=len(queries),verified=sum(q['verified']for q in queries),seconds=time.perf_counter()-start)),flush=True)
 (OUT/'conversions.json').write_text(json.dumps(conversions,separators=(',',':')));result=dict(status=status,entries=len(rows),queries=len(queries),expected_queries=72,missing=72-len(queries),seconds=time.perf_counter()-start,by_cap={str(cap):dict(queries=sum(q['caller_seconds']==cap for q in queries),verified=sum(q['caller_seconds']==cap and q['verified']for q in queries),mover_knownWIN=sum(q['caller_seconds']==cap and q['side_to_move']==q['known_WIN_for']for q in queries),sources=dict(Counter(q['source']for q in queries if q['caller_seconds']==cap)))for cap in p['caller_seconds']},postquery_conversions=len(conversions),scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
