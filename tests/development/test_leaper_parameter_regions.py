"""Cached-graph algebra must agree with actual full-history Core execution."""
from collections import Counter
import pytest

from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.core.transition import apply_action,initial_state
from generic_chess.core.movegen import legal_actions
from scripts.leaper_parameter_regions import action_scores,material_vector,supervised_fit
from scripts.leaper_retrograde import solve_world,fresh_state


@pytest.fixture(scope='module')
def graph():
    return solve_world(kinds=('A','B'),layouts=[(0,1,8,7)])


def test_cached_D2_action_values_match_Core_with_complete_fresh_history(graph):
    g=graph;compiled=g['compiled']
    selected=[i for i,e in enumerate(g['edges'])if e][::41]
    repeats=0
    for ratio in(.25,.9900874213210581,1.,3.):
        from generic_chess.learning.incremental import Model
        material=Model([1.,ratio,1.])
        leaf=[material.raw(p)for p in map(material_vector,g['positions'])]
        for i in selected:
            state=fresh_state(g['positions'][i],compiled)
            sign=1 if state.position.side_to_move==0 else -1
            def gold(s,depth):
                nonlocal repeats
                if s.terminal_status.is_terminal:
                    if s.terminal_status.status.value=='repetition':repeats+=1
                    w=s.terminal_status.winner
                    return 0 if w is None else (1 if w==0 else -1)*(MATE_SCORE-s.ply_count)*sign
                if not depth:
                    return material.raw(material_vector(s.position))*sign
                values=[gold(apply_action(s,a,compiled),depth-1)for a in legal_actions(s,compiled)]
                return(max if s.position.side_to_move==state.position.side_to_move else min)(values)
            for depth in(1,2):
                actual=action_scores(g,i,leaf,depth)
                expected=tuple(gold(apply_action(state,a,compiled),depth-1)for a in g['actions'][i])
                assert actual==expected
    # Each player moves its own actor: in this no-pass world, a complete board
    # cannot recur within two plies. Repeat-two still matters to EXACT future
    # labels, and is covered separately by root-block and actual-history tests.
    assert selected and repeats==0
    with pytest.raises(ValueError,match='D1/D2'):
        action_scores(g,selected[0],leaf,3)


def test_oracle_fit_retains_boundary_and_nonidentifiable_controls():
    # Score r predicts only wins: constrained optimum is the upper boundary.
    win=supervised_fit({(0,1,0):Counter({1:10})})
    assert win['ratio']==8 and win['derivative']<0
    lose=supervised_fit({(0,1,0):Counter({-1:10})})
    assert lose['ratio']==0 and lose['derivative']>0
    symmetric=supervised_fit({(-2,1,0):Counter({1:5,-1:5})})
    assert symmetric['ratio']==pytest.approx(2,abs=1e-10)
    flat=supervised_fit({(0,0,0):Counter({1:5,-1:5})})
    assert flat['derivative']==0


def test_root_public_search_belongs_to_graph_minimax_set(graph):
    from generic_chess.session.session import GameSession
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
    from generic_chess.learning.mainline_search import search
    g=graph;root=g['roots'][0]
    session=GameSession(g['compiled']);env=FixedScaleSessionEnv(session,unit_type='A')
    for ratio in(.25,1.,3.):
        leaf=[a+b*ratio+c for a,b,c in map(material_vector,g['positions'])]
        weights=[ratio if name==('board','B')else 1. for name in env.names]
        for depth in(1,2):
            scores=action_scores(g,root,leaf,depth)
            r=search(env,Model(weights),depth=depth,nodes=100000,seconds=3)
            assert r.complete and r.completed_depth==depth
            k=g['actions'][root].index(r.action.action)
            assert scores[k]==max(scores)


def test_constructed_fresh_observer_matches_independently_compiled_real_fresh_game(graph):
    from dataclasses import replace
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
    from generic_chess.learning.mainline_search import search
    from scripts.leaper_parameter_regions import fresh_observer_session
    g=graph
    selected=[i for i,p in enumerate(g['positions'])if p.side_to_move==0 and g['edges'][i]][::113]
    assert selected
    for index in selected:
        p=g['positions'][index]
        board=tuple(tuple(p.board[y*3+x]for x in range(3))for y in range(3))
        real=GameSession(compile_ruleset_for_execution(replace(g['rules'],initial_position=board)))
        observed=fresh_observer_session(g,index)
        assert replace(real.state.position,ruleset_fingerprint=p.ruleset_fingerprint)==p
        assert set(real.legal_actions())==set(observed.legal_actions())
        receipts=[]
        for session in(observed,real):
            env=FixedScaleSessionEnv(session,unit_type='A')
            receipts.append(search(env,Model([1.]*len(env.names)),depth=2,nodes=100000,seconds=3))
        a,b=receipts
        assert a.complete and b.complete
        assert(a.action,a.value,a.nodes,a.completed_depth)==(b.action,b.value,b.nodes,b.completed_depth)
