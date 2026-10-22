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


def test_history_certificate_replays_real_terminal_and_rejects_draw_or_resource_cutoff(graph):
    from scripts.leaper_retrograde import winning_history_certificate
    setup=next(i for i,r in enumerate(graph['roots'])if graph['values'][r]==1)
    state=initial_state(graph['compiled'],str(setup)if setup else None)
    proof=winning_history_certificate(graph,state)
    assert proof['winner']==0 and proof['terminal_branches']>0
    with pytest.raises(Exhaustion,match='UNKNOWN'):
        winning_history_certificate(graph,state,max_nodes=0)
    draw=next(i for i,r in enumerate(graph['roots'])if graph['values'][r]==0)
    with pytest.raises(ValueError,match='decisive'):
        winning_history_certificate(graph,initial_state(graph['compiled'],str(draw)if draw else None))


def test_already_terminal_certificate_needs_no_new_graph_history_cache(graph):
    from scripts.leaper_retrograde import winning_history_certificate
    index=next(i for i,v in graph['terminals'].items()if v)
    state=fresh_state(graph['positions'][index],graph['compiled'])
    uncached={k:v for k,v in graph.items()if k not in('key_indices','history_values')}
    proof=winning_history_certificate(uncached,state)
    assert proof['winner']==state.terminal_status.winner and proof['leaf_paths']==[[]]
    assert proof['nodes']==1 and proof['root_rank']==0


def test_graph_budget_failure_produces_no_numeric_draw_labels():
    with pytest.raises(Exhaustion,match='UNKNOWN'):
        solve_world(max_states=0)


@pytest.mark.parametrize('lineup', [('A','B','A'),('A','B','C')])
def test_layout_intervention_preserves_occupancy_and_changes_only_declared_AB_squares(lineup):
    from generic_chess.core.attacks import is_in_check
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from scripts.leaper_microgames import coexistence_rules
    original=compile_ruleset_for_execution(coexistence_rules(lineup))
    swapped=compile_ruleset_for_execution(coexistence_rules(lineup,layout='swap_ab'))
    before=initial_state(original).position.board
    state=initial_state(swapped);after=state.position.board
    assert Counter(before)==Counter(after)
    assert [i for i,p in enumerate(before)if p]==[i for i,p in enumerate(after)if p]
    for i,p in enumerate(before):assert after[{1:3,3:1,7:5,5:7}.get(i,i)]==p
    assert not state.terminal_status.is_terminal
    assert not any(is_in_check(state.position,c,swapped)for c in(0,1))
    with pytest.raises(ValueError,match='layout'):
        coexistence_rules(lineup,layout='typo')


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


def test_rank_shortcut_agrees_with_independent_root_block_on_cyclic_graphs():
    import random
    rng=random.Random(20261022)
    for _ in range(300):
        n=12
        edges=[tuple(j for j in range(n)if j%2!=i%2 and rng.random()<.35)
               for i in range(n)]
        terminals={i:rng.choice((-1,0,1))for i,cs in enumerate(edges)if not cs}
        for i in rng.sample(range(n),3):edges[i]=();terminals[i]=rng.choice((-1,0,1))
        values,ranks=attractor(edges,terminals)
        g=dict(edges=edges,actions=[tuple(range(len(e)))for e in edges],
            values=values,ranks=ranks,terminals=terminals)
        for root,children in enumerate(edges):
            if not children:continue
            blocked=list(edges);blocked[root]=()
            truth,_=attractor(blocked,terminals|{root:0})
            assert root_action_labels(g,root)=={a:-truth[c]for a,c in enumerate(children)}


def test_one_prefix_attractor_labels_agree_with_each_actual_child_history(graph):
    from scripts.leaper_retrograde import history_action_labels
    from scripts.leaper_microgames import session_at
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    compiled=compile_ruleset_for_execution(make_rules())
    tree=ExactTree(compiled);tree.solve(initial_state(compiled))
    for short,path in tree.paths.items():
        if not tree.edges[short]:continue
        state=session_at(graph['compiled'],None,path).state
        if state.terminal_status.is_terminal:continue
        labels=history_action_labels(graph,state)
        for action,value in labels.items():
            assert value==-history_value(graph,apply_action(state,action,graph['compiled']))


def test_material_surplus_A_against_bare_Anchor_does_not_imply_winning_value():
    from scripts.leaper_microgames import KING
    graph=solve_world(kinds=('A','B'),b_geometry=KING)
    positions=[]
    for i,p in enumerate(graph['positions']):
        ordinary=[piece.current_type_id for piece in p.board if piece and piece.current_type_id!='K']
        if ordinary==['A']:positions.append(i)
    assert positions and all(graph['values'][i]==0 for i in positions)


def test_fresh_C_only_control_has_material_ties_but_public_D3_finds_actual_mate():
    from copy import copy
    from scripts.leaper_microgames import coexistence_rules
    from generic_chess.core.pieces import Piece
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
    from generic_chess.learning.mainline_search import search
    actors={0:Piece(0,'K','K'),3:Piece(0,'B','B'),4:Piece(0,'A','A'),6:Piece(1,'C','C'),8:Piece(1,'K','K')}
    board=tuple(tuple(actors.get(y*3+x)for x in range(3))for y in range(3))
    rules=coexistence_rules(('A','B','C'),horizon=2*9**9+1,initial_position=board)
    compiled=compile_ruleset_for_execution(rules);session=GameSession(compiled)
    child_features=[]
    for action in session.legal_actions():
        child=copy(session);child.submit(action)
        env=FixedScaleSessionEnv(child,unit_type='A')
        assert env.terminal()is None
        child_features.append(env.features())
    assert len(child_features)==6 and len(set(child_features))==1
    env=FixedScaleSessionEnv(session,unit_type='A')
    receipt=search(env,Model([1.]*6),depth=3,nodes=8192,seconds=3)
    assert receipt.complete and receipt.completed_depth==3 and receipt.pv_terminal
    for choice in receipt.pv_choices:env.push(choice)
    assert env.terminal()==1 and env.session.state.terminal_status.status is TerminalStatus.CHECKMATE


def test_symmetric_experiential_probe_uses_existing_learner_and_saves_literal_paths(tmp_path):
    import json
    from scripts.leaper_retrograde import experiential_probe
    result=experiential_probe(tmp_path/'probe',episodes=2)
    assert result['episodes']==2 and result['missing']==0
    assert result['config']['oracle'].startswith('NONE:')
    assert result['endings']=={'ACTUAL_TERMINAL':2}
    queries=[json.loads(line)for line in(tmp_path/'probe'/'queries.jsonl').read_text().splitlines()]
    assert all(q['complete']and q['pv_choices']for q in queries)


def test_sampled_experience_preserves_actual_opening_history_and_color_pairs(tmp_path):
    import json
    from scripts.leaper_retrograde import experiential_probe
    from scripts.leaper_microgames import sampled_openings,coexistence_rules,session_at
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    compiled=compile_ruleset_for_execution(coexistence_rules(('A','B','C')))
    paths=sampled_openings(compiled,count=8)
    assert paths==sampled_openings(compiled,count=8)
    assert all(1<=len(p)<=1+i%6 for i,p in enumerate(paths))
    for p in paths:
        state=session_at(compiled,None,p).state
        assert state.ply_count==len(p)and len(state.history)==len(p)+1
    result=experiential_probe(tmp_path/'openings',episodes=2,opening_count=8)
    rows=[json.loads(s)for s in(tmp_path/'openings'/'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
    queries=[json.loads(s)for s in(tmp_path/'openings'/'queries.jsonl').read_text(encoding='utf-8').splitlines()]
    assert result['missing']==0
    assert [r['color']for r in rows]==[0,1]
    assert rows[0]['initial_record']==rows[1]['initial_record']
    for r in rows:
        assert r['record']['actions'][:1]==r['initial_record']['actions']
    assert all(q['prefix_length']==1 and q['opening_index']==0 for q in queries)


def test_random_foe_changes_experience_without_fabricating_searches_or_oracle_labels(tmp_path):
    import json
    from scripts.leaper_retrograde import experiential_probe
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    initial=[1.,1.03,1.01,1.,1.,1.]
    result=experiential_probe(tmp_path/'random',episodes=2,opening_count=8,
        random_foe_seed=2026102201,initial_weights=initial)
    assert result['missing']==0 and result['config']['oracle'].startswith('NONE:')
    assert result['config']['initial']==initial
    moves=[json.loads(s)for s in(tmp_path/'random'/'opponent-moves.jsonl').read_text(encoding='utf-8').splitlines()]
    queries=[json.loads(s)for s in(tmp_path/'random'/'queries.jsonl').read_text(encoding='utf-8').splitlines()]
    episodes=[json.loads(s)for s in(tmp_path/'random'/'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
    assert episodes[0]['before_weights']==initial
    assert moves and all(q['actor']==q['color']for q in queries)
    assert sum(e['queries']for e in episodes)==len(queries)
    assert sum(e['plies']for e in episodes)==len(moves)+len(queries)
    compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads((tmp_path/'random'/'rules.json').read_text(encoding='utf-8'))))
    for e in episodes:
        session=GameSession.replay(compiled,deserialize_game_record(json.dumps(e['record'])))
        assert session.state.ply_count==len(e['initial_record']['actions'])+e['plies']
        if e['outcome']is not None:assert session.state.terminal_status.is_terminal


def test_depth_curve_saves_reference_timeout_without_any_numeric_labels(tmp_path):
    import json
    from scripts.leaper_retrograde import fresh_depth_study
    result=fresh_depth_study(tmp_path/'curve',width=3,roots_count=1,depths=(1,),whole_seconds=.000001)
    assert 'UNKNOWN' in result['status']and result['numeric_labels']is None
    assert result['queries']==0 and result['missing']==1
    assert json.loads((tmp_path/'curve'/'summary.json').read_text())==result


@pytest.mark.parametrize('lineup,axis,names', [
    (('A','B','A'),'horizontal',(('board','A'),('board','B'),('hand','A'),('hand','B'))),
    (('A','B','C'),'vertical',(('board','A'),('board','B'),('board','C'),('hand','A'),('hand','B'),('hand','C'))),
])
def test_experience_world_control_replays_its_own_rules(tmp_path,lineup,axis,names):
    import json
    from scripts.leaper_retrograde import experiential_probe
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.learning.incremental import FixedScaleSessionEnv
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    folder=tmp_path/'world'
    result=experiential_probe(folder,episodes=2,opening_count=8,
        random_foe_seed=2026102201,lineup=lineup,c_axis=axis)
    compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(
        (folder/'rules.json').read_text(encoding='utf-8'))))
    env=FixedScaleSessionEnv(GameSession(compiled),unit_type='A')
    assert env.names==names
    assert result['config']['lineup']==lineup and result['config']['c_axis']==axis
    assert result['missing']==0
    for encoded in (folder/'episodes.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(encoded)
        replay=GameSession.replay(compiled,deserialize_game_record(json.dumps(row['record'])))
        assert replay.state.ply_count==len(row['initial_record']['actions'])+row['plies']
        assert replay.state.terminal_status.is_terminal==(row['outcome']is not None)


def test_fresh_setup_experience_uses_public_setup_identity_and_empty_history(tmp_path):
    import json
    from scripts.leaper_retrograde import experiential_probe
    from scripts.leaper_microgames import coexistence_rules
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    boards=[coexistence_rules(('A','B'),layout=layout).initial_position
            for layout in ('original','swap_ab')]
    folder=tmp_path/'fresh'
    result=experiential_probe(folder,episodes=4,lineup=('A','B'),
        initial_positions=boards,random_foe_seed=2026102203)
    assert result['missing']==0 and result['config']['initial_setup_count']==2
    compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(
        (folder/'rules.json').read_text(encoding='utf-8'))))
    rows=[json.loads(x)for x in(folder/'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [e['initial_setup_index']for e in rows]==[0,0,1,1]
    for i,e in enumerate(rows):
        initial=GameSession.replay(compiled,deserialize_game_record(json.dumps(e['initial_record'])))
        assert initial.state.ply_count==0 and len(initial.state.history)==1
        assert initial.state.position.board==sum(boards[i//2],())
        replay=GameSession.replay(compiled,deserialize_game_record(json.dumps(e['record'])))
        assert replay.state.ply_count==e['plies']
    with pytest.raises(ValueError,match='no played openings'):
        experiential_probe(tmp_path/'mixed',opening_count=1,initial_positions=boards)
