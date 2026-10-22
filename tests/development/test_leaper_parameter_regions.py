"""Cached-graph algebra must agree with actual full-history Core execution."""
from collections import Counter
import pytest

from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.core.transition import apply_action,initial_state
from generic_chess.core.movegen import legal_actions
from scripts.leaper_parameter_regions import action_scores,material_vector,supervised_fit
from scripts.leaper_retrograde import solve_world,fresh_state


def test_draw_only_closure_does_not_confuse_minimax_draw_with_no_possible_mate():
    from scripts.leaper_parameter_regions import draw_only_closure
    from scripts.leaper_retrograde import attractor
    # Vertex0 can choose a draw or blunder to an opponent's terminal win.
    # The separate 3<->4 cycle and terminal draw1 can never reach a decisive end.
    edges=((1,2),(),(),(4,),(3,))
    terminals={1:0,2:1}
    values,_=attractor(edges,terminals)
    assert values[0]==0
    assert draw_only_closure(edges,terminals)==frozenset((1,3,4))
    with pytest.raises(ValueError):draw_only_closure(((1,),),{})
    with pytest.raises(ValueError):draw_only_closure(((),),{})


def test_actual_Core_graph_draw_only_region_is_closed_under_every_action(graph):
    from scripts.leaper_parameter_regions import draw_only_closure
    g=graph;closed=draw_only_closure(g['edges'],g['terminals'])
    assert closed
    for i in closed:
        assert g['values'][i]==0
        assert set(g['edges'][i])<=closed
    # Independently execute actual Core children rather than only checking
    # graph fixed-point arithmetic; capture-removal reaches these draw regions.
    selected=sorted(closed)[::31]
    for i in selected:
        s=fresh_state(g['positions'][i],g['compiled'])
        for a in legal_actions(s,g['compiled']):
            child=apply_action(s,a,g['compiled'])
            assert g['indices'][child.position]in closed


def test_uniform_tie_error_is_an_expectation_not_a_forced_error():
    from fractions import Fraction
    from scripts.leaper_parameter_regions import tie_error_counts
    mixed=tie_error_counts((2,2,1),(1,-1,0))
    assert mixed==dict(forced=False,unsafe=True,expected_error=Fraction(1,2),choices=2)
    forced=tie_error_counts((1,2,2),(1,0,-1))
    assert forced['forced']and not forced['unsafe']and forced['expected_error']==1
    assert tie_error_counts((2,1),(1,-1))['expected_error']==0
    with pytest.raises(ValueError):tie_error_counts((2,2),(None,0))


def test_decision_relevance_keeps_action_binding_and_cancellation(graph):
    from fractions import Fraction
    from scripts.leaper_parameter_regions import decision_relevance,tie_error_counts
    from scripts.leaper_retrograde import root_action_labels
    g=graph;indices=[i for i,e in enumerate(g['edges'])if e][::137]
    labels={i:tuple(root_action_labels(g,i)[a]for a in g['actions'][i])for i in indices}
    result=decision_relevance(g,labels,ratios=('1/4','1','3/2'),depths=(1,4))
    # Independent scalar API checks the batched observer, including D4 root
    # repetition and a deliberate reversal of action order plus its labels.
    for depth,observation in result.items():
        for j,b in enumerate(observation['ratios']):
            leaf=[a+b*bb+c for a,bb,c in map(material_vector,g['positions'])]
            errors=[tie_error_counts(action_scores(g,i,leaf,depth),labels[i])['expected_error']for i in indices]
            assert observation['total_errors'][j]==sum(errors,Fraction(0))
        assert observation['rootwise_oracle_error']<=observation['minimum_global_error']
    reversed_graph=dict(g,edges=[tuple(reversed(e))for e in g['edges']])
    reversed_labels={i:tuple(reversed(lab))for i,lab in labels.items()}
    reverse=decision_relevance(reversed_graph,reversed_labels,ratios=('1/4','1','3/2'),depths=(4,))
    assert reverse[4]['total_errors']==result[4]['total_errors']
    def stop():raise RuntimeError('actual cancellation')
    with pytest.raises(RuntimeError,match='actual cancellation'):
        decision_relevance(g,labels,ratios=(1,),cancel=stop)
    with pytest.raises(ValueError):decision_relevance(g,{indices[0]:(None,)},ratios=(1,))
    with pytest.raises(ValueError):decision_relevance(g,labels,ratios=(1,1))


def test_uniform_tie_distance_bounds_every_missing_binary_error_assignment():
    from fractions import Fraction
    from itertools import product
    from scripts.leaper_parameter_regions import uniform_tie_distance
    for a,b in[((2,2,1),(1,2,2)),((2,2,2),(2,1,1)),((2,1,1),(1,2,1)),((2,2,1),(2,2,1))]:
        left=[i for i,s in enumerate(a)if s==max(a)]
        right=[i for i,s in enumerate(b)if s==max(b)]
        differences=[abs(sum(Fraction(e[i],len(left))for i in left)-sum(Fraction(e[i],len(right))for i in right))for e in product((0,1),repeat=3)]
        assert max(differences)==uniform_tie_distance(a,b)
    with pytest.raises(ValueError):uniform_tie_distance((),())


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
            for depth in(1,2,3,4):
                actual=action_scores(g,i,leaf,depth)
                expected=tuple(gold(apply_action(state,a,compiled),depth-1)for a in g['actions'][i])
                assert actual==expected
    # Two-ply recurrence is impossible;four-ply root returns are real Core
    # terminals and must be scored as draws by the cached observer.
    assert selected and repeats>0
    with pytest.raises(ValueError,match='D1-D4'):
        action_scores(g,selected[0],leaf,5)


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


def test_custom_public_models_need_no_supervised_metadata_and_map_AB_channels(graph,tmp_path):
    import gzip,json,pickle
    from scripts.leaper_parameter_regions import public_position_study,tie_study
    from scripts.leaper_retrograde import root_action_labels
    g=graph;root=g['roots'][0];regions=tmp_path/'regions';regions.mkdir()
    cache=regions/'graph.pkl.gz'
    cache.write_bytes(gzip.compress(pickle.dumps({k:v for k,v in g.items()if k!='compiled'})))
    # The graph has many ongoing Positions but only this root is labelled.
    # Uniform-tie analysis must retain a bound for the unlabelled remainder.
    ongoing=sum(bool(e)for e in g['edges'])
    summary=dict(status='COMPLETE',config=dict(caches={'AB':str(cache)}),worlds={'AB':dict(ongoing=ongoing)})
    (regions/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
    values=root_action_labels(g,root)
    (regions/'AB-labels.jsonl').write_text(json.dumps(dict(index=root,values=[values[a]for a in g['actions'][root]]))+'\n',encoding='utf-8')
    models={'AB':{'nonuniform':[1.,.7,.9,1.,1.,1.]}}
    result=tie_study(tmp_path/'ties',regions=regions,models_by_world=models)
    assert result['status']=='PARTIAL_LABELS'
    for row in result['rows']:
        assert row['positions']==1 and row['missing_positions']==ongoing-1
        lo,hi=row['full_domain_expected_error_bounds']
        assert hi-lo==pytest.approx(ongoing-1)
    # A public caller consumes this explicit one-root distribution only. It
    # maps six A/B/C slots to this AB world's four actual board/hand channels.
    summary['worlds']['AB']['ongoing']=1
    (regions/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
    result=public_position_study(tmp_path/'public',regions=regions,models_by_world=models)
    assert result['recorded']==2 and result['missing']==0
    rows=[json.loads(l)for l in(tmp_path/'public'/'AB-queries.jsonl').read_text(encoding='utf-8').splitlines()]
    assert all(r[2]==r[3]and r[6]is not None for r in rows)
