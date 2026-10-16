"""Opt-in finite closed-graph NO_FORCED_WIN checker, not a DRAW solver.
Cycles are allowed only under scoped Position-only execution, draw repetition,
and finite max_ply. Certificate validation never uses reference WDL labels.
"""
from dataclasses import dataclass
from collections import deque
from time import perf_counter
from copy import copy
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,replay_bound,execute
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,_ordered
from results.dev_aux.task2199.semantic_graph import canonical,scope_reason,rule_limit

@dataclass(frozen=True)
class RefutationNode:
 edges:tuple

@dataclass(frozen=True)
class RefutationCertificate:
 ruleset_fingerprint:str
 root_record:object
 root_state:object
 target:int
 nodes:tuple

def verify_no_forced_win(session,cert,*,max_nodes=65536,seconds=5.,cancel=None,return_positions=False):
 b=_Budget(max_nodes,seconds,cancel);valid=False;reason='verified';positions={};edges=0
 try:
  b.poll();replay_bound(session)
  if type(cert)is not RefutationCertificate or cert.ruleset_fingerprint!=session.compiled.ruleset_fingerprint:raise ValueError('rule_binding')
  if not _same_state(cert.root_record,session.to_record())or not _same_state(cert.root_state,session.state):raise ValueError('root_binding')
  if session.result.status is not SessionStatus.ONGOING:raise ValueError('actual_root_terminal')
  scope=scope_reason(session.compiled)
  if scope is not None:raise ValueError(scope)
  if type(cert.target)is not int or cert.target not in(0,1):raise ValueError('invalid_target')
  if type(cert.nodes)is not tuple or not cert.nodes:raise ValueError('invalid_nodes')
  if rule_limit(session.compiled,'max_ply')<=session.state.ply_count:raise ValueError('no_remaining_horizon')
  positions[0]=session.state.position;queue=deque([0]);visited=set()
  while queue:
   b.poll();i=queue.popleft()
   if i in visited:continue
   if type(i)is not int or not 0<=i<len(cert.nodes):raise ValueError('invalid_node_index')
   visited.add(i);b.visit();node=cert.nodes[i]
   if type(node)is not RefutationNode or type(node.edges)is not tuple:raise ValueError('invalid_node')
   current=canonical(positions[i],session.compiled);result=current.result;b.poll()
   if result.status is not SessionStatus.ONGOING:
    if result.winner==cert.target:raise ValueError('target_WIN_leaf')
    if node.edges:raise ValueError('terminal_has_edges')
    continue
   legal=[SessionChoice('ACTION',action=a)for a in _ordered(current.legal_actions())]
   if not legal:raise ValueError('ongoing_without_legal_actions')
   selected=[x for x,j in node.edges]
   if any(type(x)is not SessionChoice or x.kind!='ACTION'or x.action is None or x.declaration_id is not None for x in selected):raise ValueError('invalid_choice')
   if any(_same_state(x,y)for n,x in enumerate(selected)for y in selected[:n]):raise ValueError('duplicate_choice')
   if positions[i].side_to_move==cert.target:
    if len(selected)!=len(legal)or any(not any(_same_state(x,y)for y in selected)for x in legal):raise ValueError('missing_target_action')
   elif len(selected)!=1 or not any(_same_state(selected[0],x)for x in legal):raise ValueError('invalid_defender_choice')
   for choice,j in node.edges:
    b.poll()
    if type(j)is not int or not 0<=j<len(cert.nodes):raise ValueError('invalid_child')
    child=copy(current);execute(child,choice);edges+=1;b.poll()
    if j in positions:
     if not _same_state(positions[j],child.state.position):raise ValueError('inconsistent_full_position_merge')
    else:positions[j]=child.state.position
    if j not in visited:queue.append(j)
  if len(visited)!=len(cert.nodes):raise ValueError('unreachable_nodes')
  valid=True
 except _Interrupted:reason=b.reason
 except(ValueError,TypeError,KeyError,IndexError)as e:reason=str(e)
 result=dict(verified=valid,claim='NO_FORCED_WIN'if valid else'UNKNOWN',reason=reason,nodes=b.nodes,edges=edges,seconds=b.elapsed(),scope='FiniteclosedfullPosition safetytrap: ALLtargetactions/ONEdefenderaction, no targetwinnerterminal; cyclesallowed, actualdrawrepetition/finiteplyterminate. NotactualDRAW/LOSS/reward orallgenerateddomain. No teacherlabels usedbychecker.')
 if return_positions and valid:return result,positions
 return result

class RefutationCursor:
 def __init__(self,session,cert,*,max_nodes=65536,seconds=5.,cancel=None):
  receipt=verify_no_forced_win(session,cert,max_nodes=max_nodes,seconds=seconds,cancel=cancel,return_positions=True)
  if not isinstance(receipt,tuple):raise ValueError('unverified_refutation:'+receipt['reason'])
  self.receipt,self.positions=receipt;self.certificate=cert;self.index=0;self.record=session.to_record();self.state=session.state;self.result=session.result;self.active=True
 def choose(self,session):
  if not self.active or session.to_record()!=self.record or not _same_state(session.state,self.state):raise ValueError('cursor_binding')
  if session.result.status is not SessionStatus.ONGOING or session.state.position.side_to_move==self.certificate.target:raise ValueError('not_defender_turn')
  return self.certificate.nodes[self.index].edges[0][0]
 def observe(self,before,choice,after):
  if not self.active or before.to_record()!=self.record or not _same_state(before.state,self.state):raise ValueError('cursor_binding')
  expected=copy(before);execute(expected,choice)
  if expected.to_record()!=after.to_record()or not _same_state(expected.state,after.state)or expected.result!=after.result:raise ValueError('invalid_actual_transition')
  matches=[j for x,j in self.certificate.nodes[self.index].edges if _same_state(x,choice)]
  if len(matches)!=1 or not _same_state(self.positions[matches[0]],after.state.position):raise ValueError('outside_refutation')
  if after.result.status is not SessionStatus.ONGOING:
   if after.result.winner==self.certificate.target:raise ValueError('target_won')
   self.active=False
  self.index=matches[0];self.record=after.to_record();self.state=after.state;self.result=after.result
