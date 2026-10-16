from pathlib import Path
from dataclasses import asdict
from copy import copy
import json,time,hashlib,datetime
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from results.dev_aux.task2187.trace import root_session
from results.dev_aux.task2179.graph import prove_graph,verify_graph,GraphStrategyCursor
from results.dev_aux.task2189.frontier import prove_frontier_graph
from results.dev_aux.task2203.incremental import prove_incremental_graph
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2204')

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single900cap NEVERrestart')
 if not Path('results/dev_aux/task2190/completion.json').exists():raise RuntimeError('Existinglongproducer mustclose first; nosecondlongwriter')
 p=json.loads((OUT/'plan.json').read_text());
 for name,digest in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
 began=time.perf_counter();deadline=began+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd());rows=[];status='COMPLETE'
 (OUT/'started.json').write_text(json.dumps(dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())),encoding='utf-8')
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for root in json.loads(Path(p['input']).read_text())['roots']:
   envelopes=p['envelopes'];offset=root['family']%len(envelopes);envelopes=envelopes[offset:]+envelopes[:offset]
   for n,e in enumerate(envelopes):
    arms=p['arms']if(root['family']+n)%2==0 else list(reversed(p['arms']))
    for arm in arms:
     if cancel():status='PARTIAL_GLOBAL_CAP';break
     s=root_session(root);nreads=stop.reads;start=time.perf_counter()
     r=(prove_frontier_graph if arm=='WHOLE_GRAPH_FRONTIER'else prove_incremental_graph)(s,target=root['target'],max_nodes=e['nodes'],max_edges=e['edges'],seconds=min(e['seconds'],deadline-time.perf_counter()),max_depth=p['depth'],cancel=cancel)
     row={k:v for k,v in asdict(r).items()if k!='certificate'};row.update(query=len(rows),family=root['family'],target=root['target'],arm=arm,envelope=e,outer_seconds=time.perf_counter()-start,stop_reads_query=stop.reads-nreads,verification=None,actual_mate=None)
     if r.certificate is not None:
      cf.write(json.dumps(dict(query=len(rows),family=root['family'],arm=arm,root_record=json.loads(serialize_game_record(s.to_record())),certificate=encode(r.certificate)))+'\n');cf.flush()
      vr=verify_graph(s,r.certificate,max_nodes=131072,seconds=min(p['verification_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel);row['verification']=vr
      if vr['verified']:
       try:
        cur=GraphStrategyCursor(s,r.certificate,max_nodes=131072,seconds=min(p['cursor_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel);actual=copy(s);moves=0;start=time.perf_counter()
        while actual.result.status is SessionStatus.ONGOING:
         if cancel():raise TimeoutError('globalcap actualcursor')
         choice=cur.choose(actual)if actual.state.position.side_to_move==root['target']else max(cur.certificate.nodes[cur.index].edges,key=lambda e:cur.certificate.nodes[e[1]].rank)[0]
         cur.commit(actual,choice);moves+=1
        assert actual.result.winner==root['target'];row['actual_mate']=dict(winner=actual.result.winner,moves=moves,seconds=time.perf_counter()-start,record=json.loads(serialize_game_record(actual.to_record())))
       except(ValueError,TimeoutError)as error:row['cursor_failure']=dict(type=type(error).__name__,message=str(error))
     rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush()
    if status!='COMPLETE':break
   print(json.dumps(dict(family=root['family'],queries=len(rows),verified=sum(bool(x['verification']and x['verification']['verified'])for x in rows),seconds=time.perf_counter()-began)),flush=True)
   if status!='COMPLETE':break
 result=dict(status=status,queries=len(rows),expected_queries=p['expected_queries'],missing=p['expected_queries']-len(rows),seconds=time.perf_counter()-began,verified=sum(bool(r['verification']and r['verification']['verified'])for r in rows),actual_mates=sum(r['actual_mate']is not None for r in rows),actual_stop_reads=stop.reads)
 (OUT/'completion.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
