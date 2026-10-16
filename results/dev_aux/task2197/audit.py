from pathlib import Path
from dataclasses import asdict
import json,time,hashlib,datetime
from results.dev_aux.task2187.trace import root_session
from results.dev_aux.task2179.graph import prove_graph
from results.dev_aux.task2191.semantic_graph import prove_graph as core_graph
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2197')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single180cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text());
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');rows=[];pairs=0;status='COMPLETE'
 def cancel():stop();return time.perf_counter()-began>=180
 for root in json.loads(Path(p['inputs']).read_text())['roots']:
  pair=[]
  for name,f in([('SESSION_CANONICAL',prove_graph),('CORE_CANONICAL',core_graph)]if root['family']%2==0 else[('CORE_CANONICAL',core_graph),('SESSION_CANONICAL',prove_graph)]):
   if cancel():status='PARTIAL_GLOBAL_CAP';break
   s=root_session(root);start=time.perf_counter();r=f(s,target=root['target'],max_nodes=64,max_edges=512,seconds=1.,max_depth=96,cancel=cancel,_clock=lambda:0.)
   value={k:v for k,v in asdict(r).items()if k!='certificate'};value['certificate']=None if r.certificate is None else encode(r.certificate)
   rows.append(dict(family=root['family'],arm=name,outer_seconds=time.perf_counter()-start,result=value));pair.append(value)
  if len(pair)==2:assert pair[0]==pair[1];pairs+=1
  if status!='COMPLETE':break
 (OUT/'queries.json').write_text(json.dumps(rows),encoding='utf-8');result=dict(status=status,pairs_equal=pairs,queries=len(rows),missing=124-len(rows),seconds=time.perf_counter()-began,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
