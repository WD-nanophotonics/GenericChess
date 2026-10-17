from pathlib import Path
from copy import copy
from dataclasses import fields
import json,time,datetime,hashlib,traceback,uuid
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import execute
from results.dev_aux.task2384.incremental import prove_incremental_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2424')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());slots=json.loads((OUT/'inputs.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter();deadline=start+p['cap_seconds'];rows=[];current=None;status='COMPLETE'
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_cap=p['cap_seconds'],source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())))
 def cancel():stop();return time.perf_counter()>=deadline
 try:
  with(OUT/'queries.jsonl').open('x')as qf,(OUT/'certificates.jsonl').open('x')as cf:
   for slot in slots:
    if cancel():status='PARTIAL_GLOBAL_CAP';break
    current=slot;row=dict(slot,queried=False,verified=False,actual_mate=False)
    if slot['record']is not None:
     c=compile_ruleset_for_execution(deserialize_ruleset(Path(slot['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(slot['record'])));assert s.result.status is SessionStatus.ONGOING and s.state.position.side_to_move==slot['role'];seconds=min(p['query_seconds'],max(0.,deadline-time.perf_counter()));r=prove_incremental_graph(s,target=slot['role'],max_nodes=p['query_positions'],max_edges=p['query_edges'],seconds=seconds,max_depth=p['depth'],cancel=cancel);row.update(queried=True,query_seconds_allocated=seconds,result={f.name:getattr(r,f.name)for f in fields(r)if f.name!='certificate'},actual_record=json.loads(serialize_game_record(s.to_record())),actual_status=s.result.status.value)
     if r.certificate is not None:
      cert=r.certificate;cf.write(json.dumps(dict(slot=slot['slot'],certificate=encode(cert)))+'\n');cf.flush();v=verify_graph(s,cert,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'],cancel=cancel);row['verification']=v
      if v['verified']:
       row['verified']=True;cur=GraphStrategyCursor(s,cert,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'],cancel=cancel);moves=0
       while s.result.status is SessionStatus.ONGOING and not cancel():
        before=copy(s);node=cert.nodes[cur.index];ch=cur.choose(s)if s.state.position.side_to_move==cert.target else max(node.edges,key=lambda e:cert.nodes[e[1]].rank)[0];execute(s,ch);cur.observe(before,ch,s);moves+=1
       row.update(actual_record=json.loads(serialize_game_record(s.to_record())),actual_status=s.result.status.value,actual_winner=s.result.winner,actual_conversion_moves=moves,actual_mate=s.result.status is not SessionStatus.ONGOING and s.result.winner==slot['role'])
    rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush();print(json.dumps(dict(slot=slot['slot'],family=slot['family'],role=slot['role'],stage=slot['stage'],queried=row['queried'],verified=row['verified'],actual_mate=row['actual_mate'])),flush=True);current=None
 except BaseException as error:
  event=uuid.uuid4().hex;private=Path('.local_agent/runtime-errors');private.mkdir(exist_ok=True);(private/(event+'.txt')).write_text(traceback.format_exc());(OUT/'failure.json').write_text(json.dumps(dict(error_type=type(error).__name__,message=str(error),private_event=event,pending_slot=current,completed_rows=len(rows),action='FAIL_CLOSED_NO_RETRY'),indent=2));(OUT/'completion.json').write_text(json.dumps(dict(status='INTERRUPTED_'+type(error).__name__,planned=32,rows=len(rows),unstarted=32-len(rows),original_cap=p['cap_seconds']),indent=2));raise
 completion=dict(status=status,planned=len(slots),rows=len(rows),unstarted=len(slots)-len(rows),queried=sum(r['queried']for r in rows),verified=sum(r['verified']for r in rows),actual_mates=sum(r['actual_mate']for r in rows),seconds=time.perf_counter()-start,original_cap=p['cap_seconds'],scope=p['scope']);(OUT/'completion.json').write_text(json.dumps(completion,indent=2));print(json.dumps(completion))
if __name__=='__main__':run()
