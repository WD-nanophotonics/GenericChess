"""Same full Position, real third repetition: stale WIN reuse must reject."""
from pathlib import Path
from dataclasses import replace
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2296")
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());pairs=json.loads(Path("results/dev_aux/task2292/frozen-pairs.json").read_text());source={r["context"]:r for r in json.loads(Path("results/dev_aux/task2291/certificates.json").read_text())};rows=[]
 for index,p in enumerate(pairs):
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(p["rules"]).read_text()));r=GameSession.replay(c,deserialize_game_record(json.dumps(p["source_record"])));s=GameSession.replay(c,deserialize_game_record(json.dumps(p["target_record"])));assert _same_state(r.state.position,s.state.position)and s.result.status is SessionStatus.ONGOING;prefix=len(r.to_record().actions);loop=s.to_record().actions[prefix:];assert len(loop)==4
  for a in loop:
   assert s.result.status is SessionStatus.ONGOING;s.submit(a)
  assert _same_state(r.state.position,s.state.position)and s.result.status is not SessionStatus.ONGOING and s.result.winner is None
  old=decode_graph(r,source[p["context"]]["certificate"]);candidate=replace(old,root_record=s.to_record(),root_state=s.state);v=verify_graph(s,candidate,max_nodes=65536,seconds=1.,cancel=stop);assert not v["verified"]and v["reason"]=="actual_session_terminal"
  try:GraphStrategyCursor(s,candidate,max_nodes=65536,seconds=1.,cancel=stop)
  except ValueError as error:cursor_rejection=str(error)
  else:raise AssertionError("terminalcursoradmitted")
  rows.append(dict(pair=index,context=p["context"],same_complete_position=True,actual_status=s.result.status.value,winner=s.result.winner,source_record=p["source_record"],second_occurrence_record=p["target_record"],third_occurrence_record=json.loads(serialize_game_record(s.to_record())),candidate_verification=v,cursor_rejection=cursor_rejection))
 (OUT/"rows.json").write_bytes(json.dumps(rows,indent=2).encode());result=dict(status="PASS_REAL_REPETITION_HISTORY_BOUNDARY_NOT_STATE_ONLY_WIN",pairs=len(rows),actual_draws=len(rows),same_full_position_cases=len(rows),rejected_stale_candidates=len(rows),additional_actual_public_moves=24,seconds=time.perf_counter()-start,scope="SAMEcompiled/fullPosition butdifferentcompleteactualGameRecord andrealterminalauthority. Firstloop ongoing+freshcandidateadmitted in2292; identicalsecondloop actualthirdrepetition DRAW, verifier/cursorreject. No manualcount/stateinjection, no fakefiles, no newrewardtraining/defaultbank/all-domainclaim.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
