"""Separate2091 hypothesis: actual full-history tree validation can replace the
coarse previous-repeat gate. Original2086 remains unchanged. Not arbitrary-
history table WDL: a draw on ANY defense aborts construction as UNKNOWN.
"""
from copy import copy
from time import perf_counter
from scripts.generic_session_win_proof import SessionProofNode,SessionWinCertificate,SessionProofResult,SessionChoice,replay_bound,execute
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state
from scripts.generic_inventory_proof_transport import execution_differences
from scripts.generic_proof_rnb_bridge import actor_state,uci
from generic_chess.session.result import SessionStatus
class HistoryCheckedRankProvider:
 def __init__(self,teacher):self.teacher=teacher
 def __call__(self,session,*,target=None,max_nodes=1024,seconds=1.5,max_depth=64,cancel=None,_clock=perf_counter):
  target=session.state.position.side_to_move if target is None else target
  if type(target)is not int or target not in(0,1):raise ValueError('invalidtarget')
  if type(max_depth)is not int or not 0<=max_depth<=128:raise ValueError('invaliddepth')
  b=_Budget(max_nodes,seconds,cancel,_clock);root=session.to_record();state=session.state;result=session.result
  def out(reason,node=None):return SessionProofResult('PROVEN_WIN'if node is not None else'UNKNOWN',None if node is None else SessionWinCertificate(session.compiled.ruleset_fingerprint,root,state,target,node),reason,b.nodes,b.elapsed(),0 if node is None else node.rank)
  def build(current):
   b.visit()
   if current.result.status is not SessionStatus.ONGOING:
    if current.result.winner!=target:raise ValueError('actualterminalnotwin')
    return SessionProofNode(0,terminal=current.result)
   r=self.teacher.rows[self.teacher.key(actor_state(current.state))];v={'WIN':1,'DRAW':0,'LOSS':-1}[r['label']];v=v if current.state.position.side_to_move==target else-v
   if v!=1:raise ValueError('notargetwin')
   legal={uci(a):a for a in current.legal_actions()};b.poll()
   names=[r['winning_action']]if current.state.position.side_to_move==target else list(legal)
   if set(legal)!={e['action']for e in r['actions']}:raise ValueError('frontiermismatch')
   edges=[]
   for name in names:
    b.poll();child=copy(current);choice=SessionChoice('ACTION',action=legal[name]);execute(child,choice);b.poll();childrow=self.teacher.rows[self.teacher.key(actor_state(child.state))]
    if childrow['rank']is None or childrow['rank']>=r['rank']:raise ValueError('ranknotdecreasing')
    edges.append((choice,build(child)))
   return SessionProofNode(1+max(n.rank for _,n in edges),tuple(edges))
  try:
   b.poll()
   if execution_differences(self.teacher.reference,session.compiled):return out('foreign_execution')
   replay_bound(session);b.poll()
   if result.status is not SessionStatus.ONGOING:return out('already_terminal')
   pos=session.state.position
   if pos.aux_state or any(h.total()for h in pos.hands)or any(p is not None and(p.promoted or p.base_type_id!=p.current_type_id)for p in pos.board):return out('state_outside_scope')
   row=self.teacher.rows.get(self.teacher.key(actor_state(state)))
   if row is None:return out('position_outside_graph')
   value={'WIN':1,'DRAW':0,'LOSS':-1}[row['label']];value=value if pos.side_to_move==target else-value
   if value!=1:return out('not_positive_table_value')
   # Every actual-history branch below must terminate in target WIN; old counts
   # are replayed, not treated as positional table WIN. No coarse count<=1 gate.
   if row['rank']>min(max_depth,96-state.ply_count):return out('rank_outside_remaining_horizon')
   node=build(session);b.poll();return out('budgeted_rank_full_session_certificate',node)
  except _Interrupted:return out(b.reason)
  except(KeyError,ValueError,NotImplementedError):return out('unsupported_or_actual_strategy_invalid')
  finally:assert session.to_record()==root and _same_state(session.state,state)and session.result==result
