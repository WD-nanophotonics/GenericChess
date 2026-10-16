"""Core canonicalization must preserve semantic fields and actual execution."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import importlib.util,json,sys,pytest
sys.path.insert(0,str(Path('tests').resolve()));sys.path.insert(0,str(Path('tests/development').resolve()))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleAuxState,RuleActionEffect,RuleSquareRef,RuleInvariant
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.identity import repetition_identity_key
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_win_proof import _same_state,_ordered
import results.dev_aux.task2180.test_graph as old
from results.dev_aux.task2191.semantic_graph import canonical,scope_reason,prove_graph,verify_graph,GraphStrategyCursor

# Existing baseline counterexamples exercise the new canonical constructor,
# independent verification, and real actual-session cursor unchanged in meaning.
@pytest.fixture(autouse=True)
def new_graph_entries(monkeypatch):
 monkeypatch.setattr(old,'prove_graph',prove_graph);monkeypatch.setattr(old,'verify_graph',verify_graph);monkeypatch.setattr(old,'GraphStrategyCursor',GraphStrategyCursor)

teacher=old.teacher
for name in dir(old):
 if name.startswith('test_')and name!='test_declarations_perpetual_and_semantic_scope_fail_closed':globals()[name]=getattr(old,name)

def aux_session():
 spec=importlib.util.spec_from_file_location('auxidentity2191',Path('tests/product/test_runtime_aux_identity.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return GameSession(mod._compiled(initial=0,value=1))

def semantic_mate():
 rs=krk_ruleset(4)
 action=RuleSemanticAction(name='aux_step',type_ids=('R',),geometry=RuleGeometrySpec(kind='leap',offset=(1,0)),target_relation='empty',composition='augment',aux_state=(RuleAuxState('flag','bool','global','persistent',0),),effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),RuleActionEffect('set_bool',slot_name='flag',value=1)),invariants=(RuleInvariant('own_anchor_safe'),))
 rs=replace(rs,semantic_actions=(action,));board=[None]*16
 for i,p in((1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(8,Piece(0,'R','R'))):board[i]=p
 return GameSession(compile_semantic_ruleset(replace(rs,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)))))

def test_semantic_public_mate_certificate_and_actual_cursor():
 s=semantic_mate();assert scope_reason(s.compiled)is None
 r=prove_graph(s,max_nodes=512,seconds=3.);assert r.certificate is not None
 assert isinstance(r.certificate.nodes[0].edges[0][0].action,SemanticBoardMove)
 assert verify_graph(s,r.certificate,seconds=3.)['verified']
 cur=GraphStrategyCursor(s,r.certificate,seconds=3.);moves=0
 while s.result.status is SessionStatus.ONGOING:
  c=cur.choose(s)if s.state.position.side_to_move==0 else cur.certificate.nodes[cur.index].edges[-1][0];cur.commit(s,c);moves+=1
 assert s.result.winner==0 and moves>=1
 replay=GameSession.replay(s.compiled,s.to_record());assert _same_state(replay.state,s.state)and replay.result==s.result

def test_semantic_actual_aux_write_keeps_side_and_value_when_canonicalized():
 s=aux_session();a=next(a for a in s.legal_actions()if isinstance(a,SemanticBoardMove)and a.pattern_id.startswith('sem_'));s.submit(a)
 assert s.state.position.side_to_move==1 and s.state.position.aux_state
 c=canonical(s.state.position,s.compiled)
 assert _same_state(c.state.position,s.state.position)
 assert set(c.legal_actions())==set(s.legal_actions())and c.result==s.result
 # A fresh public GameSession made from board rows alone resets these fields.
 rows=tuple(tuple(s.state.position.board[i:i+5])for i in range(0,25,5))
 wrong=GameSession(replace(s.compiled,support=replace(s.compiled.support,initial_position=rows,initial_setup_options={})))
 assert not _same_state(wrong.state.position,s.state.position)
 assert wrong.state.position.side_to_move==0 and not wrong.state.position.aux_state

def test_full_typed_position_hands_base_aux_are_not_projected_away():
 s=aux_session();p=replace(s.state.position,side_to_move=1,hands=(Hands((('A',1),)),Hands.empty()),aux_state=(((0,-1),True),),board_width=5,board_height=5)
 c=canonical(p,s.compiled);assert _same_state(c.state.position,p)
 assert type(dict(c.state.position.aux_state)[(0,-1)])is bool

def test_semantic_history_policies_and_unqualified_features_fail_closed():
 s=aux_session();c=s.compiled
 for support in(replace(c.support,repetition_policy='continuous_check_loss'),replace(c.support,repetition_limit=1),replace(c.support,max_ply=0)):
  assert scope_reason(replace(c,support=support))is not None
 for name,fixture in __import__('results.dev_aux.task2168.panel',fromlist=['fixtures']).fixtures():
  if name in('winning_claim','restart_claim','pass_draw','played_perpetual'):assert scope_reason(fixture.compiled)is not None

def test_cancelled_semantic_proof_is_unknown_and_root_immutable():
 s=semantic_mate();before=s.to_record();state=s.state;r=prove_graph(s,cancel=lambda:True,seconds=1.)
 assert r.status=='UNKNOWN'and r.certificate is None and r.reason=='cancelled'
 assert _same_state(state,s.state)and before==s.to_record()


def test_semantic_graph_unrolls_to_independent_actual_history_tree_verifier():
 from scripts.generic_session_win_proof import SessionProofNode,SessionWinCertificate,verify_session_certificate,SessionStrategyCursor
 s=semantic_mate();r=prove_graph(s,max_nodes=512,seconds=3.);cert=r.certificate;assert cert is not None
 def unroll(i):
  node=cert.nodes[i]
  return SessionProofNode(node.rank,tuple((c,unroll(j))for c,j in node.edges),node.terminal)
 tree=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,cert.target,unroll(0))
 receipt=verify_session_certificate(s,tree,max_nodes=16384,seconds=3.);assert receipt['verified']
 actual=copy(s);cur=SessionStrategyCursor(actual,tree,seconds=3.)
 while actual.result.status is SessionStatus.ONGOING:
  c=cur.choose(actual)if actual.state.position.side_to_move==tree.target else cur.node.edges[-1][0];cur.commit(actual,c)
 assert actual.result.winner==tree.target


def test_s4_and_transition_ir_are_not_accidentally_admitted():
 from rule_semantics_ir_fixtures import uchifuzume_ruleset
 c=compile_semantic_ruleset(uchifuzume_ruleset())
 assert scope_reason(c)=='unsupported_semantic_postcondition'
 from rule_semantics_ir_fixtures import castling_ruleset
 c=compile_semantic_ruleset(castling_ruleset())
 assert scope_reason(c)=='unsupported_semantic_trigger'


def test_real_executable_semantic_adapter_uses_support_not_legacy_metadata():
 from generic_chess.rules.execution import ExecutableSemanticRuleset
 from results.dev_aux.task2191.semantic_graph import rule_limit
 base=semantic_mate().compiled
 # Real execution facade with no legacy inspection object: proof must consume
 # semantic IR/support authority, never geometry-shaped compatibility metadata.
 c=ExecutableSemanticRuleset(ir=base.ir,support=base.support,_legacy_compiled=None)
 s=GameSession(c);assert scope_reason(c)is None and rule_limit(c,'max_ply')==c.support.max_ply
 r=prove_graph(s,max_nodes=512,seconds=3.);assert r.certificate is not None and verify_graph(s,r.certificate,seconds=3.)['verified']
 small=replace(c,support=replace(c.support,max_ply=1))
 assert rule_limit(small,'max_ply')==1
 assert _same_state(canonical(s.state.position,c).state.position,s.state.position)
