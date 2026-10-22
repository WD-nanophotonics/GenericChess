"""Actual rules/history, exact/reference agreement and oracle separation."""
from dataclasses import replace
import pytest

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.exact_generic_preference_solver_v3 import solve_root_threshold_v3
from scripts.leaper_microgames import (
    KING, ExactTree, Exhaustion, make_rules, session_at, decision_study,
    blockade_example,terminal_census,learning_diagnostic,coexistence_rules,
    composition_parameter_cells,quiet_layouts,
)


@pytest.mark.parametrize('kinds',[('M','M'),('A','B'),('B','A')])
def test_shared_runtime_exact_reference_agrees_on_every_root_action(kinds):
    compiled=compile_ruleset_for_execution(make_rules(kinds=kinds))
    state=initial_state(compiled);tree=ExactTree(compiled)
    tree.solve(state)
    reference=solve_root_threshold_v3(compiled,state,max_nodes=100000)
    assert reference.strong and reference.root_value=={-1:'LOSS',0:'DRAW',1:'WIN'}[tree.values[state]]
    expected={str(action_to_dict(a)):v for a,s in tree.edges[state]for v in(tree.values[s],)}
    assert {str(x['action']):{'LOSS':-1,'DRAW':0,'WIN':1}[x['value']]for x in reference.action_values}==expected
    assert all(s.ply_count<=6 for s in tree.values)


def test_core_unrolling_preserves_public_session_and_complete_history():
    compiled=compile_ruleset_for_execution(make_rules(horizon=3))
    tree=ExactTree(compiled);tree.solve(initial_state(compiled))
    for state,path in tree.paths.items():
        session=session_at(compiled,None,path)
        assert session.state==state
        assert len(state.history)==state.ply_count+1
        assert len(tree.edges[state])==len(legal_actions(state,compiled))


def test_homogeneous_mechanics_are_equal_and_anchors_remain_royal():
    rules=make_rules()
    assert all(tuple(a.offset for a in t.movement_atoms)==KING for t in rules.piece_types)
    assert sum(t.is_anchor for t in rules.piece_types)==1
    assert rules.capture_disposition=='remove_from_game'and rules.repetition_limit==2
    assert not rules.pass_enabled and not rules.semantic_actions and not rules.declarations


def test_coexistence_B_geometry_control_uses_actual_Core_and_preserves_default():
    from scripts.leaper_microgames import DIAGONAL
    from generic_chess.session.session import GameSession
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    default=coexistence_rules(('A','B'))
    assert default==coexistence_rules(('A','B'),b_geometry=DIAGONAL)
    changed=coexistence_rules(('A','B'),b_geometry=KING)
    assert changed.initial_position==default.initial_position
    sessions=[GameSession(compile_ruleset_for_execution(r))for r in(default,changed)]
    orthogonal=BoardMove(Square(0,1),Square(1,1))
    assert orthogonal not in sessions[0].legal_actions()
    assert orthogonal in sessions[1].legal_actions()
    sessions[1].submit(orthogonal)
    assert sessions[1].state.position.board[4].current_type_id=='B'
    assert len(sessions[1].state.history)==2


def test_reference_budget_failure_is_unknown_not_a_draw():
    compiled=compile_ruleset_for_execution(make_rules())
    tree=ExactTree(compiled,max_states=0)
    with pytest.raises(Exhaustion,match='UNKNOWN'):tree.solve(initial_state(compiled))
    assert not tree.values


def test_public_full_rule_horizon_chooses_exact_optimal_actions():
    compiled=compile_ruleset_for_execution(make_rules())
    tree=ExactTree(compiled);tree.solve(initial_state(compiled))
    rows=decision_study(tree,limit=16,depths=(6,))
    assert rows and all(r['complete']and r['optimal']for r in rows)


def test_matched_geometry_and_removal_counterfactuals_use_legal_fresh_histories():
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    import json
    rows=blockade_example()
    assert [r['player0_value']for r in rows]==[1,0,0]
    for row in rows:
        compiled=compile_ruleset_for_execution(ruleset_from_dict(row['rules']))
        session=GameSession.replay(compiled,deserialize_game_record(json.dumps(row['after'])))
        assert session.state.ply_count==1
        assert len(row['after']['actions'])==1
    assert rows[1]['legal_replies'][0]['from']==[1,0]
    assert rows[1]['legal_replies'][0]['to']==[0,1]


@pytest.mark.parametrize('width,raw,ongoing,stale',[(3,8208,2736,72),(4,101280,55004,76)])
def test_diagonal_orthogonal_world_has_no_mating_configuration_even_after_capture(width,raw,ongoing,stale):
    result=terminal_census(('A','B'),width=width)
    # 2*(9P2 + 2*9P3 + 9P4): no ordinary, either one, or both.
    assert result['enumerated_placements']==raw
    assert result['static_counts']['ongoing']==ongoing
    assert result['static_counts']['stalemate']==stale
    assert result['static_counts']['checkmate']==0


def test_real_deep_terminal_learning_has_zero_gradient_and_explicit_actor_weights(tmp_path):
    import json
    result=learning_diagnostic(tmp_path/'leaper',episodes=2)
    deep=result['summaries'][1]
    assert deep['candidate_queries']>0
    assert deep['candidate_queries']==deep['terminal_PV_observations']
    assert deep['changed_updates']==0 and deep['initial']==deep['final']
    queries=[json.loads(s)for s in(tmp_path/'leaper'/'queries.jsonl').read_text().splitlines()]
    assert all(q['search_weights']==[1.]*4 for q in queries if q['actor']!=q['color'])


def test_C_replacement_keeps_force_occupancy_and_legal_start_fixed():
    from generic_chess.core.movement import LeapAtom
    states=[]
    for lineup in(('A','B','A'),('A','B','C')):
        rules=coexistence_rules(lineup)
        assert all(isinstance(a,LeapAtom)for t in rules.piece_types for a in t.movement_atoms)
        compiled=compile_ruleset_for_execution(rules);state=initial_state(compiled)
        assert not state.terminal_status.is_terminal
        states.append(state)
    def occupancy(state):
        return [(i,p.owner)for i,p in enumerate(state.position.board)if p is not None]
    assert occupancy(states[0])==occupancy(states[1])
    assert len(occupancy(states[0]))==8


def test_extra_C_can_turn_stalemate_draw_into_forced_loss_in_actual_session():
    from scripts.leaper_microgames import conditional_C_liability
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.core.terminal import TerminalStatus
    result=conditional_C_liability()
    for key,status in(('with_C_record',TerminalStatus.CHECKMATE),('without_C_record',TerminalStatus.STALEMATE)):
        compiled=compile_ruleset_for_execution(ruleset_from_dict(result['rule']))
        session=GameSession.replay(compiled,deserialize_game_record(__import__('json').dumps(result[key])))
        assert session.state.terminal_status.status is status
    assert result['with_C_owner_value']==-1 and result['without_C_owner_value']==0


def test_C_axis_intervention_removes_the_actual_horizontal_mate_defense_only():
    from generic_chess.core.pieces import Piece
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    from generic_chess.core.terminal import TerminalStatus
    from generic_chess.session.session import GameSession
    from generic_chess.rules.schema import ruleset_to_dict
    actors={0:Piece(0,'K','K'),3:Piece(0,'B','B'),4:Piece(0,'A','A'),
        5:Piece(1,'A','A'),6:Piece(1,'C','C'),8:Piece(1,'K','K')}
    board=tuple(tuple(actors.get(y*3+x)for x in range(3))for y in range(3))
    rules=[coexistence_rules(('A','B','C'),initial_position=board,c_axis=a)for a in('horizontal','vertical')]
    data=[ruleset_to_dict(r)for r in rules]
    assert {k for k in data[0]if data[0][k]!=data[1][k]}=={'piece_types'}
    sessions=[GameSession(compile_ruleset_for_execution(r))for r in rules]
    for session in sessions:session.submit(BoardMove(Square(1,1),Square(1,2)))
    assert sessions[0].legal_actions()==(BoardMove(Square(0,2),Square(1,2)),)
    assert sessions[1].state.terminal_status.status is TerminalStatus.CHECKMATE
    assert sessions[1].state.terminal_status.winner==0


def test_transpose_is_full_finite_game_isomorphism_including_repetition_history():
    from generic_chess.core.coordinates import Square
    from generic_chess.core.transition import apply_action
    compiled=compile_ruleset_for_execution(make_rules(layouts=[(0,1,8,7),(0,3,8,5)]))
    def transpose(action):
        return replace(action,from_square=Square(action.from_square.rank,action.from_square.file),
                       to_square=Square(action.to_square.rank,action.to_square.file))
    pending=[(initial_state(compiled),initial_state(compiled,'1'))];visited=0
    while pending:
        left,right=pending.pop();visited+=1
        assert left.terminal_status==right.terminal_status
        assert left.ply_count==right.ply_count
        assert left.position.side_to_move==right.position.side_to_move
        assert all(left.position.board[y*3+x]==right.position.board[x*3+y]for x in range(3)for y in range(3))
        assert [(h.actor,h.gave_check)for h in left.history]==[(h.actor,h.gave_check)for h in right.history]
        assert [[a.position_key==b.position_key for b in left.history]for a in left.history]==[[a.position_key==b.position_key for b in right.history]for a in right.history]
        actions=legal_actions(left,compiled)
        assert {transpose(a)for a in actions}==set(legal_actions(right,compiled))
        pending.extend((apply_action(left,a,compiled),apply_action(right,transpose(a),compiled))for a in actions)
    assert visited==416


def test_complete_material_leaf_cells_separate_forced_error_from_tied_action(tmp_path):
    result=composition_parameter_cells(tmp_path/'cells',upper=2,depths=(1,2))
    assert result['cuts']==['1/2','1','3/2']
    # These checks also execute all public/reference action-set comparisons.
    for row in result['tables']['ABC']['rows']:
        assert row['forced_errors']==0 and row['tie_risks']==2
    aba=result['tables']['ABA']['rows']
    low=next(r for r in aba if r['cell']==0 and r['depth']==1)
    high=next(r for r in aba if r['cell']==2 and r['depth']==1)
    assert (low['forced_errors'],high['forced_errors'])==(2,3)


def test_larger_board_safe_layout_selection_keeps_declared_count_and_default():
    layouts=quiet_layouts(4,width=4)
    assert layouts[0]==(0,1,15,14)and len(set(layouts))==4
    compile_ruleset_for_execution(make_rules(width=4,layouts=layouts))
