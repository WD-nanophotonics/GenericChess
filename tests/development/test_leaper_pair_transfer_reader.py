"""Real full-history and retained-PV corruption tests, without new search calls."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_h6_pair_transfer import verify_history_counterexamples,verify_depth_receipts
import json

DATA=Path('docs/research/data')
PACKET=DATA/'leaper_pair_transfer_20261024'


def test_equal_position_clock_and_current_count_still_need_prehistory():
    out=verify_history_counterexamples(DATA/'leaper_h6_initial_truth_20261023',load(PACKET/'blocked-prefix.json'))
    assert out['verified']and len(out['cases'])==2
    for row in out['cases']:
        assert row['values']==[-1,0]and row['ply']==4 and row['current_occurrences']==1
        assert row['terminal_differences']==[dict(action=['K',1,0,0,0],left='ongoing',right='repetition')]


def test_replacing_one_history_by_equal_current_position_is_rejected():
    source=load(PACKET/'blocked-prefix.json')
    pair=source['families'][0]['same_Position_clock_counterexample'][0]
    pair['right']['record']=deepcopy(pair['left']['record'])
    with pytest.raises(ValueError,match='source history differs'):
        verify_history_counterexamples(DATA/'leaper_h6_initial_truth_20261023',source)


def test_shared_runtime_search_preserves_the_two_actual_histories():
    # Two integration calls on different H6 roots, not extra slots in the
    # closed36-query H64 depth diagnostic. Same physical board/clock must
    # produce opposite terminal guarantees through the real learner caller.
    from scripts.leaper_h6_initial_truth import admit
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
    from generic_chess.learning.mainline_search import search
    inputs=load(DATA/'leaper_h6_initial_truth_20261023'/'inputs.json.gz')
    family=next(f for f in inputs['families']if f['family']==6)
    source=next(r for r in inputs['rows']if r['family']==6);compiled=admit(family,source)
    pair=load(PACKET/'blocked-prefix.json')['families'][0]['same_Position_clock_counterexample'][0]
    values=[]
    for side in('left','right'):
        session=GameSession.replay(compiled,deserialize_game_record(json.dumps(pair[side]['record'])))
        env=FixedScaleSessionEnv(session,unit_type='A');receipt=search(env,Model([1.]*len(env.names)),depth=2,nodes=256,seconds=2)
        assert receipt.complete and receipt.completed_depth==2
        values.append(receipt.value)
    assert values==[-MATE,0]


@pytest.mark.parametrize('order',[('left','right'),('right','left')])
def test_warm_public_TT_does_not_alias_equal_boards_with_different_past(order):
    # Unlike the fresh-player learner adapter, this keeps one public TT
    # across both histories. No changed evaluator or q policy can clear it.
    from scripts.leaper_h6_initial_truth import admit
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,_material_features
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    inputs=load(DATA/'leaper_h6_initial_truth_20261023'/'inputs.json.gz')
    family=next(f for f in inputs['families']if f['family']==6)
    source=next(r for r in inputs['rows']if r['family']==6);compiled=admit(family,source)
    pair=load(PACKET/'blocked-prefix.json')['families'][0]['same_Position_clock_counterexample'][0]
    sessions={side:GameSession.replay(compiled,deserialize_game_record(json.dumps(pair[side]['record'])))for side in order}
    env=FixedScaleSessionEnv(sessions[order[0]],unit_type='A');model=Model([1.]*len(env.names))
    class Material:
        def evaluate(self,state):
            value=model.raw(_material_features(state.position,compiled,env.names))
            return value if state.position.side_to_move==0 else-value
        def capture_order_value(self,mover,victim):return 0
    player=AlphaBetaPlayer(compiled,evaluator_override=Material(),use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=False,require_full_pv=True))
    keys=set()
    for side in order:
        result=player.choose_action(sessions[side],SearchLimits(max_depth=2,max_nodes=256,max_time_seconds=2,quiescence_max_depth=0,quiescence_hard_max_depth=0))
        assert result.completed_depth==2
        assert (result.score<-900_000_000)if side=='left'else(result.score==0)
        assert keys<=player._tt._data.keys()
        keys=set(player._tt._data)
        assert keys


@pytest.fixture(scope='module')
def depth_inputs():
    return (load(DATA/'leaper_single_parity_20261023'/'inputs.json.gz')['worlds'],
        load(PACKET/'mask5-truth.json.gz'),load(PACKET/'depth-inputs.json.gz'),load(PACKET/'depth-results.json.gz'))


def test_retained_depth_results_have_literal_PVs_and_capture_failure_controls(depth_inputs):
    out=verify_depth_receipts(*depth_inputs)
    assert out['queries']==36 and out['nodes']==4378 and out['literal_PV_edges']==78
    assert len(out['bad_choice_capture_controls'])==3
    assert all(len(x['immediate_capture_A_draw_replies'])==1 for x in out['bad_choice_capture_controls'])


@pytest.mark.parametrize('corruption',['PV_geometry','fixed_weight','missing_query','claimed_depth','chosen_WDL'])
def test_retained_depth_corruption_rejected(depth_inputs,corruption):
    worlds,truth,inputs,result=deepcopy(depth_inputs);row=result['rows'][0]
    if corruption=='PV_geometry':row['receipt']['pv_choices'][0]['action']['geometry_id']='absent'
    elif corruption=='fixed_weight':row['weights'][0]=2.
    elif corruption=='missing_query':result['rows'].pop()
    elif corruption=='claimed_depth':row['requested_depth']=5
    elif corruption=='chosen_WDL':row['chosen_WDL']=-1
    with pytest.raises(ValueError):verify_depth_receipts(worlds,truth,inputs,result)
