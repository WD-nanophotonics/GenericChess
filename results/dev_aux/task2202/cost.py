from pathlib import Path
from dataclasses import asdict
from copy import copy
import json,time,hashlib,datetime
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from results.dev_aux.task2179.graph import prove_graph,verify_graph,GraphStrategyCursor
from results.dev_aux.task2189.frontier import prove_frontier_graph
from results.dev_aux.task2187.trace import root_session
from results.dev_aux.task2181.run import encode as encode_graph
from results.dev_aux.task2048.portable_certificate import encode as encode_tree
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2202')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single300cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text());began=time.perf_counter();deadline=began+300;stop=EvidenceStopReader(Path.cwd());rows=[];status='COMPLETE';roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2177/inputs.json').read_text())['roots']}
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())),encoding='utf-8')
 def check():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for family in p['cases']:
   for wall in(p['walls']if family%2 else list(reversed(p['walls']))):
    for arm in(p['provers']if family%2 else list(reversed(p['provers']))):
     for style in(p['styles']if(family+p['provers'].index(arm))%2 else list(reversed(p['styles']))):
      if check():status='PARTIAL_GLOBAL_CAP';break
      s=root_session(roots[family]);readstart=stop.reads;qstart=time.perf_counter()
      # Per-poll realdeadline remains in _Budget for BOTHstyles. Outer checks
      # are actualfresh all-six-file reads, immediately surrounding each tinycall.
      callback=check if style=='CURRENT_INNER_FRESH'else lambda:time.perf_counter()>=deadline
      kw=dict(target=roots[family]['target'],max_nodes=8192,seconds=min(wall,deadline-time.perf_counter()),max_depth=96,cancel=callback)
      if arm=='PN':r=prove_session_win_batch_pn(s,**kw)
      else:r=(prove_graph if arm=='BFS'else prove_frontier_graph)(s,max_edges=65536,**kw)
      elapsed=time.perf_counter()-qstart;stop_after=check();nreads=stop.reads-readstart
      row={k:v for k,v in asdict(r).items()if k!='certificate'};row.update(query=len(rows),family=family,arm=arm,style=style,wall=wall,outer_query_seconds=elapsed,query_fresh_reads=nreads,atomic_overshoot_seconds=max(0.,elapsed-wall),verification=None,actual_mate=None)
      if stop_after:status='PARTIAL_GLOBAL_CAP'
      elif r.certificate is not None:
       cf.write(json.dumps(dict(query=len(rows),family=family,arm=arm,certificate=encode_tree(r.certificate.tree)if arm=='PN'else encode_graph(r.certificate)))+'\n');cf.flush()
       vr=(verify_session_certificate if arm=='PN'else verify_graph)(s,r.certificate,max_nodes=131072,seconds=min(3.,deadline-time.perf_counter()),cancel=check);row['verification']=vr
       if vr['verified']:
        cls=SessionStrategyCursor if arm=='PN'else GraphStrategyCursor
        try:
         cur=cls(s,r.certificate,max_nodes=131072,seconds=min(3.,deadline-time.perf_counter()),cancel=check);actual=copy(s);moves=0
         while actual.result.status is SessionStatus.ONGOING:
          if check():raise TimeoutError('globalcap')
          if actual.state.position.side_to_move==roots[family]['target']:choice=cur.choose(actual)
          elif arm=='PN':choice=max(cur.node.edges,key=lambda e:e[1].rank)[0]
          else:choice=max(cur.certificate.nodes[cur.index].edges,key=lambda e:cur.certificate.nodes[e[1]].rank)[0]
          cur.commit(actual,choice);moves+=1
         assert actual.result.winner==roots[family]['target'];row['actual_mate']=dict(moves=moves,winner=actual.result.winner,record=json.loads(serialize_game_record(actual.to_record())))
        except(ValueError,TimeoutError)as e:row['cursor_failure']=str(e)
      rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush()
      if status!='COMPLETE':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
   print(json.dumps(dict(family=family,queries=len(rows),seconds=time.perf_counter()-began)),flush=True)
 result=dict(status=status,queries=len(rows),missing=144-len(rows),seconds=time.perf_counter()-began,verified=sum(bool(x['verification']and x['verification']['verified'])for x in rows),actual_mates=sum(x['actual_mate']is not None for x in rows),scope=p['scope']);(OUT/'completion.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
