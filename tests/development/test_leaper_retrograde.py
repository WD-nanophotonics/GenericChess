"""Fresh-position attractors versus complete-history shared Core authority."""
from collections import Counter
from dataclasses import replace

import pytest

from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from scripts.leaper_microgames import ExactTree, Exhaustion, make_rules, quiet_layouts
from scripts.leaper_retrograde import attractor, fresh_state, history_value, inactive_clock, root_action_labels, solve_world


def test_attractor_retains_cycles_and_draw_escape_instead_of_labelling_loss():
    # 0 losing terminal; 1 wins into 0; 2 loses (all children win);
    # 3,4 cycle; 5 can draw into the cycle rather than lose into 1.
    edges=[(),(0,),(1,),(4,),(3,),(1,3)]
    values,ranks=attractor(edges,{0:-1})
    assert values=={0:-1,1:1,2:-1,3:0,4:0,5:0}
    assert ranks=={0:0,1:1,2:2}


def test_winning_rank_is_minimum_but_losing_rank_is_worst_defense():
    edges=[(),(0,),(1,),(2,),(1,3),(2,4)]
    values,ranks=attractor(edges,{0:-1})
    assert [values[i]for i in range(6)]==[-1,1,-1,1,-1,1]
    assert [ranks[i]for i in range(6)]==[0,1,2,3,4,3]


def test_position_bound_makes_actual_positive_core_clock_unreachable():
    assert inactive_clock(3)==8209
    assert inactive_clock(4)==101281
    assert inactive_clock(5)==663601


@pytest.fixture(scope='module')
def graph():return solve_world()


def test_independent_synchronous_fixed_point_agrees_at_every_vertex(graph):
    values=dict(graph['terminals'])
    while True:
        new=dict(values)
        for i,children in enumerate(graph['edges']):
            if i in values:continue
            if any(values.get(c)==-1 for c in children):new[i]=1
            elif children and all(values.get(c)==1 for c in children):new[i]=-1
        if new==values:break
        values=new
    assert {i:values.get(i,0)for i in range(len(graph['edges']))}==graph['values']


def test_all_288_fresh_roots_match_existing_h6_full_history_results(graph):
    # Independent full-history unrolling, not another Position value iteration.
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    compiled=compile_ruleset_for_execution(make_rules(layouts=quiet_layouts(288)))
    tree=ExactTree(compiled)
    labels=[tree.solve(initial_state(compiled,str(i)if i else None))for i in range(288)]
    assert labels==[graph['values'][i]for i in graph['roots']]
    assert Counter(labels)=={1:80,0:200,-1:8}


def test_fresh_winning_certificates_replay_all_defenses_with_real_history(graph):
    compiled=graph['compiled'];values=graph['values'];ranks=graph['ranks']
    visited=0
    for setup,root in enumerate(graph['roots']):
        if not values[root]:continue
        winner=0 if values[root]==1 else 1
        pending=[initial_state(compiled,str(setup)if setup else None)]
        while pending:
            state=pending.pop();i=graph['indices'][state.position];visited+=1
            if state.terminal_status.is_terminal:
                assert state.terminal_status.status is TerminalStatus.CHECKMATE
                assert state.terminal_status.winner==winner
                continue
            choices=list(zip(graph['actions'][i],graph['edges'][i]))
            if state.position.side_to_move==winner:
                choices=[next((a,c)for a,c in choices if values[c]==-1 and ranks[c]==ranks[i]-1)]
            for action,child in choices:
                actual=apply_action(state,action,compiled)
                assert graph['indices'][actual.position]==child
                assert ranks[child]<ranks[i]
                assert actual.terminal_status.status is not TerminalStatus.REPETITION
                pending.append(actual)
    assert visited>100


def test_graph_budget_failure_produces_no_numeric_draw_labels():
    with pytest.raises(Exhaustion,match='UNKNOWN'):
        solve_world(max_states=0)


def test_actual_ongoing_history_can_turn_fresh_win_into_draw(graph):
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    state=initial_state(graph['compiled'],'285')
    for src,dst in(((1,2),(0,1)),((2,2),(1,2)),((0,1),(0,2)),((1,2),(2,1))):
        state=apply_action(state,BoardMove(Square(*src),Square(*dst)),graph['compiled'])
    assert state.terminal_status.status is TerminalStatus.ONGOING
    assert graph['values'][graph['indices'][state.position]]==1
    assert history_value(graph,state)==0


def test_history_labels_refuse_missing_occurrence_evidence(graph):
    state=initial_state(graph['compiled'])
    with pytest.raises(AssertionError,match='history/count mismatch'):
        history_value(graph,replace(state,repetition_counts=()))


def test_history_attractor_plus_distance_matches_independent_h6_unroll(graph):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from scripts.leaper_microgames import session_at
    compiled=compile_ruleset_for_execution(make_rules())
    tree=ExactTree(compiled);tree.solve(initial_state(compiled))
    for state,path in tree.paths.items():
        long=session_at(graph['compiled'],None,path).state
        value,rank=history_value(graph,long,with_rank=True)
        if rank is not None and rank>6-state.ply_count:value=0
        player0=value*(1 if state.position.side_to_move==0 else -1)
        assert player0==tree.values[state]


def test_blocked_root_action_labels_match_complete_one_move_histories(graph):
    for setup,root in enumerate(graph['roots'][:8]):
        state=initial_state(graph['compiled'],str(setup)if setup else None)
        for action,label in root_action_labels(graph,root).items():
            child=apply_action(state,action,graph['compiled'])
            assert label==-history_value(graph,child)


def test_material_surplus_A_against_bare_Anchor_does_not_imply_winning_value():
    from scripts.leaper_microgames import KING
    graph=solve_world(kinds=('A','B'),b_geometry=KING)
    positions=[]
    for i,p in enumerate(graph['positions']):
        ordinary=[piece.current_type_id for piece in p.board if piece and piece.current_type_id!='K']
        if ordinary==['A']:positions.append(i)
    assert positions and all(graph['values'][i]==0 for i in positions)


def test_symmetric_experiential_probe_uses_existing_learner_and_saves_literal_paths(tmp_path):
    import json
    from scripts.leaper_retrograde import experiential_probe
    result=experiential_probe(tmp_path/'probe',episodes=2)
    assert result['episodes']==2 and result['missing']==0
    assert result['config']['oracle'].startswith('NONE:')
    assert result['endings']=={'ACTUAL_TERMINAL':2}
    queries=[json.loads(line)for line in(tmp_path/'probe'/'queries.jsonl').read_text().splitlines()]
    assert all(q['complete']and q['pv_choices']for q in queries)


def test_depth_curve_saves_reference_timeout_without_any_numeric_labels(tmp_path):
    import json
    from scripts.leaper_retrograde import fresh_depth_study
    result=fresh_depth_study(tmp_path/'curve',width=3,roots_count=1,depths=(1,),whole_seconds=.000001)
    assert 'UNKNOWN' in result['status']and result['numeric_labels']is None
    assert result['queries']==0 and result['missing']==1
    assert json.loads((tmp_path/'curve'/'summary.json').read_text())==result
