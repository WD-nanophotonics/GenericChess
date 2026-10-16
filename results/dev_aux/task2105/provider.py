"""Price-independent total-board-count trigger; UNKNOWN never adjudicates DRAW."""
from time import perf_counter
from results.dev_aux.task2088.provider import CompositeProvider
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
class TriggerProvider:
 def __init__(self,teacher,*,pn_nodes=32,pn_seconds=.02,solver=prove_session_win_batch_pn):
  self.pn_nodes=pn_nodes;self.pn_seconds=pn_seconds;self.solver=solver
  def small(session,**kwargs):
   kwargs['max_nodes']=min(kwargs['max_nodes'],self.pn_nodes);kwargs['seconds']=min(kwargs['seconds'],self.pn_seconds)
   return self.solver(session,**kwargs)
  self.small=small;self.composite=CompositeProvider(teacher,fallback=small);self.last_route=None
 def __call__(self,session,*,target=None,max_nodes=1024,seconds=.2,max_depth=64,cancel=None,_clock=perf_counter):
  if type(target)is bool:raise ValueError('invalidtarget')
  if sum(p is not None for p in session.state.position.board)>4:
   self.last_route='ABOVE4_SMALL_GENERIC_PN'
   return self.small(session,target=target,max_nodes=max_nodes,seconds=seconds,max_depth=max_depth,cancel=cancel,_clock=_clock)
  self.last_route='AT_MOST4_QUALIFIED_COMPOSITE'
  return self.composite(session,target=target,max_nodes=max_nodes,seconds=seconds,max_depth=max_depth,cancel=cancel,_clock=_clock)
