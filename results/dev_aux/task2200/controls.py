"""S4 forbidden mate and trigger controls through actual public execution."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import sys,json,hashlib,time
sys.path.insert(0,str(Path('tests').resolve()));sys.path.insert(0,str(Path('tests/development').resolve()))
from rule_semantics_ir_fixtures import _semantic_ruleset,weird_rulesets,castling_ruleset
from conftest import T
from generic_chess.core.pieces import Piece
from generic_chess.core.movement import LeapAtom
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_win_proof import SessionChoice,SessionProofNode,SessionWinCertificate,verify_session_certificate
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2199.semantic_graph import canonical,scope_reason,prove_graph,verify_graph,GraphCertificate,GraphNode,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2200')

def square(a):return((a.from_square.file,a.from_square.rank),(a.to_square.file,a.to_square.rank))

def mate_rules():
 rule=weird_rulesets()[-1];n=T('N',*(LeapAtom(d)for d in((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1))))
 rows=[]
 for knight in(11,12):
  b=[None]*16
  for i,p in((1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(10,Piece(0,'R','R')),(knight,Piece(1,'N','N'))):b[i]=p
  rows.append(tuple(tuple(b[i:i+4])for i in range(0,16,4)))
 rs=_semantic_ruleset(rule.piece_types+(n,),rule.semantic_actions,n=4,rows=rows[0]);return replace(rs,initial_setup_options=(RuleInitialSetupOption('quiet_mate',rows[1]),))

def unroll(s,cert):
 def node(i):
  n=cert.nodes[i];return SessionProofNode(n.rank,tuple((c,node(j))for c,j in n.edges),n.terminal)
 return SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,cert.target,node(0))

def run():
 if(OUT/'started.json').exists():raise RuntimeError('single120cap neverrestart')
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=120)),encoding='utf-8')
 def cancel():stop();return time.perf_counter()-began>=120
 rs=mate_rules();c=compile_ruleset_for_execution(rs);forbidden=GameSession(c);allowed=GameSession(c,initial_setup_key='quiet_mate');assert scope_reason(c)is None
 assert not any(square(a)==((2,2),(3,2))for a in forbidden.legal_actions())
 chosen=next(a for a in allowed.legal_actions()if square(a)==((2,2),(3,2)));actual=copy(allowed);actual.submit(chosen);assert actual.result.winner==0
 r=prove_graph(allowed,max_nodes=1024,seconds=2.,max_depth=8,cancel=cancel);assert r.certificate is not None
 v=verify_graph(allowed,r.certificate,seconds=2.,cancel=cancel);assert v['verified']
 tree=unroll(allowed,r.certificate);independent=verify_session_certificate(allowed,tree,seconds=2.,cancel=cancel);assert independent['verified']
 cur=GraphStrategyCursor(allowed,r.certificate,seconds=2.,cancel=cancel);played=copy(allowed)
 while played.result.status is SessionStatus.ONGOING:
  choice=cur.choose(played)if played.state.position.side_to_move==0 else cur.certificate.nodes[cur.index].edges[-1][0];cur.commit(played,choice)
 assert played.result.winner==0
 # Geometrically identical capture with the S4-specific capture action is
 # illegal. Forge a one-edge proof and ensure independent legality rejects.
 plain=replace(rs,semantic_actions=tuple(replace(a,postconditions=())for a in rs.semantic_actions))
 geometry=GameSession(compile_ruleset_for_execution(plain))
 public=next(a for a in geometry.legal_actions()if square(a)==((2,2),(3,2)))
 geometry.submit(public);assert geometry.result.winner==0
 candidate=copy(forbidden)
 try:candidate.submit(public);raise AssertionError('S4illegal capture accepted')
 except __import__('generic_chess.core.errors',fromlist=['IllegalActionError']).IllegalActionError:pass
 child=GraphNode(0,terminal=actual.result);forgery=GraphCertificate(c.ruleset_fingerprint,forbidden.to_record(),forbidden.state,0,(GraphNode(1,((SessionChoice('ACTION',action=public),1),)),child));bad=verify_graph(forbidden,forgery,seconds=2.,cancel=cancel);assert not bad['verified']
 # Existing castling trigger fixture, all frontiers before/after both action types.
 castle=GameSession(compile_ruleset_for_execution(castling_ruleset()));assert scope_reason(castle.compiled)is None;branches=[('root',castle)]
 for label,action in(('castle',next(a for a in castle.legal_actions()if a.pattern_id.startswith('sem_'))),('king_leaves',next(a for a in castle.legal_actions()if a.from_square.file==4 and a.from_square.rank==0 and not a.pattern_id.startswith('sem_')))):
  nxt=copy(castle);nxt.submit(action);branches.append((label,nxt));assert dict(nxt.state.position.aux_state)[(0,0)]==0
 edges=0;branch_rows=[]
 for label,s in branches:
  canon=canonical(s.state.position,s.compiled);assert _same_state(s.state.position,canon.state.position)and s.legal_actions()==canon.legal_actions()
  for a in s.legal_actions():
   if cancel():raise TimeoutError('globalcap')
   child=copy(s);child.submit(a);other=copy(canon);other.submit(a);assert _same_state(child.state.position,other.state.position)and child.result==other.result
   assert _same_state(GameSession.replay(s.compiled,child.to_record()).state,child.state);edges+=1
  branch_rows.append(dict(name=label,record=json.loads(serialize_game_record(s.to_record())),state_repr=repr(s.state),legal_actions=[action_to_dict(a)for a in s.legal_actions()]))
 (OUT/'no-S4-control-rules.json').write_text(serialize_ruleset(plain),encoding='utf-8');(OUT/'mate-rules.json').write_text(serialize_ruleset(rs),encoding='utf-8');(OUT/'trigger-rules.json').write_text(serialize_ruleset(castling_ruleset()),encoding='utf-8')
 result=dict(status='PASS_ACTUAL_S4_AND_TRIGGER_CONTROLS',S4_allowed_actual_winner=actual.result.winner,no_S4_capture_actual_winner=geometry.result.winner,graph_verification=v,independent_fullhistory_tree_verification=independent,forbidden_rejection=bad,actual_proved_record=json.loads(serialize_game_record(played.to_record())),trigger_branches=branch_rows,trigger_edges=edges,seconds=time.perf_counter()-began,scope='Scopefeasibility forfinitepositivecertificate lifting only; actual S4 rejection andtrigger rights. No globalSessionquotient/WDL/newlearning/defaultclaim.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:result[k]for k in('status','trigger_edges','seconds')}))
if __name__=='__main__':run()
