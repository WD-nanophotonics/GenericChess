"""End-to-end short observation diagnostic, explicit per-file gaps, no adoption."""
from pathlib import Path
from copy import copy
from dataclasses import asdict
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task109.adapter import PersistentStop
from results.dev_aux.task2199.semantic_graph import prove_graph,verify_graph
OUT=Path('results/dev_aux/task2211')
class TimedReader(EvidenceStopReader):
 def __init__(self,root):super().__init__(root);self.events=[];self.began=time.perf_counter()
 def __call__(self):
  for index,path in enumerate(self.paths):
   raw=None;start=time.perf_counter()-self.began
   try:
    raw=path.read_bytes();end=time.perf_counter()-self.began
    self.reads+=1;self.bytes_read+=len(raw)
    previous=self._cache.get(path)
    if previous is None or previous[0]!=raw:
     value=json.loads(raw);stopped=bool(value.get('user_paused')or value.get('stopped'));self._cache[path]=(raw,stopped);self.parses+=1
    else:stopped=previous[1]
    self.events.append(dict(file=index,start=start,end=end,bytes=len(raw),stopped=stopped))
   except(OSError,ValueError,TypeError,AttributeError)as error:self.failed(path,raw,error)
   if stopped:raise PersistentStop('persistent user stop')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def freeze():
 p=dict(question='Does less frequent observation still save caller cost when compile/replay/verification/recording and actual per-file observation gaps are measured?',input='results/dev_aux/task2208/roots.json',input_sha=sha('results/dev_aux/task2208/roots.json'),styles=['CURRENT_INNER_FRESH','CALLER_DEADLINE_OUTER_FRESH'],total_seconds=.2,one_cap_seconds=120,expected_queries=16,nodes=8192,edges=65536,depth=96,pins={x:sha(x)for x in('results/dev_aux/task2211/probe.py','results/dev_aux/task2199/semantic_graph.py','results/dev_aux/task2153/stop_evidence.py')},scope='ALL8exposedroots retained,2styles mechanicallybalanced. Caller clockstarts BEFORE freshprecheck/compile/replay,includessearch/verify. Postcheck/recording arepaid andreported butatomic operations mayoverrun. Per-file observation start/end intervals, not6-file atomic snapshot. No flags modified, no simulated userstop orproductionpollingadoption. UNKNOWNnotdraw. Instrumentation/ordinaryconcurrency limits timings, no causal throughput claim.')
 with(OUT/'plan.json').open('x',encoding='utf-8')as f:json.dump(p,f,indent=2)
 print('FROZEN16calls_noquery')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text())
 assert sha(p['input'])==p['input_sha']
 for x,h in p['pins'].items():assert sha(x)==h
 began=time.perf_counter();deadline=began+p['one_cap_seconds'];stop=TimedReader(Path.cwd())
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=sha(OUT/'plan.json'))));rows=[];events=[]
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as f:
  for root in json.loads(Path(p['input']).read_text()):
   styles=p['styles']if root['index']%2==0 else list(reversed(p['styles']))
   for style in styles:
    if time.perf_counter()>=deadline:break
    start=time.perf_counter();end=min(start+p['total_seconds'],deadline);nevents=len(stop.events)
    def poll():
     if style=='CURRENT_INNER_FRESH':stop()
     return time.perf_counter()>=end
    phase=time.perf_counter();stop();pre=time.perf_counter()-phase
    phase=time.perf_counter();c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));record=deserialize_game_record(json.dumps(root['record']));s=GameSession.replay(c,record)
    assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha'];prep=time.perf_counter()-phase
    phase=time.perf_counter();r=prove_graph(s,target=root['target'],max_nodes=p['nodes'],max_edges=p['edges'],max_depth=p['depth'],seconds=max(0.,end-time.perf_counter()),cancel=poll);query=time.perf_counter()-phase;vr=None;verify=0.
    if r.certificate is not None:
     phase=time.perf_counter();vr=verify_graph(s,r.certificate,max_nodes=131072,seconds=max(0.,end-time.perf_counter()),cancel=poll);verify=time.perf_counter()-phase
    phase=time.perf_counter();stop();post=time.perf_counter()-phase
    row={k:v for k,v in asdict(r).items()if k!='certificate'};row.update(query=len(rows),root=root['index'],style=style,precheck_seconds=pre,preparation_seconds=prep,proof_measured_seconds=query,verification_seconds=verify,postcheck_seconds=post,verification=vr,through_postcheck_seconds=time.perf_counter()-start,event_start=nevents,event_end=len(stop.events))
    phase=time.perf_counter();blob=json.dumps(row);encoding=time.perf_counter()-phase;phase=time.perf_counter();f.write(blob+'\n');f.flush();writing=time.perf_counter()-phase
    row.update(encoding_seconds=encoding,journal_write_seconds=writing,whole_seconds=time.perf_counter()-start);rows.append(row);events.extend(dict(e,query=row['query'])for e in stop.events[nevents:])
 perfile={}
 for index in range(6):
  es=[e for e in events if e['file']==index];perfile[index]=dict(observations=len(es),max_gap_between_read_starts=max((b['start']-a['start']for a,b in zip(es,es[1:])),default=0.),max_read_seconds=max((e['end']-e['start']for e in es),default=0.),read_seconds=sum(e['end']-e['start']for e in es))
 result=dict(status='COMPLETE'if len(rows)==p['expected_queries']else'PARTIAL_GLOBAL_CAP',queries=len(rows),missing=p['expected_queries']-len(rows),seconds=time.perf_counter()-began,per_file_observation=perfile,rows=rows,scope=p['scope'])
 for name,value in(('observation-events.json',events),('result.json',result)):
  with(OUT/name).open('x',encoding='utf-8')as f:json.dump(value,f,indent=2)
 print(json.dumps({k:result[k]for k in('status','queries','seconds')}))
if __name__=='__main__':import sys;{'freeze':freeze,'run':run}[sys.argv[1]]()
