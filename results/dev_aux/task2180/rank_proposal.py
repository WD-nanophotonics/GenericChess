"""Optional positional table proposal for graph-verifier diagnostics ONLY.

Teacher rows propose edges/ranks; independent verifier never trusts them.
Not a no-table proof algorithm or an actual-history WDL reward accessor.
"""
from results.dev_aux.task2179.graph import GraphCertificate,GraphNode,canonical,position_token
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_proof_rnb_bridge import actor_state,uci
from copy import copy
from scripts.generic_win_proof import _Budget
from time import perf_counter

def propose(session,teacher,target,*,max_nodes=8192,seconds=3.,cancel=None,_clock=perf_counter):
 budget=_Budget(max_nodes,seconds,cancel,_clock);nodes=[];ids={}
 def visit(position):
  budget.poll();token=position_token(position)
  if token in ids:return ids[token]
  budget.visit();i=len(nodes);ids[token]=i;nodes.append(None);s=canonical(position,session.compiled);row=teacher.rows[teacher.key(actor_state(s.state))]
  if row['rank']==0:node=GraphNode(0,terminal=s.result)
  else:
   legal={uci(a):a for a in s.legal_actions()};names=[row['winning_action']]if position.side_to_move==target else sorted(legal);edges=[]
   for name in names:
    choice=SessionChoice('ACTION',action=legal[name]);child=copy(s);execute(child,choice);budget.poll();edges.append((choice,visit(child.state.position)))
   node=GraphNode(row['rank'],tuple(edges))
  nodes[i]=node;return i
 visit(session.state.position);return GraphCertificate(session.compiled.ruleset_fingerprint,session.to_record(),session.state,target,tuple(nodes))
