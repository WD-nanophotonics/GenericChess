from pathlib import Path
from dataclasses import replace,asdict
from copy import copy
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2179.graph import prove_graph,verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2181')
def encode(cert):
 return dict(target=cert.target,nodes=[dict(rank=n.rank,terminal=None if n.terminal is None else dict(status=n.terminal.status.value,winner=n.terminal.winner),edges=[dict(action=action_to_dict(c.action),child=j)for c,j in n.edges])for n in cert.nodes])
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single900cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));assert hashlib.sha256(Path(p['input']).read_bytes()).hexdigest()==p['input_sha']
 for name,digest in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
 start=time.perf_counter();deadline=start+900;stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=900)),encoding='utf-8');roots=json.loads(Path(p['input']).read_text(encoding='utf-8'))['roots'];rows=[];status='COMPLETE'
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for root in roots:
   if cancel():status='PARTIAL_GLOBAL_CAP';break
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in root['root'][:-1]);c=replace(c,initial_position=replace(c.initial_position,board=board,side_to_move=0),initial_setup_positions={});s=GameSession(c);assert actor_state(s.state)==tuple(root['root']);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['root_state_sha']
   r=prove_graph(s,target=root['target'],max_nodes=p['max_positions'],max_edges=p['max_edges'],seconds=min(6.,max(0.,deadline-time.perf_counter())),max_depth=96,cancel=cancel)
   row=dict(family=root['family'],target=root['target'],status=r.status,reason=r.reason,positions=r.positions,expanded=r.expanded,transitions=r.transitions,seconds=r.seconds,rank=r.rank,verification=None,actual_mate=None)
   if r.certificate is not None:
    cf.write(json.dumps(dict(family=root['family'],root_record=json.loads(serialize_game_record(s.to_record())),certificate=encode(r.certificate)))+'\n');cf.flush()
    v=verify_graph(s,r.certificate,max_nodes=65536,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancel);row['verification']=v
    if v['verified']:
     assert root['label']!='DRAW' # independentcanonicalteacherposthoc crosscheck, neverpassedtosolver.
     try:
      cur=GraphStrategyCursor(s,r.certificate,max_nodes=65536,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancel);actual=copy(s);moves=0;began=time.perf_counter()
      while actual.result.status is SessionStatus.ONGOING:
       if cancel():raise TimeoutError('globalcap actualcursor')
       node=cur.certificate.nodes[cur.index];choice=cur.choose(actual)if actual.state.position.side_to_move==root['target']else max(node.edges,key=lambda e:cur.certificate.nodes[e[1]].rank)[0];cur.commit(actual,choice);moves+=1
      assert actual.result.winner==root['target'];row['actual_mate']=dict(status=actual.result.status.value,winner=actual.result.winner,moves=moves,seconds=time.perf_counter()-began,record=json.loads(serialize_game_record(actual.to_record())))
     except(ValueError,TimeoutError)as error:row['cursor_failure']=dict(type=type(error).__name__,message=str(error))
   rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush();print(json.dumps(dict(family=root['family'],queries=len(rows),verified=sum(bool(x['verification']and x['verification']['verified'])for x in rows),seconds=time.perf_counter()-start)),flush=True)
 out=dict(status=status,queries=len(rows),missing=62-len(rows),candidate_graphs=sum(r['verification']is not None for r in rows),verified=sum(bool(r['verification']and r['verification']['verified'])for r in rows),actual_mates=sum(r['actual_mate']is not None for r in rows),seconds=time.perf_counter()-start,scope=p['scope']);(OUT/'completion.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
