"""Bounded research-only Q classification observer. No new semantic queries.
Wrap existing calls; preserve arguments/results/exceptions and restore globally.
Totals cover all entered events; detail cap is separate from search completion.
"""
from contextlib import contextmanager
from collections import Counter,defaultdict
import sys,time
from generic_chess.ai.alphabeta import search as S
from generic_chess.core.search_runtime import SearchPathRuntime

class QClassificationObserver:
 def __init__(self,detail_cap=128):
  self.detail_cap=detail_cap;self.details=[];self.dropped=0;self.counts=Counter();self.cost=defaultdict(Counter);self.stack=[];self.qstack=[];self.next_q=0
 def __enter__(self):
  self.originals=(SearchPathRuntime.pushed,S.noisy_child,S._quiescence_runtime,S._order_qactions)
  pushed,noisy,q,order=self.originals
  def watched_push(runtime,action,checkpoint=None):
   f=sys._getframe(1);site=f.f_code.co_name+':'+str(f.f_lineno)
   return self.push_context(pushed,runtime,action,checkpoint,site)
  def watched_noisy(*args,**kwargs):
   event=self.stack[-1]if self.stack else None;stats=args[6]if len(args)>6 else kwargs.get('stats');fields=('capture_qactions','material_change_qactions','promotion_qactions','checking_move_qactions','checking_drop_qactions');before={k:getattr(stats,k,0)for k in fields};checked=[]
   actual=list(args);check=actual[5]
   def actual_check():
    v=check();checked.append(v);return v
   actual[5]=actual_check;t=time.perf_counter()
   try:value=noisy(*actual,**kwargs)
   except BaseException:
    self.counts['classification_aborted']+=1
    if event:event['outcome']='classification_aborted'
    raise
   elapsed=time.perf_counter()-t;changed={k:getattr(stats,k,0)-before[k]for k in fields}
   if not value:outcome='quiet_rejected'
   elif changed['capture_qactions']:outcome='capture_included'
   elif changed['material_change_qactions']:outcome='material_included'
   elif changed['promotion_qactions']:outcome='promotion_included'
   elif checked:outcome='check_included'
   else:
    # Original already read this cached runtime terminal value. No computation.
    assert args[1].terminal_status.is_terminal
    outcome='terminal_included'
   self.counts['classifications']+=1;self.counts[outcome]+=1;self.cost[outcome]['classification_seconds']+=elapsed
   if event:
    event['outcome']=outcome;event['classification_seconds']=elapsed;event['cached_child_terminal']=str(args[1].terminal_status)
   if self.qstack:
    node=self.qstack[-1];node['quiet']+=int(not value);node['included']+=int(bool(value))
   return value
  def watched_q(*args,**kwargs):
   ctx=args[-1];self.next_q+=1;event=dict(q_id=self.next_q,offered=None,visited=0,quiet=0,included=0,last_child_score=None,in_check=None,finished=False,beta=args[1]);self.qstack.append(event)
   try:
    value=q(*args,**kwargs);event['finished']=True
    if len(self.qstack)>1 and self.stack and self.stack[-1]['site'].startswith('_quiescence_runtime:'):self.qstack[-2]['last_child_score']=-value
    return value
   finally:
    self.qstack.pop();self.counts['q_calls']+=1
    if event['offered']is None:self.counts['frontier_not_generated']+=1
    else:
     assert event['visited']<=event['offered'];self.counts['generated_actions']+=event['offered'];self.counts['visited_actions']+=event['visited'];self.counts['generated_unvisited']+=event['offered']-event['visited']
    if not event['finished']:self.counts['q_aborted']+=1
    elif event['offered']is not None:
     scope='evasion'if event['in_check']else'ordinary';cutoff=event['last_child_score']is not None and event['last_child_score']>=event['beta'];kind='child_beta_cutoff'if cutoff else'exhausted';key=scope+':'+kind;self.counts[key]+=1;self.counts[key+':quiet_paid']+=event['quiet'];self.counts[key+':included']+=event['included'];self.counts[key+':visited']+=event['visited'];self.counts[key+':unvisited']+=event['offered']-event['visited']
     if cutoff:self.counts[key+':quiet_ge4']+=int(event['quiet']>=4);self.counts[key+':quiet_ge16']+=int(event['quiet']>=16)
  def watched_order(*args,**kwargs):
   value=order(*args,**kwargs)
   if self.qstack:
    event=self.qstack[-1];assert event['offered']is None;event['offered']=len(value);event['in_check']=kwargs.get('in_check',False)
   return value
  SearchPathRuntime.pushed=watched_push;S.noisy_child=watched_noisy;S._quiescence_runtime=watched_q;S._order_qactions=watched_order
  return self
 @contextmanager
 def push_context(self,original,runtime,action,checkpoint,site):
  event=dict(site=site,outcome='not_classified',push_seconds=0.,pop_seconds=0.,classification_seconds=0.)
  if self.qstack and site.startswith('_quiescence_runtime:'):self.qstack[-1]['visited']+=1
  cm=original(runtime,action,checkpoint=checkpoint);t=time.perf_counter()
  try:value=cm.__enter__()
  except BaseException:
   event['push_seconds']=time.perf_counter()-t;event['outcome']='push_aborted';self.collect(event);raise
  event['push_seconds']=time.perf_counter()-t;self.stack.append(event)
  try:
   try:yield value
   except BaseException:
    info=sys.exc_info();t=time.perf_counter();suppressed=cm.__exit__(*info);event['pop_seconds']=time.perf_counter()-t
    if not suppressed:raise
   else:
    t=time.perf_counter();cm.__exit__(None,None,None);event['pop_seconds']=time.perf_counter()-t
  finally:self.stack.pop();self.collect(event)
 def collect(self,event):
  self.counts['push_attempts']+=1;key=event['site']+':'+event['outcome'];c=self.cost[key];c['calls']+=1;c['push_seconds']+=event['push_seconds'];c['pop_seconds']+=event['pop_seconds'];c['classification_seconds']+=event['classification_seconds']
  if len(self.details)<self.detail_cap:self.details.append(dict(event))
  else:self.dropped+=1
 def __exit__(self,*exc):
  SearchPathRuntime.pushed,S.noisy_child,S._quiescence_runtime,S._order_qactions=self.originals
  assert not self.stack and not self.qstack
 def result(self):return dict(counts=dict(self.counts),cost={k:dict(v)for k,v in self.cost.items()},details=self.details,detail_cap=self.detail_cap,dropped_details=self.dropped,scope='Actualcalls only; generatedunvisited isnotquietfiltered. Nongeneratedfrontiers UNKNOWN. Push/pop andclassifier timers exclude childrecursion; different aggregate rows can overlap, no sum with inclusiveQ. Detailtruncation doesnotremoveaggregates; elapsedobserverperturbation separatelycontrolled.')
