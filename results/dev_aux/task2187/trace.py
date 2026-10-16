"""Observable, bounded four-query attribution. Existing implementations unchanged."""
from pathlib import Path
from dataclasses import replace,asdict
from contextlib import contextmanager
from collections import Counter,defaultdict
from copy import copy
import json,time,hashlib,datetime
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
import scripts.generic_session_win_proof_batch_pn as pn
import results.dev_aux.task2179.graph as graph
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from results.dev_aux.task2048.portable_certificate import encode
from results.dev_aux.task2181.run import encode as encode_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2187')

def root_session(root):
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')))
 board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in root['root'][:-1])
 c=replace(c,initial_position=replace(c.initial_position,board=board,side_to_move=0),initial_setup_positions={})
 s=GameSession(c);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['root_state_sha'];return s

class Trace:
 def __init__(self,limit=4096):
  self.limit=limit;self.events=[];self.dropped=0;self.stack=[];self.exclusive=defaultdict(float);self.inclusive=defaultdict(float);self.calls=Counter()
 @contextmanager
 def measure(self,name):
  start=time.perf_counter();frame=[name,start,0.];self.stack.append(frame);self.calls[name]+=1
  try:yield
  finally:
   elapsed=time.perf_counter()-start;assert self.stack.pop()is frame
   self.inclusive[name]+=elapsed;self.exclusive[name]+=elapsed-frame[2]
   if self.stack:self.stack[-1][2]+=elapsed
 def call(self,name,f,*args,**kwargs):
  with self.measure(name):return f(*args,**kwargs)
 def observe(self,state,record,origin):
  with self.measure('trace_encode'):
   if len(self.events)>=self.limit:self.dropped+=1;return
   position=state.position
   self.events.append(dict(origin=origin,state_repr=repr(state),state_sha=hashlib.sha256(repr(state).encode()).hexdigest(),position_repr=repr(position),record=json.loads(serialize_game_record(record)),position_token=repr(graph.position_token(position)),side=position.side_to_move,ply=state.ply_count,result=repr(state.terminal_status)))
 @contextmanager
 def hooks(self,arm):
  patches=[]
  def patch(obj,name,f):patches.append((obj,name,getattr(obj,name)));setattr(obj,name,f)
  def timed(obj,name,category):
   old=getattr(obj,name);patch(obj,name,lambda *a,**kw:self.call(category,old,*a,**kw))
  old_legal=GameSession.legal_actions
  def legal(s,*a,**kw):
   if arm=='GRAPH':self.observe(s.state,s.to_record(),'canonical_graph_frontier')
   return self.call('session_legal_actions',old_legal,s,*a,**kw)
  patch(GameSession,'legal_actions',legal)
  timed(GameSession,'__init__','session_init')
  timed(pn,'legal_successors','core_eager_batch')
  timed(pn,'replay_bound','root_replay')
  timed(graph,'replay_bound','root_replay')
  timed(graph,'canonical','canonical_total')
  timed(graph,'execute','session_execute')
  timed(graph,'copy','session_copy')
  try:yield
  finally:
   for obj,name,old in reversed(patches):setattr(obj,name,old)
 def children(self,current,b,cost):
  self.observe(current.state,current.to_record(),'fullhistory_PN_frontier')
  gen=pn._children(current,b,cost)
  while True:
   try:
    with self.measure('forward_children_step'):item=next(gen)
   except StopIteration:return
   yield item
 def receipt(self,elapsed):
  return dict(events=len(self.events),dropped=self.dropped,calls=dict(self.calls),exclusive_seconds=dict(self.exclusive),inclusive_seconds=dict(self.inclusive),unattributed_seconds=elapsed-sum(self.exclusive.values()),note='Nested categories exclusive; trace encoding is paid and separate. Wrapping/clock overhead and PN selection/graph bookkeeping remain unattributed. Frontier observations before actual public generation, not free teacher labels.')

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single60cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text());began=time.perf_counter();deadline=began+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd())
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())),encoding='utf-8')
 roots={r['family']:r for r in json.loads(Path(p['inputs']).read_text())['roots']};rows=[];traces=[];certs=[]
 def cancelled():stop();return time.perf_counter()>=deadline
 for family,arm in p['order']:
  if cancelled():break
  s=root_session(roots[family]);t=Trace(p['trace_limit'])
  def cancel():return t.call('fresh_stop_read',cancelled)
  qstart=time.perf_counter()
  with t.hooks(arm):
   if arm=='PN':r=pn.prove_session_win_batch_pn(s,target=roots[family]['target'],max_nodes=p['nodes'],seconds=min(p['seconds'],deadline-time.perf_counter()),max_depth=p['depth'],cancel=cancel,_children_factory=t.children)
   else:r=graph.prove_graph(s,target=roots[family]['target'],max_nodes=p['nodes'],max_edges=p['edges'],seconds=min(p['seconds'],deadline-time.perf_counter()),max_depth=p['depth'],cancel=cancel)
  elapsed=time.perf_counter()-qstart
  row={k:v for k,v in asdict(r).items()if k!='certificate'};row.update(family=family,arm=arm,outer_seconds=elapsed,trace=t.receipt(elapsed),verification=None,actual_mate=None)
  if r.certificate is not None:
   certs.append(dict(family=family,arm=arm,certificate=encode(r.certificate.tree)if arm=='PN'else encode_graph(r.certificate)))
   if arm=='PN':vr=verify_session_certificate(s,r.certificate,max_nodes=131072,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancelled);cls=SessionStrategyCursor
   else:vr=graph.verify_graph(s,r.certificate,max_nodes=131072,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancelled);cls=graph.GraphStrategyCursor
   row['verification']=vr
   if vr['verified']:
    cur=cls(s,r.certificate,max_nodes=131072,seconds=min(4.,max(0.,deadline-time.perf_counter())),cancel=cancelled);actual=copy(s);moves=0
    while actual.result.status is SessionStatus.ONGOING:
     if cancelled():raise TimeoutError('actualcursor_globalcap')
     if actual.state.position.side_to_move==roots[family]['target']:choice=cur.choose(actual)
     elif arm=='PN':choice=max(cur.node.edges,key=lambda e:e[1].rank)[0]
     else:choice=max(cur.certificate.nodes[cur.index].edges,key=lambda e:cur.certificate.nodes[e[1]].rank)[0]
     cur.commit(actual,choice);moves+=1
    assert actual.result.winner==roots[family]['target'];row['actual_mate']=dict(moves=moves,winner=actual.result.winner,record=json.loads(serialize_game_record(actual.to_record())))
  traces.append(dict(family=family,arm=arm,events=t.events));rows.append(row)
  print(json.dumps(dict(family=family,arm=arm,status=r.status,events=len(t.events),seconds=elapsed)),flush=True)
 # Save observations before loading any teacher labels; no labels passed to query.
 for name,data in [('queries.json',rows),('traces.json',traces),('certificates.json',certs)]:
  with(OUT/name).open('x',encoding='utf-8')as f:json.dump(data,f)
 result=dict(status='COMPLETE'if len(rows)==4 else'PARTIAL_GLOBAL_CAP',queries=len(rows),missing=4-len(rows),seconds=time.perf_counter()-began,actual_stop_reads=stop.reads,source_mutations=0,labels_used_during_query=False)
 (OUT/'completion.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
