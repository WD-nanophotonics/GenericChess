"""Scoped negative proof scheduling, never arbitrary-history WDL or reward.

The complete position graph supplies a non-winning strategy for the opponent
when target positional value <=0. Under these exact rules history only ADDS
draw terminals; it cannot create a target win or remove a defender's legal move.
Positive positional values still delegate because old repeats can spoil wins.
"""
from time import perf_counter
from dataclasses import replace
from results.dev_aux.task2068.teacher import CanonicalTeacher
from scripts.generic_inventory_proof_transport import execution_differences
from scripts.generic_session_win_proof import SessionProofResult,replay_bound
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_win_proof import _Budget,_Interrupted
from scripts.generic_proof_rnb_bridge import actor_state
from generic_chess.session.result import SessionStatus
class CompleteGraphNoWinFilter:
 def __init__(self,teacher,*,solver=prove_session_win_batch_pn):
  if not isinstance(teacher,CanonicalTeacher):raise ValueError('audited canonicalteacher required')
  c=teacher.reference
  if(c.repetition_policy!='draw'or c.max_ply!=96 or c.no_progress_draw is not None or c.pass_enabled or c.declarations or c.automatic_adjudications or c.repeated_cycle_target_conditions or c.consecutive_action_adjudications):raise ValueError('historymustonlyadddraws')
  self.teacher=teacher;self.solver=solver
 def no_win(self,session,target):
  if execution_differences(self.teacher.reference,session.compiled)or session.result.status is not SessionStatus.ONGOING:return False
  pos=session.state.position
  if pos.aux_state or any(h.total()for h in pos.hands)or any(p is not None and(p.promoted or p.base_type_id!=p.current_type_id)for p in pos.board):return False
  r=self.teacher.rows.get(self.teacher.key(actor_state(session.state)))
  if r is None:return False
  value={'WIN':1,'DRAW':0,'LOSS':-1}[r['label']]
  if target!=pos.side_to_move:value=-value
  if value>0:return False
  replay_bound(session);return True
 def __call__(self,session,*,target=None,max_nodes=4096,seconds=1.,max_depth=8,cancel=None,_clock=perf_counter):
  target=session.state.position.side_to_move if target is None else target
  if type(target)is not int or target not in(0,1):raise ValueError('invalidtarget')
  if type(max_depth)is not int or not 0<=max_depth<=128:raise ValueError('invaliddepth')
  b=_Budget(max_nodes,seconds,cancel,_clock)
  try:
   b.poll()
   if self.no_win(session,target):
    b.poll();return SessionProofResult('UNKNOWN',None,'certified_complete_graph_no_win',0,b.elapsed(),0)
   r=self.solver(session,target=target,max_nodes=max_nodes,seconds=max(0.,seconds-b.elapsed()),max_depth=max_depth,cancel=cancel,_clock=_clock);return replace(r,seconds=b.elapsed())
  except _Interrupted:return SessionProofResult('UNKNOWN',None,b.reason,0,b.elapsed(),0)
