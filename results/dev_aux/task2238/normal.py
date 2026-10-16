"""Opt-in full GameSession material alpha-beta reference, not a WIN proof.

Existing normal player is board-action-only. This baseline keeps all owned
Session declarations as typed choices, including actual failure outcomes.
A finite material leaf NEVER supplies a WDL label or certificate. No TT,
state-only merge, special-game heuristic, product/default integration.
"""
from dataclasses import dataclass
from copy import copy
from time import perf_counter
from math import inf,isfinite
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state
from scripts.generic_session_win_proof import choices,execute,replay_bound

@dataclass(frozen=True)
class SessionNormalReceipt:
 choice:object|None
 source:str
 nodes:int
 seconds:float
 completed_depth:int
 exit_cause:str
 score:float|None
 session_transitions:int
 material_leaves:int
 terminal_leaves:tuple

class SeededMaterialSearch:
 def __init__(self,compiled,evaluate,*,max_depth=3,priority_seed=0):
  if type(max_depth)is not int or not 1<=max_depth<=64:raise ValueError('depthmust1..64')
  self.compiled,self.evaluate,self.max_depth=compiled,evaluate,max_depth
  self.priority_seed=priority_seed
 def prioritized(self,session,budget):
  import hashlib,json
  from results.dev_aux.task2175.receipt import choice_value
  legal=list(choices(session,budget));budget.poll()
  return sorted(legal,key=lambda c:hashlib.sha256((str(self.priority_seed)+":"+json.dumps(choice_value(c),sort_keys=True,separators=(",",":"))).encode()).hexdigest())
 def choose(self,session,*,max_nodes=4096,seconds=.1,cancel=None,_clock=perf_counter):
  b=_Budget(max_nodes,seconds,cancel,_clock);before=session.to_record();state=session.state;result=session.result
  selected=None;completed=0;value=None;cause='depth_budget';transitions=leaves=0;terminals={}
  target=session.state.position.side_to_move
  def terminal_score(s):
   r=s.result
   if r.status is SessionStatus.ONGOING:return None
   label=(r.status.value,r.winner,r.declaration_outcome)
   terminals[label]=terminals.get(label,0)+1
   return 0. if r.winner is None else inf if r.winner==target else-inf
  def walk(s,depth,alpha,beta):
   nonlocal transitions,leaves
   b.visit();terminal=terminal_score(s);b.poll()
   if terminal is not None:return terminal,None
   if depth==0:
    raw=float(self.evaluate(s.state.position,target));b.poll()
    if not isfinite(raw):raise ValueError('materialleafmustbefinite')
    leaves+=1;return raw,None
   own=s.state.position.side_to_move==target;best=-inf if own else inf;choice=None;found=False
   for action in self.prioritized(s,b):
    b.poll();child=copy(s);execute(child,action);transitions+=1;b.poll()
    score,_=walk(child,depth-1,alpha,beta)
    if not found or(own and score>best)or(not own and score<best):best=score;choice=action;found=True
    if own:alpha=max(alpha,best)
    else:beta=min(beta,best)
    if alpha>=beta:break
   if not found:raise ValueError('ongoingsessionhasnochoices')
   return best,choice
  try:
   b.poll()
   if self.compiled.ruleset_fingerprint!=session.compiled.ruleset_fingerprint:raise ValueError('foreignrules')
   reconstructed=replay_bound(session);b.poll()
   if reconstructed.result.status is not SessionStatus.ONGOING:cause='actual_session_terminal'
   else:
    for depth in range(1,self.max_depth+1):
     score,choice=walk(reconstructed,depth,-inf,inf);b.poll()
     selected=choice;value=score;completed=depth
  except _Interrupted:
   cause=b.reason
   if cause=='cancelled':selected=None;value=None
  except (ValueError,NotImplementedError):
   cause='unsupported_or_unreplayable_session';selected=None;value=None
  finally:assert _same_state(session.state,state)and _same_state(session.to_record(),before)and session.result==result
  return SessionNormalReceipt(selected,'FULL_SESSION_MATERIAL_SEARCH',b.nodes,b.elapsed(),completed,cause,value,transitions,leaves,tuple((k,v)for k,v in terminals.items()))
