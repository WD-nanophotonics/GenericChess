"""Scoped Core-canonical semantic-position proof prototype, opt-in only.

No injected GameSession internals or recompiled/changed rule set. Canonical
GameState is explicitly fresh history; real root/history admission and final
actual GameSession cursor remain mandatory. Full Position is retained.
"""
from dataclasses import dataclass,replace
from collections import deque
from copy import copy
from time import perf_counter
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus,terminal_result
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.rules.compiled import CompiledRuleSet
from generic_chess.rules.ir import CompiledSemanticRuleset,CompiledSemanticSupport
from generic_chess.rules.execution import ExecutableSemanticRuleset
SEMANTIC_TYPES=(CompiledSemanticRuleset,ExecutableSemanticRuleset)
from generic_chess.session.result import SessionStatus,session_result_from_terminal
from scripts.generic_session_win_proof import SessionChoice,execute,replay_bound
from scripts.generic_win_proof import _Budget,_Interrupted,_ordered,_same_state
from results.dev_aux.task2179.graph import GraphNode,GraphCertificate,GraphResult,position_token

def rule_limit(c,name):
 return getattr(c.support if type(c)in SEMANTIC_TYPES else c,name)

def scope_reason(c):
 if type(c)not in(CompiledRuleSet,)+SEMANTIC_TYPES:return 'unsupported_compiled_type'
 if type(c)in SEMANTIC_TYPES:
  if type(c.support)is not CompiledSemanticSupport or not c.ir.capabilities.new_ir_core_executable:return 'unsupported_semantic_payload'
  # S4 and transition-trigger expansion remain separate future work, not
  # silently claimed by basic semantic aux/promotion/drop qualification.
  if any(p.postconditions for p in c.ir.patterns):return 'unsupported_semantic_postcondition'
  if c.ir.triggers:return 'unsupported_semantic_trigger'
  payloads=(c,c.support)
 else:payloads=(c,)
 for p in payloads:
  if getattr(p,'declarations',()):return 'unsupported_declarations'
  if p.repetition_policy!='draw':return 'unsupported_perpetual_history'
  if p.automatic_adjudications or p.no_progress_draw is not None or p.consecutive_action_adjudications:return 'unsupported_history_adjudication'
 if c.repeated_cycle_target_conditions:return 'unsupported_history_adjudication'
 for name in('repetition_limit','max_ply'):
  value=rule_limit(c,name)
  if type(value)is not int or value<(2 if name=='repetition_limit'else 1):return 'unsupported_'+name
 return None

@dataclass
class CoreCanonical:
 compiled:object
 state:object
 @property
 def result(self):return session_result_from_terminal(self.state.terminal_status)
 def legal_actions(self):return tuple(legal_actions(self.state,self.compiled))
 def submit(self,action):self.state=apply_action(self.state,action,self.compiled);return self.result

def canonical(position,c):
 key=repetition_identity_key(position,c)
 state=GameState(position,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
 state=replace(state,terminal_status=terminal_result(state,c))
 assert _same_state(state.position,position)
 return CoreCanonical(c,state)

def verify_graph(session,cert,*,max_nodes=65536,seconds=1.,cancel=None,_clock=perf_counter,return_positions=False):
 b=_Budget(max_nodes,seconds,cancel,_clock);reason='verified';valid=False;edges_checked=0;positions={};identities={};visited=set();visiting=set();tree_counts={}
 def fail(message):raise ValueError(message)
 def check(index,position):
  nonlocal edges_checked
  b.poll()
  if type(index)is not int or not 0<=index<len(cert.nodes):fail('invalid_node_index')
  if index in positions:
   if not _same_state(position,positions[index]):fail('inconsistent_full_position_merge')
  else:
   token=position_token(position);identity=repetition_identity_key(position,session.compiled)
   if identity in identities and identities[identity]!=index:fail('repetition_identity_alias')
   identities[identity]=index;positions[index]=position
  if index in visited:return tree_counts[index]
  if index in visiting:fail('cyclic_graph')
  visiting.add(index);b.visit();node=cert.nodes[index]
  if type(node)is not GraphNode or type(node.rank)is not int or node.rank<0 or type(node.edges)is not tuple:fail('invalid_node')
  s=canonical(position,session.compiled);b.poll();result=s.result
  if result.status is not SessionStatus.ONGOING:
   if node.rank!=0 or node.edges or result.winner!=cert.target or not _same_state(node.terminal,result):fail('invalid_terminal_WIN')
   count=1
  else:
   if node.rank==0 or node.terminal is not None or not node.edges:fail('invalid_nonterminal_rank')
   legal=_ordered(s.legal_actions());b.poll();choices=[SessionChoice('ACTION',action=a)for a in legal];selected=[choice for choice,_ in node.edges]
   if any(type(x)is not SessionChoice or x.kind!='ACTION'or x.action is None or x.declaration_id is not None for x in selected):fail('invalid_choice_type')
   if any(_same_state(x,y)for i,x in enumerate(selected)for y in selected[:i]):fail('duplicate_choice')
   if position.side_to_move==cert.target:
    if len(selected)!=1 or not any(_same_state(selected[0],x)for x in choices):fail('invalid_OR_choice')
   elif len(selected)!=len(choices)or any(not any(_same_state(x,y)for y in selected)for x in choices):fail('missing_defense')
   count=1
   for choice,child_index in node.edges:
    if type(child_index)is not int or not 0<=child_index<len(cert.nodes)or type(cert.nodes[child_index].rank)is not int or cert.nodes[child_index].rank>=node.rank:fail('nondecreasing_rank')
    b.poll();child=copy(s);execute(child,choice);edges_checked+=1;b.poll();count+=check(child_index,child.state.position)
  visiting.remove(index);visited.add(index);tree_counts[index]=count;return count
 before=session.to_record();state=session.state;result=session.result
 try:
  b.poll();replay_bound(session);b.poll()
  if session.result.status is not SessionStatus.ONGOING:raise ValueError('actual_session_terminal')
  guard=scope_reason(session.compiled)
  if guard:fail(guard)
  if type(cert)is not GraphCertificate or cert.ruleset_fingerprint!=session.compiled.ruleset_fingerprint or type(cert.target)is not int or cert.target not in(0,1)or type(cert.nodes)is not tuple or not cert.nodes:fail('invalid_certificate')
  if not _same_state(cert.root_record,before)or not _same_state(cert.root_state,state):fail('root_binding_mismatch')
  if type(cert.nodes[0].rank)is not int or cert.nodes[0].rank>rule_limit(session.compiled,'max_ply')-state.ply_count:fail('remaining_ply_guard')
  unrolled=check(0,state.position)
  if len(visited)!=len(cert.nodes):fail('unreachable_extra_nodes')
  # Strict ranks + injective repetition identities forbid within-strategy repeats.
  # Every future identity is visited at most once. The already-current root
  # cannot recur; every other identity must have room for that one occurrence.
  root_key=repetition_identity_key(state.position,session.compiled);past=dict(state.repetition_counts);limit=rule_limit(session.compiled,'repetition_limit')
  for identity in identities:
   if identity!=root_key and past.get(identity,0)>=limit-1:fail('prehistory_repetition_guard')
  b.poll();valid=True
 except _Interrupted:reason=b.reason
 except(ValueError,NotImplementedError,TypeError,AttributeError)as error:reason=str(error)
 finally:assert _same_state(session.state,state)and _same_state(session.to_record(),before)and session.result==result
 receipt=dict(verified=valid,reason=reason,nodes=b.nodes,edges=edges_checked,seconds=b.elapsed(),unrolled_tree_nodes=tree_counts.get(0),scope='QualifiedpositionDAG only; fullruleguard/rootbinding/rank/horizon/prehistory/identitychecks. Publiccanonicaledgeexecution, notprovercache.')
 return(receipt,positions)if return_positions else receipt


def prove_graph(session,*,target=None,max_nodes=8192,max_edges=65536,seconds=1.,max_depth=96,cancel=None,_clock=perf_counter):
 b=_Budget(max_nodes,seconds,cancel,_clock);target=session.state.position.side_to_move if target is None else target;positions=[];sessions=[];tokens={};children=[];parents=[];complete=[];rank=[];queue=deque();transitions=0;reason='exhausted_partial_graph';cert=None;status='UNKNOWN'
 before=session.to_record();state=session.state;result=session.result
 def add(position):
  token=position_token(position)
  if token in tokens:return tokens[token]
  if len(positions)>=max_nodes:raise ValueError('position_budget')
  b.poll();s=canonical(position,session.compiled);b.poll();i=len(positions);tokens[token]=i;positions.append(position);sessions.append(s);children.append([]);parents.append(set());complete.append(False);rank.append(0 if s.result.status is not SessionStatus.ONGOING and s.result.winner==target else None)
  if s.result.status is SessionStatus.ONGOING:queue.append(i)
  else:complete[i]=True
  return i
 def relax(index):
  updates=deque([index])
  while updates:
   b.poll();i=updates.popleft()
   if rank[i]is not None:continue
   if positions[i].side_to_move==target:
    won=[rank[j]for _,j in children[i]if rank[j]is not None]
    if not won:continue
    rank[i]=1+min(won)
   else:
    if not complete[i]or not children[i]or any(rank[j]is None for _,j in children[i]):continue
    rank[i]=1+max(rank[j]for _,j in children[i])
   updates.extend(parents[i])
 def certificate():
  ids={};nodes=[]
  def collect(i):
   b.poll()
   if i in ids:return ids[i]
   index=len(nodes);ids[i]=index;nodes.append(None);s=sessions[i]
   if rank[i]==0:node=GraphNode(0,terminal=s.result)
   else:
    edge=children[i]
    if positions[i].side_to_move==target:edge=[min((e for e in edge if rank[e[1]]is not None),key=lambda e:rank[e[1]])]
    ee=tuple((choice,collect(j))for choice,j in edge);node=GraphNode(rank[i],ee)
   nodes[index]=node;return index
  collect(0);return GraphCertificate(session.compiled.ruleset_fingerprint,before,state,target,tuple(nodes))
 try:
  b.poll();replay_bound(session);b.poll()
  if session.result.status is not SessionStatus.ONGOING:raise ValueError('actual_session_terminal')
  guard=scope_reason(session.compiled)
  if guard:raise ValueError(guard)
  if type(target)is not int or target not in(0,1)or type(max_depth)is not int or max_depth<0 or type(max_edges)is not int or max_edges<0:raise ValueError('invalid_limits_or_target')
  add(state.position)
  while queue and rank[0]is None:
   b.poll();i=queue.popleft();b.visit();s=sessions[i];legal=_ordered(s.legal_actions());b.poll()
   for action in legal:
    if transitions>=max_edges:raise ValueError('edge_budget')
    b.poll();child=copy(s);execute(child,SessionChoice('ACTION',action=action));transitions+=1;b.poll();j=add(child.state.position);children[i].append((SessionChoice('ACTION',action=action),j));parents[j].add(i);relax(i)
    if rank[0]is not None:break
   else:complete[i]=True;relax(i)
  if rank and rank[0]is not None:
   if rank[0]>max_depth:reason='depth_budget'
   elif rank[0]>rule_limit(session.compiled,'max_ply')-state.ply_count:reason='remaining_ply_guard'
   else:cert=certificate();b.poll();status='CANDIDATE_WIN_GRAPH';reason='requires_independent_graph_verification'
 except _Interrupted:reason=b.reason;cert=None
 except(ValueError,NotImplementedError)as error:reason=str(error);cert=None
 finally:assert _same_state(session.state,state)and _same_state(session.to_record(),before)and session.result==result
 return GraphResult(status,cert,reason,len(positions),b.nodes,transitions,b.elapsed(),rank[0]if rank else None)


class GraphStrategyCursor:
 def __init__(self,session,certificate,**limits):
  receipt,positions=verify_graph(session,certificate,return_positions=True,**limits)
  if not receipt['verified']:raise ValueError('graph_verification_'+receipt['reason'])
  self.certificate=certificate;self.receipt=receipt;self.positions=positions;self.index=0;self.record=session.to_record();self.state=session.state;self.result=session.result
 def bound(self,s):
  replay_bound(s)
  if not _same_state(s.to_record(),self.record)or not _same_state(s.state,self.state)or s.result!=self.result:raise ValueError('cursor_context_mismatch')
 def choose(self,s):
  self.bound(s);node=self.certificate.nodes[self.index]
  if node.rank==0:return None
  if s.state.position.side_to_move!=self.certificate.target:raise ValueError('not_target_turn')
  return node.edges[0][0]
 def observe(self,before,choice,after):
  self.bound(before);node=self.certificate.nodes[self.index];matches=[j for c,j in node.edges if _same_state(c,choice)]
  if len(matches)!=1:raise ValueError('choice_outside_graph')
  j=matches[0];expected=copy(before);execute(expected,choice)
  if not _same_state(expected.state,after.state)or not _same_state(expected.to_record(),after.to_record())or expected.result!=after.result or not _same_state(after.state.position,self.positions[j]):raise ValueError('graph_transition_mismatch')
  child=self.certificate.nodes[j]
  if child.rank>=node.rank:raise ValueError('nondecreasing_rank')
  if child.rank==0:
   if after.result.winner!=self.certificate.target:raise ValueError('actual_terminal_not_WIN')
  elif after.result.status is not SessionStatus.ONGOING:raise ValueError('unexpected_actual_terminal')
  self.index=j;self.record=after.to_record();self.state=after.state;self.result=after.result
 def commit(self,s,choice):
  self.bound(s)
  if not any(_same_state(c,choice)for c,_ in self.certificate.nodes[self.index].edges):raise ValueError('choice_outside_graph')
  before=copy(s);execute(s,choice);self.observe(before,choice,s);return s.result
