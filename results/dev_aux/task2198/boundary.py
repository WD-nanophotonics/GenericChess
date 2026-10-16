"""Exact nonterminal repetition-boundary control requested by advisor75."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,time
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleInvariant
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2191.semantic_graph import canonical,verify_graph,GraphNode,GraphCertificate,position_token,rule_limit
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2198')

def name(a):return chr(97+a.from_square.file)+str(a.from_square.rank+1)+chr(97+a.to_square.file)+str(a.to_square.rank+1)

def propose(s,teacher,target,cancel):
 ids={};nodes=[]
 def visit(p):
  cancel();token=position_token(p)
  if token in ids:return ids[token]
  assert len(nodes)<8192;i=len(nodes);ids[token]=i;nodes.append(None);c=canonical(p,s.compiled);r=teacher.rows[teacher.key(actor_state(c.state))]
  if r['rank']==0:n=GraphNode(0,terminal=c.result)
  else:
   legal=c.legal_actions();selected=[next(a for a in legal if name(a)==r['winning_action'])]if p.side_to_move==target else legal;edges=[]
   for a in selected:
    child=copy(c);choice=SessionChoice('ACTION',action=a);execute(child,choice);j=visit(child.state.position);edges.append((choice,j))
   n=GraphNode(r['rank'],tuple(edges))
  nodes[i]=n;return i
 visit(s.state.position);return GraphCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,target,tuple(nodes))

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single60cap neverrestart')
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(cap=60)),encoding='utf-8')
 def cancel():stop();assert time.perf_counter()-began<60;return False
 old=json.loads(Path('results/dev_aux/task2101/result.json').read_text());base=deserialize_ruleset(Path('results/dev_aux/task2101/rules.json').read_text());record=deserialize_game_record(json.dumps(old['root_record']));teacher=CanonicalTeacher('results/dev_aux/task2171','results/dev_aux/task2172','results/dev_aux/task2176');rows=[]
 action=RuleSemanticAction(name='same_king_step',type_ids=('K',),geometry=RuleGeometrySpec(kind='leap',offset=(1,0)),target_relation='empty',composition='augment',effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),),invariants=(RuleInvariant('own_anchor_safe'),))
 for label,rs in(('BASELINE',base),('SEMANTIC',replace(base,semantic_actions=(action,)))):
  cancel();c=compile_ruleset_for_execution(rs);s=GameSession(c)
  for a in record.actions:
   candidates=[b for b in s.legal_actions()if name(b)==name(a)];assert candidates;s.submit(candidates[0])
  assert s.result.status is SessionStatus.ONGOING
  cert=propose(s,teacher,old['target'],cancel);first=cert.nodes[0].edges[0][0];future=copy(s);execute(future,first);key=repetition_identity_key(future.state.position,c);past=dict(s.state.repetition_counts).get(key,0);fresh=canonical(future.state.position,c)
  assert past==rule_limit(c,'repetition_limit')-1 and future.result.status is SessionStatus.REPETITION and fresh.result.status is SessionStatus.ONGOING
  v=verify_graph(s,cert,seconds=3.,cancel=cancel);assert not v['verified']and v['reason']=='prehistory_repetition_guard'
  rows.append(dict(arm=label,ruleset_fingerprint=c.ruleset_fingerprint,root_record=json.loads(serialize_game_record(s.to_record())),first_action=action_to_dict(first.action),future_record=json.loads(serialize_game_record(future.to_record())),future_actual_status=future.result.status.value,future_canonical_status=fresh.result.status.value,future_past_count=past,limit=rule_limit(c,'repetition_limit'),verification=v,proposal_nodes=len(cert.nodes)))
  (OUT/(label.lower()+'-rules.json')).write_text(serialize_ruleset(rs),encoding='utf-8')
 result=dict(status='PASS_ACTUAL_NONTERMINAL_REPETITION_BOUNDARY_BOTH_EXECUTORS',rows=rows,seconds=time.perf_counter()-began,new_search_or_graph_or_fit=0,scope='Finite positive-certificate lifting, not unconditional Sessionquotient. Allcounts derivedfromactualpublicrecord; bothverifiers reject BEFOREcursor. Mate priority not misused. Tableonly proposes existingpositionstrategy, noactualhistoryWDLreward.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:result[k]for k in('status','seconds','new_search_or_graph_or_fit')}))
if __name__=='__main__':run()
