from pathlib import Path
from collections import Counter,defaultdict
from copy import copy
from dataclasses import replace
from generic_chess.core.pieces import Piece
from scripts.generic_proof_rnb_bridge import actor_state
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof_threshold import prove_session_win_threshold
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from results.dev_aux.task2145.verify import verify_prefix_session_certificate,PrefixSessionStrategyCursor
from results.dev_aux.task2048.portable_certificate import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2177')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single1200cap NEVERrestart')
 p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
 for name,digest in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
 start=time.perf_counter();deadline=start+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd())
 def cancel():stop();return time.perf_counter()>=deadline
 (OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=p['one_cap_seconds'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())),encoding='utf-8')
 roots=json.loads(Path('results/dev_aux/task2177/inputs.json').read_text(encoding='utf-8'))['roots'];rows=[];status='COMPLETE';providers={'BATCH_PN':prove_session_win_batch_pn,'RETAINED_THRESHOLD':prove_session_win_threshold}
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for root in roots:
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in root['root'][:-1]);c=replace(c,initial_position=replace(c.initial_position,board=board,side_to_move=0),initial_setup_positions={});s=GameSession(c);assert actor_state(s.state)==tuple(root['root'])and hashlib.sha256(repr(s.state).encode()).hexdigest()==root['root_state_sha']
   for target in(root['target'],):
    off=(root['family']+target)%4;envelopes=p['envelopes'][off:]+p['envelopes'][:off]
    for envelope in envelopes:
     arms=p['provers']if(root['family']+target)%2==0 else list(reversed(p['provers']))
     for arm in arms:
      if cancel():status='PARTIAL_GLOBAL_CAP';break
      r=providers[arm](s,target=target,max_nodes=envelope['nodes'],seconds=envelope['seconds'],max_depth=96,cancel=cancel)
      row=dict(family=root['family'],target=target,arm=arm,envelope=envelope,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,frontiers=r.frontiers,transitions=r.transitions,iterations=r.iterations,peak_depth=r.peak_depth,eager_board_successors=r.eager_board_successors,claims_assessed=r.claims_assessed,recursive_calls=getattr(r,'recursive_calls',None),selections=getattr(r,'selections',None),reference_verification=None,prefix_verification=None,actual_mate=None)
      if r.certificate is not None:
       vr=verify_session_certificate(s,r.certificate,max_nodes=131072,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancel);vp=verify_prefix_session_certificate(s,r.certificate,max_nodes=131072,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancel)
       row.update(reference_verification=vr,prefix_verification=vp)
       cf.write(json.dumps(dict(query=len(rows),family=root['family'],target=target,arm=arm,envelope=envelope,rules=root['rules'],root_record=json.loads(serialize_game_record(s.to_record())),tree=encode(r.certificate.tree)))+'\n');cf.flush()
       if vr['verified']or vp['verified']:
        cls=SessionStrategyCursor if vr['verified']else PrefixSessionStrategyCursor
        try:
         cursor=cls(s,r.certificate,max_nodes=131072,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancel);actual=copy(s);moves=0
         while actual.result.status is SessionStatus.ONGOING:
          if cancel():raise TimeoutError('globalcap duringdiagnosticcursor')
          choice=cursor.choose(actual)if actual.state.position.side_to_move==target else max(cursor.node.edges,key=lambda e:e[1].rank)[0]
          cursor.commit(actual,choice);moves+=1
         assert actual.result.winner==target
         row['actual_mate']=dict(status=actual.result.status.value,winner=actual.result.winner,moves=moves,record=json.loads(serialize_game_record(actual.to_record())))
        except Exception as error:
         row['cursor_failure']=dict(type=type(error).__name__,message=str(error))
      rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush()
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   print(json.dumps(dict(family=root['family'],queries=len(rows),seconds=time.perf_counter()-start,proofs=sum(x['status']=='PROVEN_WIN'for x in rows))),flush=True)
   if status!='COMPLETE':break
 out=dict(status=status,queries=len(rows),expected_queries=p['expected_queries'],missing_queries=p['expected_queries']-len(rows),seconds=time.perf_counter()-start,proofs=sum(r['status']=='PROVEN_WIN'for r in rows),actual_mates=sum(r['actual_mate']is not None for r in rows),actual_stop_reads=stop.reads,scope=p['scope'])
 (OUT/'completion.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
