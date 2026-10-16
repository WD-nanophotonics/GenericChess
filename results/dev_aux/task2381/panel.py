from pathlib import Path
from dataclasses import fields
from copy import copy
import json,time,hashlib,datetime,traceback,uuid
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2379.reader import FreshFileIOStopReader
from results.dev_aux.task2273.incremental_adapted import prove_incremental_graph as baseline
from results.dev_aux.task2382.incremental import prove_incremental_graph as bounded
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
OUT=Path('results/dev_aux/task2381')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 p=OUT/n;assert not p.exists();tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2),encoding='utf-8');tmp.replace(p)
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists();contexts=json.loads((OUT/'contexts.json').read_text());assert sha(OUT/'contexts.json')==p['contexts_sha']
 for name,h in p['pins'].items():assert sha(name)==h
 safety=EvidenceStopReader(Path.cwd());safety();start=time.perf_counter();deadline=start+p['one_cap_seconds'];save('started.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=sha(OUT/'plan.json')));rows=[];status='COMPLETE'
 def authority():safety();return time.perf_counter()>=deadline
 try:
  with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
   for ctx in contexts:
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(ctx['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(ctx['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==ctx['state_sha']
    for mode in p['modes']:
     for arm in(p['arms']if ctx['context']%2==0 else list(reversed(p['arms']))):
      if authority():status='PARTIAL_GLOBAL_CAP';break
      reader=(EvidenceStopReader if arm=='BASE'else FreshFileIOStopReader)(Path.cwd());calls=0;gap=0.;last=None
      def cancel():
       nonlocal calls,gap,last
       now=time.perf_counter()
       if last is not None:gap=max(gap,now-last)
       last=now;calls+=1;reader();return time.perf_counter()>=deadline
      kwargs=dict(target=ctx['target'],max_nodes=512 if mode=='FIXED_POSITIONS512'else 65536,max_edges=524288,seconds=min(60. if mode=='FIXED_POSITIONS512'else 8.4,max(0.,deadline-time.perf_counter())),max_depth=96,cancel=cancel);tick=time.perf_counter();r=(bounded if arm=='SELECTOR16'else baseline)(s,**kwargs);wall=time.perf_counter()-tick;authority();row={f.name:getattr(r,f.name)for f in fields(r)if f.name!='certificate'};row.update(query=len(rows),context=ctx['context'],mode=mode,arm=arm,requested_seconds=kwargs['seconds'],requested_positions=kwargs['max_nodes'],measured_seconds=wall,cancel_calls=calls,reader_reads=reader.reads,reader_bytes=reader.bytes_read,max_cancel_start_gap_seconds=gap,verification=None,actual_mate=None,certificate_sha=None)
      if r.certificate is not None:
       raw=encode(r.certificate);row['certificate_sha']=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest();cf.write(json.dumps(dict(query=len(rows),context=ctx['context'],certificate=raw))+'\n');cf.flush();v=verify_graph(s,r.certificate,max_nodes=131072,seconds=min(5.,max(0.,deadline-time.perf_counter())),cancel=authority);row['verification']=v
       if v['verified']:
        cur=GraphStrategyCursor(s,r.certificate,max_nodes=131072,seconds=min(5.,max(0.,deadline-time.perf_counter())),cancel=authority);actual=copy(s);moves=0
        while actual.result.status is SessionStatus.ONGOING:
         if authority():raise TimeoutError('globalcapcursor')
         node=cur.certificate.nodes[cur.index];ch=cur.choose(actual)if actual.state.position.side_to_move==ctx['target']else max(node.edges,key=lambda e:cur.certificate.nodes[e[1]].rank)[0];cur.commit(actual,ch);moves+=1
        assert actual.result.winner==ctx['target'];row['actual_mate']=dict(moves=moves,status=actual.result.status.value,winner=actual.result.winner,record=json.loads(serialize_game_record(actual.to_record())))
      rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush()
      if time.perf_counter()>=deadline:status='PARTIAL_GLOBAL_CAP';break
     if status!='COMPLETE':break
    print(json.dumps(dict(context=ctx['context'],queries=len(rows),seconds=time.perf_counter()-start)),flush=True)
    if status!='COMPLETE':break
  save('completion.json',dict(status=status,queries=len(rows),expected_queries=len(contexts)*len(p['modes'])*len(p['arms']),missing=len(contexts)*len(p['modes'])*len(p['arms'])-len(rows),seconds=time.perf_counter()-start,scope=p['scope']))
 except BaseException as e:
  priv=Path('.local_agent/runtime-errors');priv.mkdir(exist_ok=True);event=uuid.uuid4().hex;(priv/(event+'.txt')).write_text(traceback.format_exc(),encoding='utf-8');save('failure.json',dict(error_type=type(e).__name__,private_event=event,action='FAIL_CLOSED_NO_RETRY'));save('completion.json',dict(status='INTERRUPTED_'+type(e).__name__,queries=len(rows),expected_queries=len(contexts)*len(p['modes'])*len(p['arms']),missing=len(contexts)*len(p['modes'])*len(p['arms'])-len(rows),seconds=time.perf_counter()-start));raise
 print(json.dumps(json.loads((OUT/'completion.json').read_text())))
if __name__=='__main__':run()
