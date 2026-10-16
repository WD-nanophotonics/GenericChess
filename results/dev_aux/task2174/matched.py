"""Matched root-alpha/root-inclusive Core control, research only.

This control models board actions. Session declarations remain an explicit
capability gap; fullSession arm includes them. Both arms replay authoritative
root admission, iterate inclusive depth, retain root alpha, same lexical order.
"""
from math import inf,isfinite
from time import perf_counter
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,_ordered
from scripts.generic_session_win_proof import replay_bound,SessionChoice
from results.dev_aux.task2148.normal import SessionNormalReceipt
class MatchedCoreMaterialSearch:
 def __init__(self,compiled,evaluate,*,max_depth=3):
  if type(max_depth)is not int or not 1<=max_depth<=64:raise ValueError('depthmust1..64')
  self.compiled,self.evaluate,self.max_depth=compiled,evaluate,max_depth
 def choose(self,session,*,max_nodes=4096,seconds=.1,cancel=None,_clock=perf_counter):
  b=_Budget(max_nodes,seconds,cancel,_clock);before=session.to_record();state=session.state;result=session.result;selected=None;completed=0;value=None;cause='depth_budget';transitions=leaves=0;terminals={};target=session.state.position.side_to_move;rt=None
  def walk(depth,alpha,beta):
   nonlocal transitions,leaves
   b.visit();t=rt.terminal_status;b.poll()
   if t.status is not TerminalStatus.ONGOING:
    label=(t.status.value,t.winner,None);terminals[label]=terminals.get(label,0)+1;return (0. if t.winner is None else inf if t.winner==target else-inf),None
   if depth==0:
    raw=float(self.evaluate(rt.position,target));b.poll()
    if not isfinite(raw):raise ValueError('materialleafmustbefinite')
    leaves+=1;return raw,None
   own=rt.position.side_to_move==target;best=-inf if own else inf;choice=None;found=False
   for action in _ordered(rt.legal_actions(checkpoint=b.poll)):
    b.poll();rt.push(action,checkpoint=b.poll);transitions+=1
    try:score,_=walk(depth-1,alpha,beta)
    finally:rt.pop()
    if not found or(own and score>best)or(not own and score<best):best=score;choice=SessionChoice('ACTION',action=action);found=True
    if own:alpha=max(alpha,best)
    else:beta=min(beta,best)
    if alpha>=beta:break
   if not found:raise ValueError('ongoingstatehasnochoices')
   return best,choice
  try:
   b.poll()
   if self.compiled.ruleset_fingerprint!=session.compiled.ruleset_fingerprint:raise ValueError('foreignrules')
   reconstructed=replay_bound(session);b.poll()
   if reconstructed.result.status is not SessionStatus.ONGOING:cause='actual_session_terminal'
   else:
    rt=SearchPathRuntime.from_state(reconstructed.state,self.compiled);b.poll()
    for depth in range(1,self.max_depth+1):
     score,choice=walk(depth,-inf,inf);b.poll();selected=choice;value=score;completed=depth
  except _Interrupted:
   cause=b.reason
   if cause=='cancelled':selected=None;value=None
  except(ValueError,NotImplementedError):cause='unsupported_or_unreplayable_session';selected=None;value=None
  finally:
   if rt is not None:rt.assert_balanced()
   assert _same_state(session.state,state)and _same_state(session.to_record(),before)and session.result==result
  return SessionNormalReceipt(selected,'MATCHED_CORE_MATERIAL_SEARCH',b.nodes,b.elapsed(),completed,cause,value,transitions,leaves,tuple((k,v)for k,v in terminals.items()))
