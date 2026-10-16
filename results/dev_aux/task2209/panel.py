"""Frozen eight actual semantic roots; proof evidence, not game-value training."""
from pathlib import Path
from copy import copy
from dataclasses import asdict
import json,time,hashlib,datetime
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from results.dev_aux.task2199.semantic_graph import prove_graph,verify_graph,GraphStrategyCursor,scope_reason
from results.dev_aux.task2181.run import encode as graph_encode
from results.dev_aux.task2048.portable_certificate import encode as tree_encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2209')
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,v):
 with(OUT/n).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
def freeze():
 assert not(OUT/'plan.json').exists()
 roots=[]
 def add(name,rules,record):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text(encoding='utf-8')))
  s=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
  assert s.result.status is SessionStatus.ONGOING and scope_reason(c)is None
  roots.append(dict(index=len(roots),name=name,rules=rules,rules_sha=sha(Path(rules).read_bytes()),record=record,state_sha=sha(repr(s.state).encode()),target=s.state.position.side_to_move,legal_actions=len(s.legal_actions())))
 prefixes=json.loads(Path('results/dev_aux/task2194/prefixes.json').read_text())
 for ply in(0,2,5,6):add('lifecycle_ply'+str(ply),'results/dev_aux/task2194/rules.json',prefixes[ply]['record'])
 rules='results/dev_aux/task2200/mate-rules.json';c=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text()))
 for key in(None,'quiet_mate'):
  s=GameSession(c,initial_setup_key=key);add('S4_'+str(key),rules,json.loads(serialize_game_record(s.to_record())))
 branches=json.loads(Path('results/dev_aux/task2200/result.json').read_text())['trigger_branches']
 for label in('root','king_leaves'):
  r=next(r for r in branches if r['name']==label);add('trigger_'+label,'results/dev_aux/task2200/trigger-rules.json',r['record'])
 save('roots.json',roots)
 pins={p:sha(Path(p).read_bytes())for p in('results/dev_aux/task2208/panel.py','results/dev_aux/task2199/semantic_graph.py','scripts/generic_session_win_proof_batch_pn.py','scripts/generic_session_win_proof.py','results/dev_aux/task2153/stop_evidence.py')}
 save('plan.json',dict(question='Do full-history PN or full-Position graph prove executable wins beyond tiny mate fixtures under matched short proof and paid caller budgets?',selection='Eight mechanically selected existing roots: lifecycle plies0/2/5/6, both S4 setups, trigger root/king_leaves. Frozen before proof outcomes, all exposed development inputs, no labels used.',roots_sha=sha((OUT/'roots.json').read_bytes()),pins=pins,arms=['FULL_HISTORY_PN','SEMANTIC_GRAPH'],proof_seconds=.2,caller_seconds=1.,actual_path_seconds=2.,nodes=8192,edges=65536,depth=96,one_cap_seconds=120,expected_queries=16,scope='Compilation/shared fixture preparation reported separately. Caller clock starts before root replay and includes proof, verification, current cursor construction. Execution path separately capped and paid; not WDL reward, no price fit, teacher or default adoption. UNKNOWN distinct from draw.'))
 print(json.dumps(dict(status='FROZEN_NO_PROOF_QUERIES',roots=len(roots),legal=[r['legal_actions']for r in roots])))
def run():
 assert not(OUT/'started.json').exists()
 p=json.loads((OUT/'plan.json').read_text());assert p['roots_sha']==sha((OUT/'roots.json').read_bytes())
 for name,d in p['pins'].items():assert sha(Path(name).read_bytes())==d
 stop=EvidenceStopReader(Path.cwd());began=time.perf_counter();deadline=began+p['one_cap_seconds'];save('started.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=sha((OUT/'plan.json').read_bytes())))
 def global_cancel():stop();return time.perf_counter()>=deadline
 rows=[];status='COMPLETE'
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for root in json.loads((OUT/'roots.json').read_text()):
   if global_cancel():status='PARTIAL_GLOBAL_CAP';break
   prep=time.perf_counter();assert sha(Path(root['rules']).read_bytes())==root['rules_sha'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));record=deserialize_game_record(json.dumps(root['record']));prep=time.perf_counter()-prep
   arms=p['arms']if root['index']%2==0 else list(reversed(p['arms']))
   for arm in arms:
    start=time.perf_counter();end=min(deadline,start+root['proof_seconds']+p['caller_overhead_seconds']);nreads=stop.reads
    def cancel():return global_cancel()or time.perf_counter()>=end
    s=GameSession.replay(c,record);assert sha(repr(s.state).encode())==root['state_sha'];replay_seconds=time.perf_counter()-start
    args=dict(target=root['target'],max_nodes=p['nodes'],seconds=max(0.,min(root['proof_seconds'],end-time.perf_counter())),max_depth=p['depth'],cancel=cancel)
    r=prove_session_win_batch_pn(s,**args)if arm=='FULL_HISTORY_PN'else prove_graph(s,max_edges=p['edges'],**args)
    row={k:v for k,v in asdict(r).items()if k!='certificate'};row.update(query=len(rows),root=root['index'],proof_cap=root['proof_seconds'],name=root['name'],arm=arm,shared_compile_seconds=prep,root_replay_seconds=replay_seconds,verification=None,cursor_ready=False,actual_mate=None)
    cur=None
    if r.certificate is not None:
     cf.write(json.dumps(dict(query=len(rows),root=root['index'],arm=arm,certificate=tree_encode(r.certificate.tree)if arm=='FULL_HISTORY_PN'else graph_encode(r.certificate)))+'\n');cf.flush()
     verifier=verify_session_certificate if arm=='FULL_HISTORY_PN'else verify_graph
     row['verification']=verifier(s,r.certificate,max_nodes=131072,seconds=max(0.,end-time.perf_counter()),cancel=cancel)
     if row['verification']['verified']:
      try:
       cls=SessionStrategyCursor if arm=='FULL_HISTORY_PN'else GraphStrategyCursor
       cur=cls(s,r.certificate,max_nodes=131072,seconds=max(0.,end-time.perf_counter()),cancel=cancel)
       row['cursor_ready']=not cancel()
      except(ValueError,TimeoutError)as e:row['cursor_error']=str(e)
    row['caller_seconds']=time.perf_counter()-start;row['caller_fresh_reads']=stop.reads-nreads
    if cur is not None and row['cursor_ready']:
     played=copy(s);startpath=time.perf_counter();moves=0
     try:
      while played.result.status is SessionStatus.ONGOING:
       if global_cancel()or time.perf_counter()-startpath>=p['actual_path_seconds']:raise TimeoutError('actual_path_cap')
       if played.state.position.side_to_move==root['target']:choice=cur.choose(played)
       elif arm=='FULL_HISTORY_PN':choice=max(cur.node.edges,key=lambda e:e[1].rank)[0]
       else:choice=max(cur.certificate.nodes[cur.index].edges,key=lambda e:cur.certificate.nodes[e[1]].rank)[0]
       cur.commit(played,choice);moves+=1
      assert played.result.winner==root['target'];row['actual_mate']=dict(moves=moves,winner=played.result.winner,record=json.loads(serialize_game_record(played.to_record())))
     except(ValueError,TimeoutError)as e:row['actual_path_error']=str(e)
     row['actual_path_seconds']=time.perf_counter()-startpath
    rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush();print(json.dumps({k:row[k]for k in('query','name','arm','status','reason','caller_seconds','cursor_ready')}),flush=True)
 save('completion.json',dict(status=status,queries=len(rows),expected_queries=p['expected_queries'],missing=p['expected_queries']-len(rows),seconds=time.perf_counter()-began,verified=sum(bool(r['verification']and r['verification']['verified'])for r in rows),cursor_ready=sum(r['cursor_ready']for r in rows),actual_mates=sum(r['actual_mate']is not None for r in rows),fresh_stop_reads=stop.reads))
if __name__=='__main__':import sys;{'freeze':freeze,'run':run}[sys.argv[1]]()
