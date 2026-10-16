"""Bounded incremental ordering estimates, never WIN/refutation authority.

Actual observed premise: whole-graph heuristic recomputes millions of selection
visits. Limit estimates and traversal to128 work units each per selection;
96maximum proof-depth plus32 bookkeeping margin, chosen before new outcomes.
Cycles and nonconverged estimates affect order only. FIFO remains a fallback.
Guarded true-rank propagation and original independent verifier are unchanged.
"""
from dataclasses import dataclass
from collections import deque
from copy import copy
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute,replay_bound
from scripts.generic_win_proof import _Budget,_Interrupted,_ordered,_same_state
from results.dev_aux.task2179.graph import GraphResult,GraphNode,GraphCertificate,scope_reason,position_token,canonical

@dataclass(frozen=True)
class IncrementalGraphResult(GraphResult):
 visits:int=0
 fallbacks:int=0
 cycles:int=0
 updates:int=0

class SelectionLimit(Exception):pass

def select_frontier(queue,positions,sessions,children,parents,complete,rank,target,b,max_depth,stats,cache):
 ceiling=8193;scores=cache['scores'];pending=deque([]if cache['last']is None else[cache['last']]);updates=0
 def value(i):
  if rank[i]is not None:return(0,ceiling)
  if sessions[i].result.status is not SessionStatus.ONGOING:return(ceiling,0)
  return scores.get(i,(1,1))
 # Bounded local propagation. No convergence or cycle-correct PN claim;
 # actual WIN always comes exclusively from the original rank induction.
 while pending and updates<128:
  b.poll();i=pending.popleft();updates+=1;stats['updates']+=1
  if rank[i]is not None or sessions[i].result.status is not SessionStatus.ONGOING:new=value(i)
  elif not complete[i]or not children[i]:new=(1,1)
  else:
   vv=[]
   for _,j in children[i]:
    if updates>=128:break
    b.poll();updates+=1;stats['updates']+=1;vv.append(value(j))
   if len(vv)!=len(children[i]):break
   new=(min(x[0]for x in vv),min(ceiling,sum(x[1]for x in vv)))if positions[i].side_to_move==target else(min(ceiling,sum(x[0]for x in vv)),min(x[1]for x in vv))
  if scores.get(i)!=(new):
   scores[i]=new
   for parent in sorted(parents[i]):
    if updates>=128:break
    b.poll();updates+=1;stats['updates']+=1;pending.append(parent)
 visits=0;active=set()
 def step():
  nonlocal visits
  if visits>=128:raise SelectionLimit
  b.poll();visits+=1;stats['visits']+=1
 def walk(i,depth):
  step()
  if rank[i]is not None or sessions[i].result.status is not SessionStatus.ONGOING:return None
  if i in active:stats['cycles']+=1;return None
  if depth>=max_depth:return None
  if not complete[i]:return i
  active.add(i);candidates=[];own=positions[i].side_to_move==target
  for n,(_,j)in enumerate(children[i]):
   step()
   if j in active:stats['cycles']+=1;continue
   if rank[j]is None and sessions[j].result.status is SessionStatus.ONGOING:candidates.append((value(j)[0 if own else 1],n,j))
  for _,_,j in sorted(candidates):
   found=walk(j,depth+1)
   if found is not None:active.remove(i);return found
  active.remove(i);return None
 try:chosen=walk(0,0)
 except SelectionLimit:chosen=None
 if chosen is None or chosen not in queue:stats['fallbacks']+=1;chosen=queue[0]
 cache['last']=chosen;return chosen

def prove_incremental_graph(session,*,target=None,max_nodes=8192,max_edges=65536,seconds=1.,max_depth=96,cancel=None,_clock=perf_counter):
 b=_Budget(max_nodes,seconds,cancel,_clock);target=session.state.position.side_to_move if target is None else target;positions=[];sessions=[];tokens={};children=[];parents=[];complete=[];rank=[];queue=deque();transitions=0;reason='exhausted_partial_graph';cert=None;status='UNKNOWN'
 selection_stats=dict(visits=0,fallbacks=0,cycles=0,updates=0);selector_cache=dict(scores={},last=None)
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
   b.poll();i=select_frontier(queue,positions,sessions,children,parents,complete,rank,target,b,max_depth,selection_stats,selector_cache);queue.remove(i);b.visit();s=sessions[i];legal=_ordered(s.legal_actions());b.poll()
   for action in legal:
    if transitions>=max_edges:raise ValueError('edge_budget')
    b.poll();child=copy(s);execute(child,SessionChoice('ACTION',action=action));transitions+=1;b.poll();j=add(child.state.position);children[i].append((SessionChoice('ACTION',action=action),j));parents[j].add(i);relax(i)
    if rank[0]is not None:break
   else:complete[i]=True;relax(i)
  if rank and rank[0]is not None:
   if rank[0]>max_depth:reason='depth_budget'
   elif rank[0]>session.compiled.max_ply-state.ply_count:reason='remaining_ply_guard'
   else:cert=certificate();b.poll();status='CANDIDATE_WIN_GRAPH';reason='requires_independent_graph_verification'
 except _Interrupted:reason=b.reason;cert=None
 except(ValueError,NotImplementedError)as error:reason=str(error);cert=None
 finally:assert _same_state(session.state,state)and _same_state(session.to_record(),before)and session.result==result
 return IncrementalGraphResult(status,cert,reason,len(positions),b.nodes,transitions,b.elapsed(),rank[0]if rank else None,**selection_stats)

