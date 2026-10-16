"""Independent saved-entry/paid-query/certificate/history consumer."""
from pathlib import Path
from collections import Counter
from copy import copy
import json,time,hashlib
from fractions import Fraction as F
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2295")
def run():
 begin=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());data=read("results/dev_aux/task2284/inputs.json");source=Path(data["source"]);assert hashlib.sha256(source.read_bytes()).hexdigest()==data["source_sha"];games=[json.loads(x)for x in source.read_text().splitlines()];roots={r["index"]:r for r in read("results/dev_aux/task2266/inputs.json")};seen={};count=0
 def cancel():stop();return time.perf_counter()-begin>=240
 for game,row in zip(games,data["rows"]):
  if cancel():raise TimeoutError("consumer_cap")
  assert all(row[k]==game[k]for k in("slot","root","arm","ratio","candidate_color"));root=roots[game["root"]];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root["rules"]).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root["record"])));final=deserialize_game_record(json.dumps(game["record"]));prefix=s.to_record().actions;assert final.actions[:len(prefix)]==prefix;first=None
  for relative in range(len(final.actions)-len(prefix)+1):
   actors=sum(pc is not None for pc in s.state.position.board)+sum(n for h in s.state.position.hands for _,n in h.counts)
   if actors<=4:first=relative;break
   if relative<len(final.actions)-len(prefix):s.submit(final.actions[len(prefix)+relative]);count+=1
  if first is None:assert row["entry"]is None
  else:
   e=row["entry"];assert e["record"]==json.loads(serialize_game_record(s.to_record()))and e["state_sha"]==hashlib.sha256(repr(s.state).encode()).hexdigest()and e["actors"]==actors and e["relative_ply"]==first and e["status"]==s.result.status.value
   if s.result.status is SessionStatus.ONGOING:
    key=hashlib.sha256(json.dumps(dict(rules=c.ruleset_fingerprint,record=e["record"]),sort_keys=True).encode()).hexdigest();seen.setdefault(key,len(seen));assert row["context"]==seen[key]
   else:assert "context"not in row
 assert len(games)==len(data["rows"])==64 and len(seen)==len(data["contexts"])==7
 p=read("results/dev_aux/task2285/plan.json");inputs=read("results/dev_aux/task2285/inputs.json");queries=[json.loads(x)for x in Path("results/dev_aux/task2285/queries.jsonl").read_text().splitlines()];done=read("results/dev_aux/task2285/result.json");assert len(queries)==done["queries"]==p["expected_queries"]==42;assert hashlib.sha256(Path("results/dev_aux/task2285/inputs.json").read_bytes()).hexdigest()==p["inputs_sha"];by={}
 for i,r in enumerate(inputs):
  caps=p["caller_seconds"];caps=caps[i%3:]+caps[:i%3]
  for j,cap in enumerate(caps):
   q=queries[3*i+j];assert q["entry"]==i and q["index"]==3*i+j and q["caller_seconds"]==cap and q["method"]==r["method"]and q["context"]==r["context"]and q["known_WIN_for"]is None and q["label_known_before_query"]is False
   root=data["contexts"][r["context"]];assert root["root_record"]==r["root_record"];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r["rules"]).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r["root_record"])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==r["root_state_sha"];legal=[choice_value(SessionChoice("ACTION",action=a))for a in s.legal_actions()];assert q["choice"]is None or q["choice"]in legal
   assert q["graph_positions"]<=65536 and q["graph_transitions"]<=524288 and q["normal_visits"]<=512;cost=["admission_seconds","fallback_admission_seconds","proof_seconds","verification_seconds","normal_seconds"];assert all(q[x]>=0 for x in cost)and sum(q[x]for x in cost)<=q["reported_seconds"]+.001;by[(r["method"],cap)]=by.get((r["method"],cap),0)+q["verified"]
 assert not any(q["verified"]for q in queries);assert Path("results/dev_aux/task2285/certificates.jsonl").read_bytes()==b"";assert read("results/dev_aux/task2285/conversions.json")==[]
 qualification=[json.loads(x)for x in Path("results/dev_aux/task2286/queries.jsonl").read_text().splitlines()];assert len(qualification)==320;groups={}
 for q in qualification:
  assert q["completed_depth"]==3;groups[(q["family"],q["seed"],q["ratio"])]=q
 for family,seed,_ in groups:
  for a,b in[(1.5,1.75),(2.5,3.)]:assert all(groups[(family,seed,a)][k]==groups[(family,seed,b)][k]for k in("choice","nodes","transitions","completed_depth"))
 proofrows=read("results/dev_aux/task2291/certificates.json");convs={r["context"]:r for r in read("results/dev_aux/task2291/conversions.json")};moves=0
 for row in proofrows:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(row["rules"]).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row["root_record"])));cert=decode_graph(s,row["certificate"]);assert verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)["verified"];cursor=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);actions=deserialize_game_record(json.dumps(convs[row["context"]]["record"])).actions[len(s.to_record().actions):]
  for a in actions:
   before=copy(s);choice=SessionChoice("ACTION",action=a)
   if s.state.position.side_to_move==cert.target:assert cursor.choose(s)==choice
   execute(s,choice);cursor.observe(before,choice,s);moves+=1
  assert s.result.status is not SessionStatus.ONGOING and s.result.winner==cert.target
 result=dict(status="PASS_CLOSED_NATURAL_ENTRY_QUERY_AND_REFERENCE_QUALIFICATION",source_games=64,firstentry_replayed_prefix_moves=count,ongoing_occurrences=54,unique_contexts=7,paid_queries=42,verified_moverWIN=0,frequency_weighted_verified_occurrences=0,ordinary_qualification_queries=320,reference_assisted_nonmoverWIN=len(proofrows),reference_conversion_moves=moves,seconds=time.perf_counter()-begin,scope="IndependentpublicSessionreplay/sequence/rootdedup/returnedlegality/separatework/paidcost and actualpositivegraph+currentcursor. CanonicalDRAWnotactualdraw,3nonmoverWINs explanatory notdiscoveredby2285. No frozenproducer/fit/newrewardgame; no54independentcontexts or pricebenefitfromcoverage.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
