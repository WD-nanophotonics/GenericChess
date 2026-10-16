"""Independent complete real-history reuse and terminal-boundary consumer."""
from pathlib import Path
from copy import copy
from dataclasses import replace
import json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2298")
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());pairs=read("results/dev_aux/task2292/frozen-pairs.json");receipts=read("results/dev_aux/task2292/receipts.json");convs={r["pair"]:r for r in read("results/dev_aux/task2292/conversions.json")};terminal=read("results/dev_aux/task2296/rows.json");sources={r["context"]:r for r in read("results/dev_aux/task2291/certificates.json")};played=0;cycles=0
 for i,(pair,receipt,tt)in enumerate(zip(pairs,receipts,terminal)):
  stop();assert i==receipt["pair"]==tt["pair"]and pair["context"]==receipt["context"]==tt["context"];c=compile_ruleset_for_execution(deserialize_ruleset(Path(pair["rules"]).read_text()));root=GameSession.replay(c,deserialize_game_record(json.dumps(pair["source_record"])));s=GameSession.replay(c,deserialize_game_record(json.dumps(pair["target_record"])));assert _same_state(root.state.position,s.state.position)and s.state.ply_count==root.state.ply_count+4;assert root.to_record()!=s.to_record()and s.result.status is SessionStatus.ONGOING
  cert=decode_graph(root,sources[pair["context"]]["certificate"]);old=verify_graph(s,cert,max_nodes=65536,seconds=2.,cancel=stop);assert not old["verified"]and old["reason"]=="root_binding_mismatch";fresh=replace(cert,root_record=s.to_record(),root_state=s.state);v=verify_graph(s,fresh,max_nodes=65536,seconds=2.,cancel=stop);assert v["verified"]and receipt["candidate_verification"]["verified"];cur=GraphStrategyCursor(s,fresh,max_nodes=65536,seconds=2.,cancel=stop);final=deserialize_game_record(json.dumps(convs[i]["record"]));assert final.actions[:len(s.to_record().actions)]==s.to_record().actions
  for a in final.actions[len(s.to_record().actions):]:
   before=copy(s);choice=SessionChoice("ACTION",action=a)
   if s.state.position.side_to_move==cert.target:assert cur.choose(s)==choice
   execute(s,choice);cur.observe(before,choice,s);played+=1
  assert s.result.status is not SessionStatus.ONGOING and s.result.winner==cert.target
  middle=GameSession.replay(c,deserialize_game_record(json.dumps(tt["second_occurrence_record"])));last=GameSession.replay(c,deserialize_game_record(json.dumps(tt["third_occurrence_record"])));assert _same_state(root.state.position,middle.state.position)and _same_state(root.state.position,last.state.position);assert middle.result.status is SessionStatus.ONGOING and last.result.status is not SessionStatus.ONGOING and last.result.winner is None;assert len(last.to_record().actions)==len(middle.to_record().actions)+4;cycles+=8
  reject=verify_graph(last,replace(cert,root_record=last.to_record(),root_state=last.state),max_nodes=65536,seconds=2.,cancel=stop);assert not reject["verified"]and reject["reason"]=="actual_session_terminal"
 assert len(pairs)==len(receipts)==len(terminal)==len(convs)==6
 result=dict(status="PASS_CLOSED_REAL_HISTORY_REUSE_AND_THIRD_REPETITION",actual_prefix_pairs=6,source_binding_rejections=6,current_history_admissions=6,actual_conversion_moves=played,actual_cycle_moves_replayed=cycles,actual_terminal_draw_rejections=6,seconds=time.perf_counter()-start,scope="Actualpublicrecordreplay/samefullPosition/samecompiledrules/currentverify+cursor/strictactualpaths; no manualhistoryinjection or originalproducer rerun. Sixpairsare3sourcecontexts with2chosenloops each, not6independentgames/naturalcachehit or newpriceevidence.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
