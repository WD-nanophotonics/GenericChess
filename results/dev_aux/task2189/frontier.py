"""Opt-in bounded most-proving heuristic over a guarded partial position graph.

Derived from2179 prove_graph; sound WIN/rank propagation unchanged. Estimates
ONLY order future expansion; they NEVER prove/refute WDL. Cyclic estimates are
unknown, not draw. Per-selection finite work falls back to the existing FIFO.
This is not DFPN, TCA or a cycle-correct proof-number counting claim.
"""
from dataclasses import dataclass
from collections import deque
from copy import copy
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute,replay_bound
from scripts.generic_win_proof import _Budget,_Interrupted,_ordered,_same_state
from results.dev_aux.task2179.graph import (GraphResult,GraphNode,GraphCertificate,
 scope_reason,position_token,canonical)

@dataclass(frozen=True)
class FrontierGraphResult(GraphResult):
 visits:int=0
 fallbacks:int=0
 cycles:int=0

class SelectionLimit(Exception):pass

def select_frontier(queue,positions,sessions,children,complete,rank,target,b,max_depth,stats):
 # Finite acyclic traversal supplies a heuristic. Memo is per selection, so
 # path-dependent cycle truncation affects ordering only and is discarded.
 memo={};active=set();visits=0;inf=float('inf');ceiling=8192
 def walk(i,depth):
  nonlocal visits
  b.poll();visits+=1;stats['visits']+=1
  if visits>ceiling:raise SelectionLimit
  if rank[i]is not None:return 0,inf,None
  if sessions[i].result.status is not SessionStatus.ONGOING:return inf,0,None
  if i in active or depth>=max_depth:
   stats['cycles']+=i in active;return 1,1,None
  if i in memo:return memo[i]
  if not complete[i]:return 1,1,i
  active.add(i);values=[walk(j,depth+1)for _,j in children[i]];active.remove(i)
  candidates=[(n,v)for n,v in enumerate(values)if v[2]is not None]
  own=positions[i].side_to_move==target
  if not values:value=(inf,0,None)if own else(1,1,None)
  else:
   pn=min(v[0]for v in values)if own else min(ceiling,sum(v[0]for v in values))
   dn=min(ceiling,sum(v[1]for v in values))if own else min(v[1]for v in values)
   frontier=None if not candidates else min(candidates,key=lambda nv:(nv[1][0 if own else 1],nv[0]))[1][2]
   value=pn,dn,frontier
  memo[i]=value;return value
 try:
  _,_,frontier=walk(0,0)
  if frontier is not None and frontier in queue:return frontier
 except SelectionLimit:pass
 stats['fallbacks']+=1;return queue[0]

def prove_frontier_graph(session,*,target=None,max_nodes=8192,max_edges=65536,seconds=1.,max_depth=96,cancel=None,_clock=perf_counter):
 b=_Budget(max_nodes,seconds,cancel,_clock);target=session.state.position.side_to_move if target is None else target;positions=[];sessions=[];tokens={};children=[];parents=[];complete=[];rank=[];queue=deque();transitions=0;reason='exhausted_partial_graph';cert=None;status='UNKNOWN'
 selection_stats=dict(visits=0,fallbacks=0,cycles=0)
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
   b.poll();i=select_frontier(queue,positions,sessions,children,complete,rank,target,b,max_depth,selection_stats);queue.remove(i);b.visit();s=sessions[i];legal=_ordered(s.legal_actions());b.poll()
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
 return FrontierGraphResult(status,cert,reason,len(positions),b.nodes,transitions,b.elapsed(),rank[0]if rank else None,**selection_stats)
