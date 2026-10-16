from pathlib import Path
from functools import lru_cache
from copy import copy
import json,time,hashlib
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_win_proof import SessionProofNode,SessionWinCertificate,verify_session_certificate
from scripts.generic_win_proof import _Interrupted
from results.dev_aux.task2179.graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2180.rank_proposal import propose
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2182.audit import root_session
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2183')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single300cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
 for name,digest in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
 start=time.perf_counter();deadline=start+300;stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=300)),encoding='utf-8');load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2171','results/dev_aux/task2172','results/dev_aux/task2176');load=time.perf_counter()-load;roots=json.loads(Path(p['inputs']).read_text(encoding='utf-8'))['roots'];rows=[];status='COMPLETE'
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for root in roots:
   if cancel():status='PARTIAL_GLOBAL_CAP';break
   row=dict(family=root['family'],label=root['label'],construction_seconds=None,positions=None,unrolled_nodes=None,queries=[],actual_mate=None)
   if root['label']=='DRAW':row['status']='TABLE_NONWIN_CONTROL_NO_PROPOSAL'
   else:
    s=root_session(root);began=time.perf_counter()
    try:cert=propose(s,teacher,root['target'],max_nodes=8192,seconds=min(3.,max(0.,deadline-time.perf_counter())),cancel=cancel)
    except(_Interrupted,ValueError)as error:row['status']='PROPOSAL_UNKNOWN';row['proposal_failure']=str(error);cert=None
    row['construction_seconds']=time.perf_counter()-began
    if cert is not None:
     row['status']='PROPOSAL_COMPLETE';row['positions']=len(cert.nodes)
     @lru_cache(None)
     def size(i):return 1+sum(size(j)for _,j in cert.nodes[i].edges)
     total=size(0);row['unrolled_nodes']=total;cf.write(json.dumps(dict(family=root['family'],root_record=json.loads(serialize_game_record(s.to_record())),certificate=encode(cert)))+'\n');cf.flush()
     tree=None
     if total<=16384:
      @lru_cache(None)
      def unroll(i):return SessionProofNode(cert.nodes[i].rank,tuple((c,unroll(j))for c,j in cert.nodes[i].edges),cert.nodes[i].terminal)
      tree=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,root['target'],unroll(0))
     verified=False
     for seconds in p['verification_seconds']:
      for arm in(['DAG','FULL_HISTORY_TREE']if root['family']%2 else['FULL_HISTORY_TREE','DAG']):
       if cancel():status='PARTIAL_GLOBAL_CAP';break
       if arm=='FULL_HISTORY_TREE'and tree is None:r=dict(verified=False,reason='NOT_RUN_UNROLLED_NODES_EXCEED_FIXED16384',nodes=0,seconds=0.,mathematical_required_nodes=total)
       else:
        kwargs=dict(max_nodes=16384,seconds=min(seconds,max(0.,deadline-time.perf_counter())),cancel=cancel)
        r=verify_graph(s,cert,**kwargs)if arm=='DAG'else verify_session_certificate(s,tree,**kwargs)
        if arm=='DAG'and r['verified']:verified=True
       row['queries'].append(dict(arm=arm,seconds_cap=seconds,receipt=r))
      if status!='COMPLETE':break
     if verified and not cancel():
      began=time.perf_counter()
      try:
       cursor=GraphStrategyCursor(s,cert,max_nodes=16384,seconds=min(1.5,max(0.,deadline-time.perf_counter())),cancel=cancel);cursor_admission=time.perf_counter()-began;actual=copy(s);moves=0;beginmoves=time.perf_counter()
       while actual.result.status is SessionStatus.ONGOING:
        if cancel():raise TimeoutError('global300cap')
        node=cert.nodes[cursor.index];choice=cursor.choose(actual)if actual.state.position.side_to_move==cert.target else max(node.edges,key=lambda e:cert.nodes[e[1]].rank)[0];cursor.commit(actual,choice);moves+=1
       assert actual.result.winner==cert.target;row['actual_mate']=dict(moves=moves,winner=actual.result.winner,status=actual.result.status.value,cursor_admission_seconds=cursor_admission,execution_seconds=time.perf_counter()-beginmoves,record=json.loads(serialize_game_record(actual.to_record())))
      except(ValueError,TimeoutError)as error:row['cursor_failure']=str(error)
   rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush()
   if root['family']%8==7:print(json.dumps(dict(cases=len(rows),seconds=time.perf_counter()-start)),flush=True)
 groups={}
 for arm in('DAG','FULL_HISTORY_TREE'):
  for sec in(.2,1.5):
   rr=[q['receipt']for r in rows for q in r['queries']if q['arm']==arm and q['seconds_cap']==sec];groups[arm+'/'+str(sec)]=dict(queries=len(rr),verified=sum(r['verified']for r in rr),notrun_nodeceil=sum(r['reason'].startswith('NOT_RUN')for r in rr),nodes=sum(r['nodes']for r in rr),actual_seconds=sum(r['seconds']for r in rr))
 out=dict(status=status,cases=len(rows),positive_proposals=sum(r['status']=='PROPOSAL_COMPLETE'for r in rows),controls=sum(r['label']=='DRAW'for r in rows),actual_mates=sum(r['actual_mate']is not None for r in rows),teacher_load_seconds=load,seconds=time.perf_counter()-start,groups=groups,scope=p['scope']);(OUT/'completion.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
