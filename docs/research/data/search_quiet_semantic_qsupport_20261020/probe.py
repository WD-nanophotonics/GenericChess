from dataclasses import replace
from pathlib import Path
import json, sys
ROOT=Path.cwd()
sys.path.insert(0, str(ROOT/'tests'))
from rule_semantics_ir_fixtures import weird_rulesets
from generic_chess.core.pieces import Piece
from generic_chess.rules.serialization import serialize_ruleset, deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.search import INF, _Budget, _Context, quiescence
import generic_chess.ai.alphabeta.search as searchmod
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.transition import legal_successors

rules=weird_rulesets()[3]
board=[[None]*8 for _ in range(8)]
for owner,type_id,file,rank in ((0,'K',0,0),(1,'K',7,7),(0,'R',3,3),(0,'R',3,4)):
    board[rank][file]=Piece(owner,type_id,type_id)
rules=replace(rules,initial_position=tuple(tuple(row) for row in board))
rules=deserialize_ruleset(serialize_ruleset(rules))
compiled=compile_ruleset_for_execution(rules)
session=GameSession(compiled)
for source,target in (((0,0),(0,1)),((7,7),(7,6))):
    action,= [a for a in session.legal_actions() if hasattr(a,'from_square') and (a.from_square.file,a.from_square.rank)==source and (a.to_square.file,a.to_square.rank)==target]
    session.submit(action)
state=session.state
compound,= [a for a in session.legal_actions() if a.pattern_id=='sem_00_move_and_shift_adjacent_friendly']
pairs=legal_successors(state,compiled)
compound_child=dict(pairs)[compound]

class Probe:
    def evaluate(self,s):
        b=s.position.board
        shifted=all(p is not None and p.owner==0 and p.current_type_id=='R' for p in (b[4*8+4],b[5*8+3]))
        value=10_000 if shifted else 0
        return -value if s.position.side_to_move==1 else value
    def type_value(self,t): return 0
    def capture_order_value(self,m,c): return 0

def run(force_include, evaluator=None):
    stats=SearchStatistics(); runtime=SearchPathRuntime(state,compiled); runtime.attach_stats(stats)
    ctx=_Context(compiled,evaluator or Probe(),TranspositionTable(),stats,
        _Budget(SearchLimits(max_depth=1,max_nodes=3000,max_time_seconds=5,
            quiescence_max_depth=1,quiescence_hard_max_depth=8),None),
        SearchTuning(use_root_tactical=False),False,False,1,8,None,runtime=runtime)
    original=searchmod.noisy_child
    def wrapped(action,child,side,parent_enemies,parent_inventory,child_in_check,*args,**kwargs):
        kept=original(action,child,side,parent_enemies,parent_inventory,child_in_check,*args,**kwargs)
        if force_include and action.pattern_id=='sem_00_move_and_shift_adjacent_friendly': return True
        return kept
    searchmod.noisy_child=wrapped
    try: score=quiescence(state,-INF,INF,0,0,ctx)
    finally: searchmod.noisy_child=original
    runtime.assert_balanced()
    return {'score':score,'qnodes':stats.qnodes,'qactions_material':stats.material_change_qactions,
            'qactions_check':stats.checking_move_qactions,'runtime_pushes':stats.runtime_pushes,
            'compound_in_initial_noisy':compound.pattern_id in [a.pattern_id for a in searchmod.classify_noisy(state,pairs,compiled)]}

cfg=EvaluationConfig()
default_eval=Evaluator(compiled,build_ruleset_profile(compiled,cfg),cfg)
out={'fixture':'existing weird_rulesets()[3] compound shift, legal two-King-move history; test-only evaluator rewards exact shifted two-piece state',
     'compound_state_changed':compound_child.position!=state.position,
     'material_inventory_equal':searchmod.material_inventory(compound_child.position)==searchmod.material_inventory(state.position),
     'child_terminal':compound_child.terminal_status.is_terminal,
     'test_evaluator_baseline':run(False),'test_evaluator_forced_include':run(True),'default_evaluator_baseline':run(False,default_eval),'default_evaluator_forced_include':run(True,default_eval),
     'interpretation':'Implementation sensitivity only; evaluator is deliberately constructed and not playing-strength/utility evidence.'}
print(json.dumps(out,sort_keys=True))



from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits

def root_decision(force):
    player=AlphaBetaPlayer(compiled,use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,evaluator_override=default_eval)
    original=searchmod.noisy_child
    def wrapped(action,child,side,parent_enemies,parent_inventory,child_in_check,*args,**kwargs):
        kept=original(action,child,side,parent_enemies,parent_inventory,child_in_check,*args,**kwargs)
        return True if force and action.pattern_id=='sem_00_move_and_shift_adjacent_friendly' else kept
    searchmod.noisy_child=wrapped
    try:
        d=player.choose_action(session,SearchLimits(max_depth=2,max_nodes=3000,quiescence_max_depth=1,quiescence_hard_max_depth=8,quiescence_max_nodes=200))
    finally: searchmod.noisy_child=original
    return {'score':d.score,'action_pattern':getattr(d.action,'pattern_id',None),'action_id':str(d.action),'depth':d.completed_depth,'nodes':d.nodes,'qnodes':d.qnodes,'qactions_check':d.checking_move_qactions,'qactions_material':d.material_change_qactions,'termination':d.termination_reason,'pv':[getattr(a,'pattern_id',str(a)) for a in d.principal_variation]}
print(json.dumps({'public_alpha_beta_baseline':root_decision(False),'public_alpha_beta_forced_quiet_compound':root_decision(True),'interpretation':'same root and deterministic 3000-node ceiling, one monkeypatched classifier inclusion only; no playing-strength claim'},sort_keys=True))
def root_decision_loose(force):
    player=AlphaBetaPlayer(compiled,use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,evaluator_override=default_eval)
    original=searchmod.noisy_child
    def wrapped(action,child,side,parent_enemies,parent_inventory,child_in_check,*args,**kwargs):
        kept=original(action,child,side,parent_enemies,parent_inventory,child_in_check,*args,**kwargs)
        return True if force and action.pattern_id=='sem_00_move_and_shift_adjacent_friendly' else kept
    searchmod.noisy_child=wrapped
    try:
        d=player.choose_action(session,SearchLimits(max_depth=2,max_nodes=3000,quiescence_max_depth=1,quiescence_hard_max_depth=8,quiescence_max_nodes=3000))
    finally: searchmod.noisy_child=original
    return {'score':d.score,'action_pattern':getattr(d.action,'pattern_id',None),'action_id':str(d.action),'depth':d.completed_depth,'nodes':d.nodes,'qnodes':d.qnodes,'qactions_check':d.checking_move_qactions,'qactions_material':d.material_change_qactions,'termination':d.termination_reason,'pv':[getattr(a,'pattern_id',str(a)) for a in d.principal_variation]}
print(json.dumps({'public_alpha_beta_baseline_qcap3000':root_decision_loose(False),'public_alpha_beta_forced_quiet_compound_qcap3000':root_decision_loose(True),'interpretation':'same deterministic total node budget; q-specific cap raised to total budget so total nodes is binding; one classifier override only'},sort_keys=True))
