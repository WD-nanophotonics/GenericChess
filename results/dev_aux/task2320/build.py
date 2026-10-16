"""Untrusted closed-graph refutation discovery, optional explicit reference assist."""
from pathlib import Path
from copy import copy
from collections import deque,defaultdict
from time import perf_counter
import hashlib
from generic_chess.session.result import SessionStatus
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_win_proof import SessionChoice,execute,replay_bound
from scripts.generic_win_proof import _Budget,_Interrupted,_ordered,_same_state
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2199.semantic_graph import canonical,scope_reason
from results.dev_aux.task2320.refutation import RefutationNode,RefutationCertificate
from results.dev_aux.task2205.consume import action

def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def encode(cert):return dict(target=cert.target,nodes=[dict(edges=[dict(action=action_to_dict(c.action),child=j)for c,j in n.edges])for n in cert.nodes])
def decode(s,data):return RefutationCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,data['target'],tuple(RefutationNode(tuple((SessionChoice('ACTION',action=action(e['action'],s.compiled.ruleset_fingerprint)),e['child'])for e in n['edges']))for n in data['nodes']))
def discover(session,*,max_nodes=65536,max_edges=524288,seconds=42.,cancel=None,guide=None):
 b=_Budget(max_nodes,seconds,cancel);positions=[session.state.position];indices={repr(positions[0]):0};edges=[];terminals=[];total_edges=0;reason='complete';certificate=None;target=session.state.position.side_to_move;mode='GENERIC_FULL_REACHABILITY'if guide is None else'REFERENCE_ASSISTED_DEFENDER_STRATEGY';began=perf_counter()
 try:
  replay_bound(session);b.poll()
  if scope_reason(session.compiled)is not None:raise ValueError(scope_reason(session.compiled))
  if session.result.status is not SessionStatus.ONGOING:raise ValueError('actual_root_terminal')
  cursor=0
  while cursor<len(positions):
   b.visit();s=canonical(positions[cursor],session.compiled);terminal=s.result.status is not SessionStatus.ONGOING;terminals.append(s.result if terminal else None);choices=[]if terminal else[SessionChoice('ACTION',action=a)for a in _ordered(s.legal_actions())]
   if guide is not None and not terminal:
    row=guide.rows[key(actor_state(s.state))]
    if(s.state.position.side_to_move==target and row['label']=='WIN')or(s.state.position.side_to_move!=target and row['label']=='LOSS'):raise ValueError('reference_cannot_refute_targetWIN')
    if s.state.position.side_to_move!=target:
     # Reference child value is from the next mover (=target). Preserve a
     # nonpositive target value. Selection is explicit reference construction.
     eligible={e['action']for e in row['actions']if e['child_value']<=0};choices=[ch for ch in choices if uci(ch.action)in eligible]
     if not choices:raise ValueError('reference_no_safe_defense')
     choices=[min(choices,key=lambda ch:hashlib.sha256(repr(ch).encode()).hexdigest())]
   node=[]
   for ch in choices:
    b.poll();child=copy(s);execute(child,ch);token=repr(child.state.position)
    if token not in indices:
     if len(positions)>=max_nodes:raise _Interrupted('position_cap')
     indices[token]=len(positions);positions.append(child.state.position)
    j=indices[token];assert _same_state(positions[j],child.state.position);node.append((ch,j));total_edges+=1
    if total_edges>max_edges:raise _Interrupted('edge_cap')
   edges.append(tuple(node));cursor+=1
  # Solve the finite reachability attractor of target-win terminals. Its
  # complement is a safety trap; it is NOT necessarily an actual DRAW label.
  win={i for i,r in enumerate(terminals)if r is not None and r.winner==target};queue=deque(win);pred=defaultdict(set);pending=[len(e)for e in edges]
  for i,ee in enumerate(edges):
   for ch,j in ee:pred[j].add(i)
  while queue:
   b.poll();j=queue.popleft()
   for i in pred[j]:
    if i in win:continue
    # Distinct actions may share a child: count those edges, not just one.
    pending[i]-=sum(k==j for ch,k in edges[i])
    if positions[i].side_to_move==target or pending[i]==0:win.add(i);queue.append(i)
  if 0 in win:reason='target_in_reachability_attractor_UNRESOLVED_ACTUAL_HISTORY'
  else:
   mapping={0:0};todo=deque([0]);nodes=[]
   while todo:
    b.poll();i=todo.popleft();ee=edges[i]
    if terminals[i]is None and positions[i].side_to_move!=target:ee=(next(e for e in ee if e[1]not in win),)
    assert all(j not in win for ch,j in ee);new=[]
    for ch,j in ee:
     if j not in mapping:mapping[j]=len(mapping);todo.append(j)
     new.append((ch,mapping[j]))
    assert len(nodes)==mapping[i];nodes.append(RefutationNode(tuple(new)))
   certificate=RefutationCertificate(session.compiled.ruleset_fingerprint,session.to_record(),session.state,target,tuple(nodes));reason='CANDIDATE_NO_FORCED_WIN_REQUIRES_INDEPENDENT_CHECK'
 except _Interrupted as e:reason=b.reason or str(e)
 except(ValueError,KeyError)as e:reason=str(e)
 return dict(certificate=certificate,mode=mode,reason=reason,expanded=b.nodes,positions=len(positions),edges=total_edges,closed=len(edges)==len(positions),seconds=perf_counter()-began)
