"""Actual S4 and trigger proof authority plus retained full-history regressions."""
import pytest
from dataclasses import replace
from copy import copy
import results.dev_aux.task2191.test_semantic_graph as prior
import results.dev_aux.task2180.test_graph as base_tests
from results.dev_aux.task2199 import semantic_graph as graph
from results.dev_aux.task2200.controls import mate_rules,unroll,square
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleAuxState,RuleTransitionTrigger,RuleSquareRef
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import verify_session_certificate

teacher=prior.teacher
for name in dir(prior):
 if name.startswith('test_')and name!='test_s4_and_transition_ir_are_not_accidentally_admitted':globals()[name]=getattr(prior,name)

@pytest.fixture(autouse=True)
def use_full_semantic_scope(monkeypatch):
 for module in(prior,base_tests):
  for name in('canonical','scope_reason','prove_graph','verify_graph','GraphStrategyCursor'):
   if hasattr(module,name):monkeypatch.setattr(module,name,getattr(graph,name))

def test_real_S4_forbidden_capture_and_allowed_quiet_mate():
 c=compile_ruleset_for_execution(mate_rules());no=GameSession(c);yes=GameSession(c,initial_setup_key='quiet_mate')
 assert graph.scope_reason(c)is None
 assert not any(square(a)==((2,2),(3,2))for a in no.legal_actions())
 r=graph.prove_graph(yes,max_nodes=1024,seconds=2.,max_depth=8);assert r.certificate is not None
 assert graph.verify_graph(yes,r.certificate,seconds=2.)['verified']
 assert verify_session_certificate(yes,unroll(yes,r.certificate),seconds=2.)['verified']

def test_actual_trigger_is_preserved_in_proved_terminal_position():
 rs=mate_rules();a=rs.semantic_actions[0]
 a=replace(a,aux_state=(RuleAuxState('right','bool','per_owner','persistent',1),),triggers=(RuleTransitionTrigger('right','piece_leaves_square',RuleSquareRef('fixed',square=(2,2),owner_relative=False),'self'),))
 c=compile_ruleset_for_execution(replace(rs,semantic_actions=(a,)));s=GameSession(c,initial_setup_key='quiet_mate');assert graph.scope_reason(c)is None and c.ir.triggers
 r=graph.prove_graph(s,max_nodes=1024,seconds=2.,max_depth=8);assert r.certificate is not None
 assert graph.verify_graph(s,r.certificate,seconds=2.)['verified']and verify_session_certificate(s,unroll(s,r.certificate),seconds=2.)['verified']
 cur=graph.GraphStrategyCursor(s,r.certificate,seconds=2.);actual=copy(s)
 while actual.result.status is SessionStatus.ONGOING:
  choice=cur.choose(actual)if actual.state.position.side_to_move==0 else cur.certificate.nodes[cur.index].edges[-1][0];cur.commit(actual,choice)
 assert actual.result.winner==0 and dict(actual.state.position.aux_state)[(0,0)]==0
 assert GameSession.replay(c,actual.to_record()).state==actual.state
