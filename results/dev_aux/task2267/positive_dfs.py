"""Opt-in bounded positive AND/OR iterative DFS, no table/price heuristic.
Repeated positions stop that branch as UNKNOWN, never DRAW/disproof.
Only independently checked rank-decreasing complete-defense candidates escape.
"""
from time import perf_counter
from copy import copy
from scripts.generic_win_proof import _Budget,_Interrupted,_ordered,_same_state
from scripts.generic_session_win_proof import SessionChoice,execute,replay_bound
from generic_chess.session.result import SessionStatus
from generic_chess.core.attacks import is_in_check
from results.dev_aux.task2179.graph import GraphNode,GraphCertificate,GraphResult,position_token
from results.dev_aux.task2199.semantic_graph import canonical,scope_reason,rule_limit

def prove_graph(session,*,target=None,max_nodes=8192,max_edges=65536,seconds=1.,max_depth=96,cancel=None,_clock=perf_counter):
 b=_Budget(max_nodes,seconds,cancel,_clock);before=session.to_record();state=session.state;result=session.result;target=state.position.side_to_move if target is None else target;known={};observed=set();visiting=set();transitions=0;reason='depth_budget_unknown';certificate=None;status='UNKNOWN';root=None
 def search(position,depth):
  nonlocal transitions
  b.poll();token=position_token(position)
  if token not in observed:
   if len(observed)>=max_nodes:raise ValueError('position_budget')
   observed.add(token)
  if token in known and known[token][1].rank<=depth:return token
  if token in visiting:return None
  b.visit();s=canonical(position,session.compiled);b.poll()
  if s.result.status is not SessionStatus.ONGOING:
   if s.result.winner==target:known[token]=(position,GraphNode(0,(),s.result));return token
   return None
  if depth<=0:return None
  visiting.add(token)
  try:
   children=[]
   for a in _ordered(s.legal_actions()):
    b.poll()
    if transitions>=max_edges:raise ValueError('edge_budget')
    child=copy(s);choice=SessionChoice('ACTION',action=a);execute(child,choice);transitions+=1;b.poll()
    # Cheap generic royal-check priority only AFTER full legal public transition.
    terminal=child.result.status is not SessionStatus.ONGOING
    priority=0 if terminal and child.result.winner==target else 3 if terminal else 1 if is_in_check(child.state.position,1-position.side_to_move,session.compiled)else 2
    children.append((priority,len(children),choice,child.state.position))
   children.sort(key=lambda x:x[:2]);proof=[]
   for _,__,choice,child in children:
    answer=search(child,depth-1)
    if answer is None:
     if position.side_to_move!=target:return None
    else:
     proof.append((choice,answer))
     if position.side_to_move==target:break
   if not proof:return None
   if position.side_to_move!=target and len(proof)!=len(children):return None
   rank=1+max(known[token2][1].rank for _,token2 in proof)
   if rank>depth:return None
   # A completed positive proof may be reused only with its proven depth bound.
   # Pending/cyclic/depth-limited failures are never cached as nonwins.
   known[token]=(position,GraphNode(rank,tuple(proof)));return token
  finally:visiting.remove(token)
 def collect(token,ids,nodes):
  b.poll()
  if token in ids:return ids[token]
  i=len(nodes);ids[token]=i;nodes.append(None);node=known[token][1];edges=tuple((choice,collect(ch,ids,nodes))for choice,ch in node.edges);nodes[i]=GraphNode(node.rank,edges,node.terminal);return i
 try:
  b.poll();replay_bound(session);b.poll();guard=scope_reason(session.compiled)
  if guard:raise ValueError(guard)
  if session.result.status is not SessionStatus.ONGOING:raise ValueError('actual_session_terminal')
  if type(target)is not int or target not in(0,1)or type(max_depth)is not int or max_depth<0 or type(max_edges)is not int or max_edges<0:raise ValueError('invalid_limits_or_target')
  horizon=min(max_depth,rule_limit(session.compiled,'max_ply')-state.ply_count)
  depths=list(range(1,horizon+1,2))
  if horizon and(not depths or depths[-1]!=horizon):depths.append(horizon)
  for depth in depths:
   root=search(state.position,depth)
   if root is not None:
    nodes=[];collect(root,{},nodes);certificate=GraphCertificate(session.compiled.ruleset_fingerprint,before,state,target,tuple(nodes));b.poll();status='CANDIDATE_WIN_GRAPH';reason='requires_independent_graph_verification';break
 except _Interrupted:reason=b.reason;certificate=None
 except(ValueError,NotImplementedError)as error:reason=str(error);certificate=None
 finally:assert _same_state(session.state,state)and _same_state(session.to_record(),before)and session.result==result
 return GraphResult(status,certificate,reason,len(observed),b.nodes,transitions,b.elapsed(),None if root is None else known[root][1].rank)
