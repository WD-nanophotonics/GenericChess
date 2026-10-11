"""Observed EP bound-as-tie defect and optional exact-root repair."""
from types import SimpleNamespace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.native import native_available
from generic_chess.native import semantic as ns
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from scripts.search_backend_comparison import CASES,CoreBoard

pytestmark=pytest.mark.skipif(not native_available(),reason='Native unavailable')

def ep():
 c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
 core=CoreBoard(next(x for x in CASES if x['id']=='chess-ep'),c)
 s=SimpleNamespace(compiled=c,state=core.initial,_search_witnesses=core.witnesses)
 nr=NativeSemanticLegalityProvider.try_create(c,strict=True).native_rules
 pos=pack_semantic_search_position(c,nr,s)
 values=dict(K=0,P=100,N=200,B=300,R=400,Q=500)
 return nr,pos,values

@pytest.mark.parametrize('tt',[0,1,64])
def test_ep_inexact_equal_bound_cannot_replace_exact_incumbent(tt):
 nr,pos,values=ep();before=ns.snapshot(nr,pos)
 full=ns.semantic_iterative_search(nr,pos,3,board_values=values,hand_values=values,tt_megabytes=tt)
 exact=ns.semantic_iterative_search(nr,pos,3,board_values=values,hand_values=values,tt_megabytes=tt,root_window_pruning=True)
 assert exact['completed_depth']==full['completed_depth']==3
 assert (exact['score'],exact['best_action'],exact['principal_variation'])==(full['score'],full['best_action'],full['principal_variation'])
 assert exact['score']==100
 child=ns.make_checked(nr,pos,exact['best_action'])
 verify=ns.semantic_iterative_search(nr,child,2,board_values=values,hand_values=values,tt_megabytes=0,_root_ply_offset=1)
 assert -verify['score']==exact['score']
 assert exact['root_tie_refinements']>0 and exact['root_tie_aborts']==0
 assert ns.snapshot(nr,pos)==before

@pytest.mark.parametrize('profile',['material','zero'])
def test_completed_lower_iteration_survives_refinement_budget_abort(profile):
 nr,pos,values=ep()
 if profile=='zero':values={tid:0 for tid in nr.type_ids}
 before=ns.snapshot(nr,pos);seen=False
 # Fixed finite budgets cover the short first-iteration tie refinements; no
 # result-driven expansion. Any published result must be a complete iteration.
 for nodes in range(1,257):
  limited=ns.semantic_iterative_search(nr,pos,3,board_values=values,hand_values=values,max_nodes=nodes,root_window_pruning=True)
  if not limited['root_tie_aborts']:continue
  seen=True;depth=limited['completed_depth'];assert limited['termination_reason']=='node_budget'
  if depth:
   reference=ns.semantic_iterative_search(nr,pos,depth,board_values=values,hand_values=values,root_window_pruning=False)
   assert (limited['score'],limited['best_action'],limited['principal_variation'])==(reference['score'],reference['best_action'],reference['principal_variation'])
  else:assert limited['used_fallback']
  assert ns.snapshot(nr,pos)==before
  break
 assert seen

@pytest.mark.parametrize('fixture',['promotion','temporary','compound'])
@pytest.mark.parametrize('tt',[0,1])
def test_supported_mechanics_match_full_window_selected_value(fixture,tt):
 from dataclasses import replace
 from generic_chess.core.pieces import Piece
 from generic_chess.session.session import GameSession
 if fixture=='promotion':
  c=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
  core=CoreBoard(next(x for x in CASES if x['id']=='shogi-promotion'),c)
  session=SimpleNamespace(compiled=c,state=core.initial,_search_witnesses=core.witnesses)
 else:
  from rule_semantics_ir_fixtures import weird_rulesets,castling_ruleset
  rules=castling_ruleset() if fixture=='compound' else weird_rulesets()[2]
  if fixture=='temporary':
   board=[list(row) for row in rules.initial_position];board[1][0]=Piece(0,'R','R');rules=replace(rules,initial_position=tuple(tuple(row) for row in board))
  c=compile_ruleset_for_execution(rules);session=GameSession(c)
 nr=NativeSemanticLegalityProvider.try_create(c,strict=True).native_rules
 pos=pack_semantic_search_position(c,nr,session);before=ns.snapshot(nr,pos)
 values={tid:100*(i+1) for i,tid in enumerate(nr.type_ids)}
 full=ns.semantic_iterative_search(nr,pos,2,board_values=values,hand_values=values,tt_megabytes=tt)
 exact=ns.semantic_iterative_search(nr,pos,2,board_values=values,hand_values=values,tt_megabytes=tt,root_window_pruning=True)
 assert (exact['score'],exact['best_action'],exact['principal_variation'])==(full['score'],full['best_action'],full['principal_variation'])
 child=ns.make_checked(nr,pos,exact['best_action'])
 verified=ns.semantic_iterative_search(nr,child,1,board_values=values,hand_values=values,_root_ply_offset=1)
 assert -verified['score']==exact['score']
 assert ns.snapshot(nr,pos)==before

@pytest.mark.parametrize('tt',[0,1])
def test_cold_and_reused_persistent_root_windows_keep_exact_selected_child(tt):
 from generic_chess.native.semantic_engine import SemanticSearchEngine
 from generic_chess.session.session import GameSession
 from generic_chess.ai.limits import SearchLimits
 from scripts.audit_lichess_complete_children import uci
 c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));session=GameSession(c)
 for move in ['e2e4','a7a6','e4e5','d7d5']:
  session.submit(next(a for a in session.legal_actions() if uci(a)==move))
 nr=NativeSemanticLegalityProvider.try_create(c,strict=True).native_rules
 values=dict(K=0,P=100,N=200,B=300,R=400,Q=500)
 engine=SemanticSearchEngine(c,nr,board_values=values,hand_values=values,tt_megabytes=tt)
 reference=ns.semantic_iterative_search(nr,pack_semantic_search_position(c,nr,session),3,board_values=values,hand_values=values)
 for _ in range(2):
  result=engine.search(session,SearchLimits(max_depth=3,max_nodes=None,quiescence_max_depth=0),root_window_pruning=True)
  assert result.score==reference['score']==100
  assert uci(result.action)=='f1d3'

@pytest.mark.parametrize('warm_depth,target_depth',[(3,1),(4,2),(4,3)])
def test_deeper_persistent_tt_is_only_ordering_hint_for_exact_root_mode(warm_depth,target_depth):
 from generic_chess.native.semantic_engine import SemanticSearchEngine
 from generic_chess.session.session import GameSession
 from generic_chess.ai.limits import SearchLimits
 from scripts.audit_lichess_complete_children import uci
 c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));session=GameSession(c)
 for move in ['e2e4','a7a6','e4e5','d7d5']:
  session.submit(next(a for a in session.legal_actions() if uci(a)==move))
 nr=NativeSemanticLegalityProvider.try_create(c,strict=True).native_rules
 values=dict(K=0,P=100,N=200,B=300,R=400,Q=500)
 engine=SemanticSearchEngine(c,nr,board_values=values,hand_values=values,tt_megabytes=1)
 engine.search(session,SearchLimits(max_depth=warm_depth,max_nodes=None,quiescence_max_depth=0),root_window_pruning=True)
 reference=ns.semantic_iterative_search(nr,pack_semantic_search_position(c,nr,session),target_depth,board_values=values,hand_values=values,tt_megabytes=0)
 result=engine.search(session,SearchLimits(max_depth=target_depth,max_nodes=None,quiescence_max_depth=0),root_window_pruning=True)
 assert result.completed_depth==target_depth and result.score==reference['score']
 assert result.action==ns.public_action(nr,reference['best_action'])
 child=ns.make_checked(nr,pack_semantic_search_position(c,nr,session),reference['best_action'])
 if target_depth==1:
  # max_depth0 iterative search is a legal fallback, not a leaf evaluator.
  child_score=ns.evaluate(nr,child,board_values=tuple(values[t] for t in nr.type_ids),hand_values=tuple(values[t] for t in nr.type_ids))
 else:
  child_score=ns.semantic_iterative_search(nr,child,target_depth-1,board_values=values,hand_values=values,_root_ply_offset=1)['score']
 assert -child_score==result.score

def test_legacy_mode_entries_do_not_supply_exact_root_scores_after_mode_switch():
 from generic_chess.native.semantic_engine import SemanticSearchEngine
 from generic_chess.session.session import GameSession
 from generic_chess.ai.limits import SearchLimits
 from scripts.audit_lichess_complete_children import uci
 c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));session=GameSession(c)
 for move in ['e2e4','a7a6','e4e5','d7d5']:
  session.submit(next(a for a in session.legal_actions() if uci(a)==move))
 nr=NativeSemanticLegalityProvider.try_create(c,strict=True).native_rules
 values=dict(K=0,P=100,N=200,B=300,R=400,Q=500)
 engine=SemanticSearchEngine(c,nr,board_values=values,hand_values=values,tt_megabytes=1)
 for depth in [4,2]:
  engine.search(session,SearchLimits(max_depth=depth,max_nodes=None,quiescence_max_depth=0),root_window_pruning=False)
 reference=ns.semantic_iterative_search(nr,pack_semantic_search_position(c,nr,session),2,board_values=values,hand_values=values,tt_megabytes=0)
 result=engine.search(session,SearchLimits(max_depth=2,max_nodes=None,quiescence_max_depth=0),root_window_pruning=True)
 assert result.score==reference['score'] and result.action==ns.public_action(nr,reference['best_action'])
